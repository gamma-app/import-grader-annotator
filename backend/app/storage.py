"""Deck scanning, PNG rendering coordination, and annotation persistence."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from . import config
from . import modes as registry
from .pdf_split import pdf_page_count, render_pdf_to_pngs, write_pdf_without_pages

# Per-deck reentrant locks serialize read-modify-write of each annotation file
# within this process. Cross-machine edits to the SAME deck are avoided by the
# divide-decks workflow (each deck is its own JSON file); the shared Drive folder
# is eventually-consistent and last-write-wins.
_deck_locks: Dict[str, threading.RLock] = {}
_deck_locks_guard = threading.Lock()


def _deck_lock(slug: str) -> threading.RLock:
    with _deck_locks_guard:
        lock = _deck_locks.get(slug)
        if lock is None:
            lock = threading.RLock()
            _deck_locks[slug] = lock
        return lock


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_cell() -> Dict:
    return {"grade": "ungraded", "note": ""}


def _id_in(key: str, ids: set) -> bool:
    """True if a stringified mode-id `key` is one of `ids` (ints)."""
    try:
        return int(key) in ids
    except (TypeError, ValueError):
        return False


def prettify(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.replace("_", "-").split("-") if w) or slug


# ---------------------------------------------------------------- paths
def deck_dir(slug: str) -> Path:
    return config.DECKS_DIR / slug


def _input_pdf(slug: str) -> Path:
    return deck_dir(slug) / config.INPUT_PDF


def _input_png_dir(slug: str) -> Path:
    return config.RENDER_CACHE_DIR / slug / config.INPUT_DIR


def _variant_pdf(slug: str, vkey: str) -> Path:
    return deck_dir(slug) / config.VARIANT_BY_KEY[vkey]["pdf"]


def _variant_png_dir(slug: str, vkey: str) -> Path:
    return config.RENDER_CACHE_DIR / slug / config.VARIANT_BY_KEY[vkey]["dir"]


def _variant_pdf_backup(slug: str, vkey: str) -> Path:
    """Pristine `<stem>.original.pdf` beside the canonical output PDF, written once
    on the first align edit so the original can be restored by hand if needed."""
    pdf = _variant_pdf(slug, vkey)
    return pdf.with_name(f"{pdf.stem}.original{pdf.suffix}")


def _annotation_path(slug: str) -> Path:
    return config.ANNOTATIONS_DIR / f"{slug}.json"


def list_slugs() -> List[str]:
    if not config.DECKS_DIR.exists():
        return []
    return sorted(p.name for p in config.DECKS_DIR.iterdir() if p.is_dir())


def _png_names(d: Path) -> List[str]:
    if not d.exists():
        return []
    return sorted(p.name for p in d.glob("*.png"))


def _image_url(slug: str, side: str, name: str) -> str:
    return f"/images/{slug}/{side}/{name}"


def _png_dir_version(png_dir: Path) -> str:
    """Cache-bust token for a render dir: `count-totalsize-newestmtime`.

    It changes whenever the dir is re-rendered (e.g. an align edit drops a page and
    renumbers the PNGs), so image URLs built with it dodge stale browser caches that
    would otherwise show the pre-edit pixels at the same `00N.png` URL — which looks
    like "the wrong slide was dropped". Combining count + size + mtime makes the token
    change even if a re-render lands in the same clock second (coarse-mtime filesystems)."""
    try:
        stats = [p.stat() for p in png_dir.glob("*.png")]
    except OSError:
        return ""
    if not stats:
        return ""
    total = sum(s.st_size for s in stats)
    newest = int(max(s.st_mtime for s in stats))
    return f"{len(stats)}-{total}-{newest}"


def _bust(url: str, ver: str) -> str:
    """Append a cache-bust query (`?v=`). `ai_grader._image_path` strips it back off."""
    return f"{url}?v={ver}" if ver else url


# ---------------------------------------------------------------- rendering
def _needs_render(pdf: Path, png_dir: Path) -> bool:
    if not pdf.exists():
        return False
    pngs = list(png_dir.glob("*.png"))
    if not pngs:
        return True
    newest_png = max(p.stat().st_mtime for p in pngs)
    return pdf.stat().st_mtime > newest_png


def ensure_rendered(slug: str, force: bool = False) -> None:
    targets = [(_input_pdf(slug), _input_png_dir(slug))]
    for vkey in config.VARIANT_KEYS:
        targets.append((_variant_pdf(slug, vkey), _variant_png_dir(slug, vkey)))
    for pdf, png_dir in targets:
        if pdf.exists() and (force or _needs_render(pdf, png_dir)):
            render_pdf_to_pngs(pdf, png_dir, width=config.RENDER_WIDTH)


# ---------------------------------------------------------------- annotation io
def load_annotation(slug: str) -> Optional[Dict]:
    path = _annotation_path(slug)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_annotation(slug: str, data: Dict) -> None:
    config.ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = _annotation_path(slug)
    fd, tmp = tempfile.mkstemp(dir=str(config.ANNOTATIONS_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ------------------------------------------------------------- mode descriptions
# Human-authored failure-mode descriptions, stored once for the workspace (not
# per deck/variant) since the taxonomy + grader prompts are variant-independent.
_mode_desc_lock = threading.RLock()
_MODE_DESC_SCHEMA = 1


def load_mode_descriptions() -> Dict:
    path = config.MODE_DESCRIPTIONS_PATH
    if not path.exists():
        return {"schema_version": _MODE_DESC_SCHEMA, "updated_at": _now(), "descriptions": {}}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"schema_version": _MODE_DESC_SCHEMA, "updated_at": _now(), "descriptions": {}}
    data.setdefault("descriptions", {})
    return data


def _save_mode_descriptions(data: Dict) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = config.MODE_DESCRIPTIONS_PATH
    fd, tmp = tempfile.mkstemp(dir=str(config.DATA_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def set_mode_description(mode_id: int, text: str, annotator: Optional[str] = None) -> Dict:
    now = _now()
    with _mode_desc_lock:
        data = load_mode_descriptions()
        entry: Dict = {"text": text, "updated_at": now}
        if annotator:
            entry["updated_by"] = annotator
        data.setdefault("descriptions", {})[str(mode_id)] = entry
        data["updated_at"] = now
        data["schema_version"] = _MODE_DESC_SCHEMA
        _save_mode_descriptions(data)
        return entry


def _pair_reviewed(modes: Dict[str, Dict]) -> bool:
    return all(modes.get(str(mid), _default_cell())["grade"] != "ungraded" for mid in registry.pair_mode_ids())


def _pairs_from_images(slug: str, vkey: str):
    inputs = _png_names(_input_png_dir(slug))
    outputs = _png_names(_variant_png_dir(slug, vkey))
    side = config.VARIANT_BY_KEY[vkey]["dir"]
    n = min(len(inputs), len(outputs))
    pairs = [
        {
            "index": i + 1,
            "input_image": _image_url(slug, config.INPUT_DIR, inputs[i]),
            "output_image": _image_url(slug, side, outputs[i]),
        }
        for i in range(n)
    ]
    unpaired = {
        "input": [_image_url(slug, config.INPUT_DIR, x) for x in inputs[n:]],
        "output": [_image_url(slug, side, x) for x in outputs[n:]],
    }
    return pairs, unpaired, len(inputs), len(outputs)


def _migrate(existing: Dict) -> Dict:
    """Bring an annotation dict up to the current schema.

    v1 stored a single output's `deck_level`/`pairs` at the top level. That output
    was the Deck Doctor deck, so it migrates into the `ideal` variant.
    """
    if not existing or "variants" in existing:
        return existing or {}
    migrated = dict(existing)
    migrated["variants"] = {
        config.DEFAULT_VARIANT: {
            "deck_level": existing.get("deck_level", {}),
            "pairs": existing.get("pairs", []),
            "unpaired": existing.get("unpaired", {"input": [], "output": []}),
            "updated_at": existing.get("updated_at", _now()),
        }
    }
    for legacy_key in ("deck_level", "pairs", "unpaired", "alignment"):
        migrated.pop(legacy_key, None)
    return migrated


def _sync_variant(slug: str, vkey: str, prev: Dict) -> Dict:
    pair_imgs, unpaired, n_in, n_out = _pairs_from_images(slug, vkey)
    now = _now()
    available = _variant_pdf(slug, vkey).exists()

    # Active cells follow the live registry, but we preserve any prior cell whose
    # mode still exists (disabled, or moved between pair/deck) so soft-disable and
    # level edits never drop a recorded grade. Only truly-removed modes are dropped.
    registry_ids = set(registry.all_mode_ids())
    prev_deck = prev.get("deck_level") or {}
    deck_level = {str(mid): prev_deck.get(str(mid), _default_cell()) for mid in registry.deck_mode_ids()}
    for k, v in prev_deck.items():
        if k not in deck_level and _id_in(k, registry_ids):
            deck_level[k] = v

    prev_pairs = {p["index"]: p for p in prev.get("pairs", [])}
    pairs: List[Dict] = []
    for pim in pair_imgs:
        prior = prev_pairs.get(pim["index"], {})
        prior_modes = prior.get("modes", {})
        modes = {str(mid): prior_modes.get(str(mid), _default_cell()) for mid in registry.pair_mode_ids()}
        for k, v in prior_modes.items():
            if k not in modes and _id_in(k, registry_ids):
                modes[k] = v
        pairs.append(
            {
                "index": pim["index"],
                "input_image": pim["input_image"],
                "output_image": pim["output_image"],
                "reviewed": _pair_reviewed(modes),
                "modes": modes,
                "updated_at": prior.get("updated_at", now),
            }
        )

    result = {
        "available": available,
        "alignment": {
            "input_count": n_in,
            "output_count": n_out,
            "pair_count": len(pairs),
            "misaligned": available and n_in != n_out,
        },
        "deck_level": deck_level,
        "pairs": pairs,
        "unpaired": unpaired,
        "updated_at": prev.get("updated_at", now),
    }
    # Carry alignment provenance forward (set by align_variant); not derived data.
    if prev.get("alignment_edit"):
        result["alignment_edit"] = prev["alignment_edit"]
    return result


def sync_annotation(slug: str) -> Dict:
    """Build/refresh the annotation file to match current images & mode registry,
    preserving any grades/notes already recorded. Schema v2 = per-variant data."""
    with _deck_lock(slug):
        existing = _migrate(load_annotation(slug) or {})
        now = _now()
        prev_variants = existing.get("variants", {})

        variants = {vkey: _sync_variant(slug, vkey, prev_variants.get(vkey, {})) for vkey in config.VARIANT_KEYS}

        ann = {
            "schema_version": config.ANNOTATION_SCHEMA_VERSION,
            "deck_slug": slug,
            "title": prettify(slug),
            "annotator": existing.get("annotator", ""),
            "created_at": existing.get("created_at", now),
            "updated_at": existing.get("updated_at", now),
            "variants": variants,
        }
        save_annotation(slug, ann)
        return ann


def _variant_detail(ann: Dict, slug: str, vkey: str) -> Dict:
    v = ann["variants"][vkey]
    meta = config.VARIANT_BY_KEY[vkey]
    # Cache-bust image URLs per side so a re-rendered deck (e.g. after an align edit)
    # never shows stale browser-cached pixels at the same `00N.png` URL.
    in_ver = _png_dir_version(_input_png_dir(slug))
    out_ver = _png_dir_version(_variant_png_dir(slug, vkey))
    pairs = [
        {
            **p,
            "input_image": _bust(p["input_image"], in_ver),
            "output_image": _bust(p["output_image"], out_ver),
        }
        for p in v["pairs"]
    ]
    unpaired_src = v.get("unpaired", {}) or {}
    unpaired = {
        "input": [_bust(u, in_ver) for u in unpaired_src.get("input", [])],
        "output": [_bust(u, out_ver) for u in unpaired_src.get("output", [])],
    }
    return {
        "deck_slug": slug,
        "title": ann.get("title", prettify(slug)),
        "annotator": ann.get("annotator", ""),
        "variant": vkey,
        "variant_label": meta["label"],
        "available": v.get("available", False),
        "alignment": v["alignment"],
        "alignment_edit": v.get("alignment_edit"),
        "deck_level": v["deck_level"],
        "pairs": pairs,
        "unpaired": unpaired,
    }


def get_deck_detail(slug: str, vkey: str) -> Dict:
    if vkey not in config.VARIANT_BY_KEY:
        raise KeyError(f"unknown variant '{vkey}'")
    ensure_rendered(slug)
    ann = sync_annotation(slug)
    return _variant_detail(ann, slug, vkey)


def _load_for_update(slug: str, vkey: str) -> Dict:
    """Load an annotation ready for mutation; sync if it's missing the variant."""
    ann = _migrate(load_annotation(slug) or {})
    if "variants" not in ann or vkey not in ann.get("variants", {}):
        ann = sync_annotation(slug)
    return ann


