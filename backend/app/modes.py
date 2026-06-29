"""The failure-mode registry.

Originally a hardcoded list; now data-backed so modes can be added, edited,
disabled, and (for grader-less modes) given a VLM grader from the UI. The
taxonomy lives in ``<data>/modes.json`` (``config.MODES_PATH``), seeded on first
access from the built-in defaults below and shared with the team via Drive, so
edits sync without a code change or restart.

This module is the single read/write surface: everything else calls the accessor
functions (``all_modes``, ``pair_mode_ids``, ``mode_graders`` …) at call time, so
runtime edits take effect immediately instead of binding an import-time snapshot.
The built-in 24 (#16 merged into #7; #18 deck-level) stay here as the DEFAULT_*
seed source (and a future "reset to default").
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import config

# Display order for grouping in the UI.
ELEMENT_ORDER = [
    "Images",
    "Components",
    "Headers/Footers/Ornaments",
    "Backgrounds & fills",
    "Typography & Colors",
    "Card & composition",
]

GRADES = ["ungraded", "pass", "borderline", "fail", "na"]

_DEFAULT_TAXONOMY: List[Dict] = [
    {"id": 1, "name": "Logo dropped", "element": "Images", "dimension": "Presence", "severity": "P1", "level": "pair"},
    {"id": 2, "name": "Headers & footers dropped", "element": "Headers/Footers/Ornaments", "dimension": "Presence", "severity": "P0", "level": "pair"},
    {"id": 3, "name": "Text sizing & spacing", "element": "Typography & Colors", "dimension": "Scale", "severity": "P1", "level": "pair"},
    {"id": 4, "name": "Divider mishandling", "element": "Headers/Footers/Ornaments", "dimension": "Presence", "severity": "P2", "level": "pair"},
    {"id": 5, "name": "Decorations dropped", "element": "Headers/Footers/Ornaments", "dimension": "Presence", "severity": "P2", "level": "pair"},
    {"id": 6, "name": "Diagrams flattened to primitives", "element": "Components", "dimension": "Presence", "severity": "P1", "level": "pair"},
    {"id": 7, "name": "Color zones / fills misassigned", "element": "Backgrounds & fills", "dimension": "Styling", "severity": "P1", "level": "pair", "aka": "merged with #16"},
    {"id": 8, "name": "Layout direction changed", "element": "Card & composition", "dimension": "Layout", "severity": "P1", "level": "pair"},
    {"id": 9, "name": "Icons dropped / swapped", "element": "Images", "dimension": "Presence", "severity": "P2", "level": "pair"},
    {"id": 10, "name": "Background / hero images dropped", "element": "Images", "dimension": "Presence", "severity": "P1", "level": "pair"},
    {"id": 11, "name": "Heading alignment", "element": "Card & composition", "dimension": "Layout", "severity": "P2", "level": "pair"},
    {"id": 12, "name": "Slides too tall / 16:9 broken", "element": "Card & composition", "dimension": "Layout", "severity": "P1", "level": "pair"},
    {"id": 13, "name": "Forced into accent treatment", "element": "Images", "dimension": "Layout", "severity": "P1", "level": "pair"},
    {"id": 14, "name": "Table styling / size", "element": "Components", "dimension": "Styling", "severity": "P1", "level": "pair"},
    {"id": 15, "name": "Labels / pills", "element": "Components", "dimension": "Styling", "severity": "P2", "level": "pair"},
    {"id": 17, "name": "Chart conversion + data loss", "element": "Components", "dimension": "Presence", "severity": "P0", "level": "pair"},
    {"id": 18, "name": "Brand color remapping", "element": "Typography & Colors", "dimension": "Styling", "severity": "P1", "level": "deck"},
    {"id": 19, "name": "Text color / emphasis drift", "element": "Typography & Colors", "dimension": "Styling", "severity": "P2", "level": "pair"},
    {"id": 20, "name": "Forced component substitution", "element": "Components", "dimension": "Presence", "severity": "P2", "level": "pair"},
    {"id": 21, "name": "Flaky / inconsistent handling", "element": "Images", "dimension": "Presence", "severity": "P2", "level": "pair"},
    {"id": 22, "name": "Bullet size / shape / color", "element": "Typography & Colors", "dimension": "Scale", "severity": "P2", "level": "pair"},
    {"id": 23, "name": "Icons / emoji / images oversized", "element": "Images", "dimension": "Scale", "severity": "P2", "level": "pair"},
    {"id": 24, "name": "Card frames / borders", "element": "Headers/Footers/Ornaments", "dimension": "Presence", "severity": "P2", "level": "pair"},
    {"id": 25, "name": "Text highlight lost", "element": "Typography & Colors", "dimension": "Styling", "severity": "P2", "level": "pair"},
]

# Built-in mode -> VLM grader, folded into each record as `grader_name` when the
# registry is seeded. 22 of 24 have a 1:1 slide grader; #18 (deck-level brand
# color) and #21 (cross-slide) intentionally have none.
_DEFAULT_GRADERS: Dict[int, str] = {
    1: "import-logo-dropped",
    2: "import-headers-footers-dropped",
    3: "import-text-sizing-spacing",
    4: "import-divider-mishandling",
    5: "import-decorations-dropped",
    6: "import-diagrams-flattened",
    7: "import-color-zones-misassigned",
    8: "import-layout-direction-changed",
    9: "import-icons-dropped-swapped",
    10: "import-background-images-dropped",
    11: "import-heading-alignment",
    12: "import-slides-too-tall",
    13: "import-forced-accent-treatment",
    14: "import-table-styling",
    15: "import-labels-pills",
    17: "import-chart-data-loss",
    19: "import-text-color-emphasis-drift",
    20: "import-forced-component-substitution",
    22: "import-bullet-styling",
    23: "import-images-oversized",
    24: "import-card-borders",
    25: "import-text-highlight-lost",
}

# Why the built-in grader-less modes have no per-pair VLM grader (seeded into
# each record's `grader_note`, shown in the directory).
_DEFAULT_GRADER_NOTES: Dict[int, str] = {
    18: "Graded once per deck (brand color remapping); the import suite is slide-level only.",
    21: "Requires cross-slide judgment a single per-pair grader can't make.",
}

DEFAULT_ELEMENT_ORDER: List[str] = list(ELEMENT_ORDER)

SCHEMA_VERSION = 1
VALID_SEVERITIES = ("P0", "P1", "P2")
VALID_LEVELS = ("pair", "deck")
# Canonical field set persisted per mode (extra keys are dropped on normalize).
_FIELDS = (
    "id", "name", "element", "dimension", "severity",
    "level", "enabled", "builtin", "grader_name", "grader_note", "aka",
)


class RegistryError(ValueError):
    """Invalid mode input (bad field, unknown id, …). Mapped to HTTP 400."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_default_modes() -> List[Dict]:
    """Merge the built-in taxonomy + grader map + notes into full records."""
    out: List[Dict] = []
    for m in _DEFAULT_TAXONOMY:
        rec = dict(m)
        rec["enabled"] = True
        rec["builtin"] = True
        rec["grader_name"] = _DEFAULT_GRADERS.get(m["id"])
        rec["grader_note"] = _DEFAULT_GRADER_NOTES.get(m["id"])
        rec.setdefault("aka", None)
        out.append({k: rec.get(k) for k in _FIELDS})
    return out


