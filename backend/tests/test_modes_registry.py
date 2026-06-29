"""Unit tests for the data-backed failure-mode registry (app/modes.py) and the
delete-guard helpers it works with. All pure/offline — no network, no PDFs.

Runs with plain Python (no pytest needed):

    backend/.venv/bin/python tests/test_modes_registry.py

or, if pytest is installed:

    backend/.venv/bin/python -m pytest tests/test_modes_registry.py
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402

# Redirect every shared store at a throwaway dir BEFORE anything reads them, so a
# developer's real SLIDE_GRADER_DATA is never touched (the modules read these
# config attrs at call time, so reassigning here is enough).
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="modes_reg_test_"))
config.DATA_DIR = _TMP
config.MODES_PATH = _TMP / "modes.json"
config.ANNOTATIONS_DIR = _TMP / "annotations"
config.AI_GRADES_DIR = _TMP / "ai_grades"
config.IMPORT_EVALS_GRADERS_DIR = _TMP / "graders"

from app import ai_grader  # noqa: E402
from app import modes  # noqa: E402
from app import storage  # noqa: E402

try:  # main pulls in the FastAPI app (static mounts); optional for the guard test.
    from app import main as _main  # noqa: E402
    from fastapi import HTTPException as _HTTPException  # noqa: E402
    HAVE_MAIN = True
except Exception:  # pragma: no cover - only if the UI hasn't been built
    HAVE_MAIN = False


def _fresh() -> None:
    """Reset to a freshly-seeded registry + empty stores between tests."""
    if config.MODES_PATH.exists():
        config.MODES_PATH.unlink()
    for d in (config.ANNOTATIONS_DIR, config.AI_GRADES_DIR):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    modes._cache = None
    modes._cache_mtime = None


# ------------------------------------------------------------------ seeding
def test_seed_defaults_24_enabled_builtins():
    _fresh()
    all_m = modes.all_modes()
    assert len(all_m) == 24  # the built-in taxonomy (16 merged into 7)
    assert len(modes.enabled_modes()) == 24
    assert all(m["builtin"] and m["enabled"] for m in all_m)
    assert modes.element_order() == modes.DEFAULT_ELEMENT_ORDER
    # a known grader mapping + the two intentionally grader-less modes
    assert modes.grader_name(1) == "import-logo-dropped"
    assert modes.grader_name(18) is None and modes.grader_note(18)
    assert modes.grader_name(21) is None


def test_seed_is_idempotent_and_persisted():
    _fresh()
    first = modes.all_mode_ids()
    assert config.MODES_PATH.exists()  # seeding wrote the file
    # a second read (cache busted) returns the same registry, not a re-seed dup
    modes._cache = None
    modes._cache_mtime = None
    assert modes.all_mode_ids() == first


# ------------------------------------------------------------------ add / id assignment
def test_add_mode_defaults_and_id_is_max_plus_one():
    _fresh()
    a = modes.add_mode({"name": "Footnotes dropped", "element": "Images"})
    assert a["id"] == 26  # max built-in id is 25
    assert a["enabled"] is True and a["builtin"] is False
    assert a["grader_name"] is None
    assert a["severity"] == "P2" and a["level"] == "pair" and a["dimension"] == ""
    assert modes.has_mode(26) and any(m["id"] == 26 for m in modes.enabled_modes())
    b = modes.add_mode({"name": "Another", "element": "Images"})
    assert b["id"] == 27


def test_add_mode_extends_element_order():
    _fresh()
    assert "Zebra" not in modes.element_order()
    modes.add_mode({"name": "Zebra thing", "element": "Zebra"})
    assert "Zebra" in modes.element_order()


# ------------------------------------------------------------------ validation
def test_add_and_update_validation_errors():
    _fresh()
    bad_inputs = [
        {"name": "", "element": "Images"},          # name required
        {"name": "x", "element": ""},               # element required
        {"name": "x", "element": "y", "severity": "P9"},   # bad severity
        {"name": "x", "element": "y", "level": "slide"},   # bad level
    ]
    for fields in bad_inputs:
        try:
            modes.add_mode(fields)
        except modes.RegistryError:
            continue
        raise AssertionError(f"expected RegistryError for {fields}")
    try:
        modes.update_mode(9999, {"name": "z"})
    except modes.RegistryError:
        return
    raise AssertionError("expected RegistryError updating an unknown id")


# ------------------------------------------------------------------ edit built-ins
def test_edit_builtin_fields_in_place():
    _fresh()
    upd = modes.update_mode(2, {"name": "Renamed", "severity": "P2", "level": "deck"})
    assert upd["name"] == "Renamed" and upd["severity"] == "P2" and upd["level"] == "deck"
    assert upd["builtin"] is True  # editing a built-in doesn't make it custom
    # the level change moved it from the pair list to the deck list
    assert 2 in modes.deck_mode_ids() and 2 not in modes.pair_mode_ids()


# ------------------------------------------------------------------ disable (soft) visibility
def test_disable_hides_from_active_but_keeps_in_registry():
    _fresh()
    modes.set_enabled(1, False)
    assert 1 not in [m["id"] for m in modes.enabled_modes()]
    assert 1 in modes.all_mode_ids()                       # still present
    assert 1 not in modes.pair_mode_ids()                  # excluded from active
    assert 1 in modes.pair_mode_ids(enabled_only=False)    # but discoverable
    assert 1 not in modes.mode_graders(enabled_only=True)
    assert 1 in modes.mode_graders(enabled_only=False)
    modes.set_enabled(1, True)
    assert 1 in [m["id"] for m in modes.enabled_modes()]


# ------------------------------------------------------------------ set_grader
def test_set_grader_attaches_and_clears_note():
    _fresh()
    assert modes.grader_name(18) is None and modes.grader_note(18)
    modes.set_grader(18, "import-custom-brand")
    assert modes.grader_name(18) == "import-custom-brand"
    assert modes.grader_note(18) is None  # note cleared once a grader is attached
    modes.set_grader(18, None)
    assert modes.grader_name(18) is None


# ------------------------------------------------------------------ delete
def test_delete_mode_removes_it():
    _fresh()
    c = modes.add_mode({"name": "Disposable", "element": "Images"})
    assert modes.has_mode(c["id"])
    assert modes.delete_mode(c["id"]) is True
    assert not modes.has_mode(c["id"])
    assert modes.delete_mode(c["id"]) is False  # idempotent / no-op second time


# ------------------------------------------------------------------ delete-guard helpers
def test_count_human_grades_reads_annotation_files():
    _fresh()
    ann = {"variants": {"ideal": {
        "deck_level": {"18": {"grade": "fail", "note": ""}},
        "pairs": [{"index": 1, "modes": {
            "26": {"grade": "borderline", "note": ""},
            "27": {"grade": "ungraded", "note": ""},
        }}],
    }}}
    (config.ANNOTATIONS_DIR / "d1.json").write_text(json.dumps(ann), encoding="utf-8")
    assert storage.count_human_grades_for_mode(26) == 1   # one graded pair cell
    assert storage.count_human_grades_for_mode(18) == 1   # one graded deck cell
    assert storage.count_human_grades_for_mode(27) == 0   # ungraded => no data
    assert storage.count_human_grades_for_mode(99) == 0   # absent everywhere


def test_delete_guard_blocks_when_data_present():
    _fresh()
    c = modes.add_mode({"name": "Guarded", "element": "Images", "level": "pair"})
    cell = {"verdict": "pass", "prompt_hash": "h", "grader": "g", "model": "m"}
    ai_grader.store_ai_verdicts(c["id"], [("d1", "ideal", 1, cell)])
    assert ai_grader.count_ai_grades_for_mode(c["id"]) == 1
    if HAVE_MAIN:
        raised = False
        try:
            _main.delete_mode(c["id"])
        except _HTTPException as exc:
            raised = exc.status_code == 409
        assert raised, "expected a 409 from delete_mode while AI data exists"
        assert modes.has_mode(c["id"])  # still there
    # clearing the data unblocks deletion
    ai_grader.clear_ai_grades_for_mode(c["id"])
    assert ai_grader.count_ai_grades_for_mode(c["id"]) == 0
    if HAVE_MAIN:
        _main.delete_mode(c["id"])
        assert not modes.has_mode(c["id"])


# ------------------------------------------------------------------ sync: lossless disable, drop on remove
def test_sync_preserves_disabled_cell_and_drops_removed():
    _fresh()
    c = modes.add_mode({"name": "Syncable", "element": "Images", "level": "pair"})
    mid = str(c["id"])
    orig = storage._pairs_from_images
    storage._pairs_from_images = lambda slug, vkey: (
        [{"index": 1, "input_image": "/images/d/input/001.png", "output_image": "/images/d/ideal/001.png"}],
        {"input": [], "output": []}, 1, 1,
    )
    try:
        prev = {"deck_level": {}, "pairs": [{"index": 1, "modes": {mid: {"grade": "fail", "note": "keep me"}}}]}
        # disabled modes stay out of the active grid but their recorded cell survives
        modes.set_enabled(c["id"], False)
        synced = storage._sync_variant("d", "ideal", prev)
        cell = synced["pairs"][0]["modes"].get(mid)
        assert cell is not None and cell["grade"] == "fail"
        # a truly-removed mode IS dropped on the next sync
        modes.delete_mode(c["id"])
        synced2 = storage._sync_variant("d", "ideal", prev)
        assert mid not in synced2["pairs"][0]["modes"]
    finally:
        storage._pairs_from_images = orig


# ------------------------------------------------------------------ runner
def _run() -> None:
    tests = sorted(
        (name, fn) for name, fn in globals().items()
        if name.startswith("test_") and callable(fn)
    )
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {exc!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    _run()