def is_variant_gradeable(slug: str, vkey: str) -> bool:
    """True when a variant has an output PDF whose page count matches the input
    (i.e. not misaligned). Misaligned variants are locked from grading until
    aligned via :func:`align_variant`."""
    if vkey not in config.VARIANT_BY_KEY:
        return False
    summ = _variant_summary(slug, vkey, None)
    return bool(summ["available"]) and not summ["misaligned"]


def align_variant(
    slug: str, vkey: str, drop_pages: List[int], annotator: Optional[str] = None
) -> Dict:
    """Drop `drop_pages` (1-based) from a misaligned variant's output PDF so it
    lines up 1:1 with the input, re-render, and clear that variant's grades.

    Destructive: rewrites the canonical output PDF in place after a one-time
    `*.original.pdf` backup (kept for manual recovery; there is no in-app reset).
    Returns the refreshed, now-unlocked deck detail.
    """
    if vkey not in config.VARIANT_BY_KEY:
        raise KeyError(f"unknown variant '{vkey}'")
    with _deck_lock(slug):
        input_pdf = _input_pdf(slug)
        out_pdf = _variant_pdf(slug, vkey)
        if not input_pdf.exists():
            raise ValueError(f"deck '{slug}' has no {config.INPUT_PDF}")
        if not out_pdf.exists():
            raise ValueError(f"variant '{vkey}' of deck '{slug}' has no output PDF")

        input_count = pdf_page_count(input_pdf)
        output_count = pdf_page_count(out_pdf)
        if output_count == input_count:
            raise RuntimeError(f"variant '{vkey}' of deck '{slug}' is already aligned")
        if output_count < input_count:
            raise ValueError(
                "cannot align by dropping output slides when output < input "
                f"({output_count} < {input_count})"
            )

        drop = [int(p) for p in drop_pages]
        if len(set(drop)) != len(drop):
            raise ValueError("drop_pages must be unique")
        for p in drop:
            if p < 1 or p > output_count:
                raise ValueError(f"page {p} is out of range 1..{output_count}")
        remaining = output_count - len(drop)
        if remaining != input_count:
            raise ValueError(
                f"dropping {len(drop)} of {output_count} output pages leaves "
                f"{remaining}, but the input has {input_count}"
            )

        # One-time backup of the pristine output PDF.
        backup = _variant_pdf_backup(slug, vkey)
        if not backup.exists():
            shutil.copy2(out_pdf, backup)

        # Rewrite the canonical output PDF without the dropped pages (atomic).
        fd, tmp = tempfile.mkstemp(dir=str(deck_dir(slug)), suffix=".pdf.tmp")
        os.close(fd)
        try:
            write_pdf_without_pages(out_pdf, Path(tmp), drop)
            os.replace(tmp, out_pdf)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

        # Re-render this variant's PNG cache from the edited PDF.
        render_pdf_to_pngs(out_pdf, _variant_png_dir(slug, vkey), width=config.RENDER_WIDTH)

        # Drop this variant's AI verdicts (indices have shifted; must be re-run).
        ai_path = config.AI_GRADES_DIR / f"{slug}__{vkey}.json"
        if ai_path.exists():
            ai_path.unlink()

        # Reset this variant to a clean slate + record provenance. Storing only
        # `alignment_edit` makes the next sync rebuild fresh (ungraded) pairs and
        # deck-level cells from the new images.
        ann = _migrate(load_annotation(slug) or {})
        ann.setdefault("variants", {})[vkey] = {
            "alignment_edit": {
                "dropped_output_pages": drop,
                "original_output_count": output_count,
                "edited_at": _now(),
                "edited_by": annotator or "",
            }
        }
        if annotator:
            ann["annotator"] = annotator
        ann["updated_at"] = _now()
        save_annotation(slug, ann)

    return get_deck_detail(slug, vkey)