def _default_registry() -> Dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": _now(),
        "element_order": list(DEFAULT_ELEMENT_ORDER),
        "modes": _build_default_modes(),
    }


# modes.json is a single shared file (like mode_descriptions.json), so reads are
# cached by file mtime and writes are atomic under a lock. Edits are rare and
# last-write-wins, consistent with the rest of the shared store.
_lock = threading.RLock()
_cache: Optional[Dict] = None
_cache_mtime: Optional[float] = None


def _normalize_mode(m: Dict) -> Optional[Dict]:
    try:
        mid = int(m["id"])
    except (KeyError, TypeError, ValueError):
        return None
    return {
        "id": mid,
        "name": str(m.get("name") or "").strip(),
        "element": str(m.get("element") or "").strip(),
        "dimension": str(m.get("dimension") or "").strip(),
        "severity": m["severity"] if m.get("severity") in VALID_SEVERITIES else "P2",
        "level": m["level"] if m.get("level") in VALID_LEVELS else "pair",
        "enabled": bool(m.get("enabled", True)),
        "builtin": bool(m.get("builtin", False)),
        "grader_name": str(m["grader_name"]).strip() if m.get("grader_name") else None,
        "grader_note": str(m["grader_note"]) if m.get("grader_note") else None,
        "aka": str(m["aka"]) if m.get("aka") else None,
    }