def reset_alignment(slug: str, vkey: str, annotator: Optional[str] = None) -> Dict:
    """Undo a previous align: restore the pristine ``*.original.pdf`` over the
    canonical output PDF, re-render, clear this variant's grades + provenance, and
    remove the backup. The deck returns to its original (misaligned) state and is
    re-locked for grading. Returns the refreshed deck detail.
    """
    if vkey not in config.VARIANT_BY_KEY:
        raise KeyError(f"unknown variant '{vkey}'")
    with _deck_lock(slug):
        out_pdf = _variant_pdf(slug, vkey)
        backup = _variant_pdf_backup(slug, vkey)
        if not backup.exists():
            raise RuntimeError(
                f"variant '{vkey}' of deck '{slug}' has no alignment backup to restore"
            )

        # Restore the pristine PDF (atomic), then drop the backup so the deck is
        # back to its exact original on-disk state.
        fd, tmp = tempfile.mkstemp(dir=str(deck_dir(slug)), suffix=".pdf.tmp")
        os.close(fd)
        try:
            shutil.copy2(backup, tmp)
            os.replace(tmp, out_pdf)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        backup.unlink()

        # Re-render this variant's PNG cache from the restored PDF.
        render_pdf_to_pngs(out_pdf, _variant_png_dir(slug, vkey), width=config.RENDER_WIDTH)

        # Drop this variant's AI verdicts (indices have shifted back).
        ai_path = config.AI_GRADES_DIR / f"{slug}__{vkey}.json"
        if ai_path.exists():
            ai_path.unlink()

        # Reset this variant to a clean slate (drops grades + alignment_edit). The
        # next sync rebuilds fresh cells; the restored original re-locks if misaligned.
        ann = _migrate(load_annotation(slug) or {})
        ann.setdefault("variants", {})[vkey] = {}
        if annotator:
            ann["annotator"] = annotator
        ann["updated_at"] = _now()
        save_annotation(slug, ann)

    return get_deck_detail(slug, vkey)


def update_pair(slug: str, vkey: str, index: int, modes: Dict[str, Dict], annotator: Optional[str] = None) -> Dict:
    if vkey not in config.VARIANT_BY_KEY:
        raise KeyError(f"unknown variant '{vkey}'")
    with _deck_lock(slug):
        if not is_variant_gradeable(slug, vkey):
            raise RuntimeError(f"variant '{vkey}' of deck '{slug}' is misaligned and locked from grading")
        ann = _load_for_update(slug, vkey)
        variant = ann["variants"][vkey]
        now = _now()
        found = False
        for pair in variant["pairs"]:
            if pair["index"] == index:
                for mid in registry.pair_mode_ids():
                    key = str(mid)
                    if key in modes:
                        cell = modes[key]
                        pair["modes"][key] = {
                            "grade": cell.get("grade", "ungraded"),
                            "note": cell.get("note", ""),
                        }
                pair["reviewed"] = _pair_reviewed(pair["modes"])
                pair["updated_at"] = now
                found = True
                break
        if not found:
            raise KeyError(f"pair {index} not found in deck {slug} variant {vkey}")
        variant["updated_at"] = now
        if annotator:
            ann["annotator"] = annotator
        ann["updated_at"] = now
        save_annotation(slug, ann)
        return next(p for p in variant["pairs"] if p["index"] == index)