def _normalize_registry(data: Dict) -> Dict:
    raw = data.get("modes") if isinstance(data, dict) else None
    modes: List[Dict] = []
    seen = set()
    for m in raw or []:
        rec = _normalize_mode(m)
        if rec is None or rec["id"] in seen:
            continue
        seen.add(rec["id"])
        modes.append(rec)
    if not modes:
        modes = _build_default_modes()
    order = [str(e).strip() for e in (data.get("element_order") or []) if str(e).strip()]
    if not order:
        order = list(DEFAULT_ELEMENT_ORDER)
    # Every element used by a mode must be in the order list or the UI (which
    # groups strictly by element_order) would silently drop those modes.
    for m in modes:
        if m["element"] and m["element"] not in order:
            order.append(m["element"])
    return {
        "schema_version": int(data.get("schema_version") or SCHEMA_VERSION),
        "updated_at": data.get("updated_at") or _now(),
        "element_order": order,
        "modes": modes,
    }


def _write(reg: Dict) -> None:
    """Atomically persist the registry and invalidate the cache."""
    global _cache, _cache_mtime
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(config.DATA_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(reg, f, indent=2, ensure_ascii=False)
        os.replace(tmp, config.MODES_PATH)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    _cache = None
    _cache_mtime = None


def _registry() -> Dict:
    """Return the cached, normalized registry (seeding modes.json on first use).

    Internal: callers MUST NOT mutate the result — read accessors copy out and
    mutators deep-copy before writing."""
    global _cache, _cache_mtime
    with _lock:
        path = config.MODES_PATH
        if not path.exists():
            _write(_default_registry())
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = None
        if _cache is not None and _cache_mtime == mtime:
            return _cache
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = _default_registry()
        reg = _normalize_registry(data)
        _cache = reg
        _cache_mtime = mtime
        return reg


# ----------------------------------------------------------------- read accessors
def all_modes() -> List[Dict]:
    """Every mode (enabled + disabled), in registry order."""
    return [dict(m) for m in _registry()["modes"]]


def enabled_modes() -> List[Dict]:
    return [dict(m) for m in _registry()["modes"] if m["enabled"]]


def mode_by_id(mode_id: int) -> Optional[Dict]:
    for m in _registry()["modes"]:
        if m["id"] == mode_id:
            return dict(m)
    return None


def has_mode(mode_id: int) -> bool:
    return any(m["id"] == mode_id for m in _registry()["modes"])


def all_mode_ids() -> List[int]:
    return [m["id"] for m in _registry()["modes"]]


def pair_mode_ids(enabled_only: bool = True) -> List[int]:
    return [m["id"] for m in _registry()["modes"]
            if m["level"] == "pair" and (m["enabled"] or not enabled_only)]


def deck_mode_ids(enabled_only: bool = True) -> List[int]:
    return [m["id"] for m in _registry()["modes"]
            if m["level"] == "deck" and (m["enabled"] or not enabled_only)]


def mode_graders(enabled_only: bool = False) -> Dict[int, str]:
    """{mode_id: grader_name} for modes that have a grader."""
    return {m["id"]: m["grader_name"] for m in _registry()["modes"]
            if m["grader_name"] and (m["enabled"] or not enabled_only)}


def grader_name(mode_id: int) -> Optional[str]:
    m = mode_by_id(mode_id)
    return m["grader_name"] if m else None


def grader_note(mode_id: int) -> Optional[str]:
    m = mode_by_id(mode_id)
    return m["grader_note"] if m else None


def element_order() -> List[str]:
    return list(_registry()["element_order"])


# ----------------------------------------------------------------- mutators
def _next_id(reg: Dict) -> int:
    ids = [m["id"] for m in reg["modes"]]
    return (max(ids) + 1) if ids else 1


def _validate_fields(fields: Dict, *, partial: bool) -> Dict:
    """Validate + coerce a subset (partial) or full set of editable fields."""
    out: Dict = {}
    if "name" in fields or not partial:
        name = str(fields.get("name") or "").strip()
        if not name:
            raise RegistryError("name is required")
        out["name"] = name
    if "element" in fields or not partial:
        element = str(fields.get("element") or "").strip()
        if not element:
            raise RegistryError("element is required")
        out["element"] = element
    if "dimension" in fields:
        out["dimension"] = str(fields.get("dimension") or "").strip()
    elif not partial:
        out["dimension"] = ""
    if "severity" in fields or not partial:
        sev = fields.get("severity") or "P2"
        if sev not in VALID_SEVERITIES:
            raise RegistryError(f"severity must be one of {', '.join(VALID_SEVERITIES)}")
        out["severity"] = sev
    if "level" in fields or not partial:
        lvl = fields.get("level") or "pair"
        if lvl not in VALID_LEVELS:
            raise RegistryError(f"level must be one of {', '.join(VALID_LEVELS)}")
        out["level"] = lvl
    if "enabled" in fields:
        out["enabled"] = bool(fields["enabled"])
    return out


def add_mode(fields: Dict) -> Dict:
    """Create a new (custom) mode. Returns the stored record."""
    clean = _validate_fields(fields, partial=False)
    with _lock:
        reg = copy.deepcopy(_registry())
        rec = {
            "id": _next_id(reg),
            "name": clean["name"],
            "element": clean["element"],
            "dimension": clean.get("dimension", ""),
            "severity": clean["severity"],
            "level": clean["level"],
            "enabled": clean.get("enabled", True),
            "builtin": False,
            "grader_name": None,
            "grader_note": None,
            "aka": None,
        }
        reg["modes"].append(rec)
        if rec["element"] not in reg["element_order"]:
            reg["element_order"].append(rec["element"])
        reg["updated_at"] = _now()
        _write(reg)
        return dict(rec)


def update_mode(mode_id: int, fields: Dict) -> Dict:
    """Patch editable fields (name/element/dimension/severity/level/enabled)."""
    clean = _validate_fields(fields, partial=True)
    with _lock:
        reg = copy.deepcopy(_registry())
        rec = next((m for m in reg["modes"] if m["id"] == mode_id), None)
        if rec is None:
            raise RegistryError(f"unknown mode #{mode_id}")
        rec.update(clean)
        if "element" in clean and clean["element"] not in reg["element_order"]:
            reg["element_order"].append(clean["element"])
        reg["updated_at"] = _now()
        _write(reg)
        return dict(rec)


def set_enabled(mode_id: int, enabled: bool) -> Dict:
    return update_mode(mode_id, {"enabled": bool(enabled)})


def set_grader(mode_id: int, name: Optional[str]) -> Dict:
    """Attach/detach a VLM grader by name. Clears grader_note when attaching."""
    with _lock:
        reg = copy.deepcopy(_registry())
        rec = next((m for m in reg["modes"] if m["id"] == mode_id), None)
        if rec is None:
            raise RegistryError(f"unknown mode #{mode_id}")
        rec["grader_name"] = str(name).strip() if name else None
        if rec["grader_name"]:
            rec["grader_note"] = None
        reg["updated_at"] = _now()
        _write(reg)
        return dict(rec)


def delete_mode(mode_id: int) -> bool:
    """Remove a mode outright. Returns False if the id was not present. Callers
    must guard against deleting a mode that still has stored grades/verdicts."""
    with _lock:
        reg = copy.deepcopy(_registry())
        before = len(reg["modes"])
        reg["modes"] = [m for m in reg["modes"] if m["id"] != mode_id]
        if len(reg["modes"]) == before:
            return False
        reg["updated_at"] = _now()
        _write(reg)
        return True