def update_deck_level(slug: str, vkey: str, modes: Dict[str, Dict], annotator: Optional[str] = None) -> Dict:
    if vkey not in config.VARIANT_BY_KEY:
        raise KeyError(f"unknown variant '{vkey}'")
    with _deck_lock(slug):
        if not is_variant_gradeable(slug, vkey):
            raise RuntimeError(f"variant '{vkey}' of deck '{slug}' is misaligned and locked from grading")
        ann = _load_for_update(slug, vkey)
        variant = ann["variants"][vkey]
        now = _now()
        for mid in registry.deck_mode_ids():
            key = str(mid)
            if key in modes:
                cell = modes[key]
                variant["deck_level"][key] = {
                    "grade": cell.get("grade", "ungraded"),
                    "note": cell.get("note", ""),
                }
        variant["updated_at"] = now
        if annotator:
            ann["annotator"] = annotator
        ann["updated_at"] = now
        save_annotation(slug, ann)
        return variant["deck_level"]


def _variant_summary(slug: str, vkey: str, ann: Optional[Dict]) -> Dict:
    in_pngs = _png_names(_input_png_dir(slug))
    out_pngs = _png_names(_variant_png_dir(slug, vkey))
    has_input_pdf = _input_pdf(slug).exists()
    has_variant_pdf = _variant_pdf(slug, vkey).exists()

    n_in = len(in_pngs) if in_pngs else (pdf_page_count(_input_pdf(slug)) if has_input_pdf else 0)
    n_out = len(out_pngs) if out_pngs else (pdf_page_count(_variant_pdf(slug, vkey)) if has_variant_pdf else 0)
    pair_count = min(n_in, n_out)

    reviewed = 0
    alignment_edit = None
    if ann and "variants" in ann:
        v = ann["variants"].get(vkey, {})
        reviewed = sum(1 for p in v.get("pairs", []) if p.get("reviewed"))
        alignment_edit = v.get("alignment_edit")

    return {
        "available": has_variant_pdf,
        "rendered": bool(in_pngs and out_pngs),
        "input_count": n_in,
        "output_count": n_out,
        "pair_count": pair_count,
        "misaligned": has_input_pdf and has_variant_pdf and n_in != n_out,
        "reviewed_count": min(reviewed, pair_count),
        "alignment_edit": alignment_edit,
    }


def deck_summary(slug: str) -> Dict:
    """Lightweight per-variant summary for the dashboard (avoids rendering)."""
    raw = load_annotation(slug)
    ann = _migrate(raw) if raw else None
    variants = {vkey: _variant_summary(slug, vkey, ann) for vkey in config.VARIANT_KEYS}
    return {
        "slug": slug,
        "title": prettify(slug),
        "has_input_pdf": _input_pdf(slug).exists(),
        "variants": variants,
    }


def list_decks() -> List[Dict]:
    return [deck_summary(s) for s in list_slugs()]


def annotation_variant(slug: str, vkey: str) -> Optional[Dict]:
    """Read one variant's stored grades (migrated to v2) without rendering.

    Returns the variant dict ({available, alignment, deck_level, pairs, unpaired,
    ...}) as last saved, or None if the deck has no annotation file / variant yet.
    Used by read-only consumers (e.g. reports) that must not trigger a re-render.
    """
    raw = load_annotation(slug)
    if not raw:
        return None
    ann = _migrate(raw)
    return ann.get("variants", {}).get(vkey)


def _cell_has_data(cell: Optional[Dict]) -> bool:
    """True when a stored cell carries human data: a real grade or a note."""
    if not cell:
        return False
    return cell.get("grade", "ungraded") != "ungraded" or bool((cell.get("note") or "").strip())


def count_human_grades_for_mode(mode_id: int) -> int:
    """How many stored human cells carry data for a mode, across all decks/variants
    (pair-level + deck-level). Read-only; never renders. Used to gate hard-delete.

    Enumerates the annotation files directly (not deck folders) so the count
    reflects what's actually persisted even if a deck folder is missing."""
    mid = str(mode_id)
    total = 0
    if not config.ANNOTATIONS_DIR.exists():
        return 0
    for path in sorted(config.ANNOTATIONS_DIR.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        ann = _migrate(raw)
        for v in ann.get("variants", {}).values():
            if _cell_has_data((v.get("deck_level") or {}).get(mid)):
                total += 1
            for p in v.get("pairs", []):
                if _cell_has_data((p.get("modes") or {}).get(mid)):
                    total += 1
    return total
