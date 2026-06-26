"""Unit tests for the pure (no-network) parts of the recalibration engine:
dataset split, scoring, flips, sampling, and optimizer-response parsing.

Runs with plain Python (no pytest needed):

    backend/.venv/bin/python tests/test_recalibrate.py

or, if pytest is installed:

    backend/.venv/bin/python -m pytest tests/test_recalibrate.py
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app import ai_grader as ag  # noqa: E402
from app import config  # noqa: E402
from app import recalibrate as rc  # noqa: E402
from app.recalibrate import Row  # noqa: E402


def _row(index: int, grade: str, variant: str = "ideal", slug: str = "d") -> Row:
    p = pathlib.Path("/tmp/x.png")
    return Row(
        slug=slug, variant=variant, index=index, input_path=p, output_path=p,
        human_grade=grade, human_note="", input_url="/images/d/input/x.png",
        output_url="/images/d/ideal/x.png",
    )


# ------------------------------------------------------------------ fractions / sizes
def test_fractions_default_sums_to_one():
    ft, fv, fte = rc._fractions()
    assert abs((ft + fv + fte) - 1.0) < 1e-9
    assert round(ft, 2) == 0.6 and round(fv, 2) == 0.2 and round(fte, 2) == 0.2


def test_split_sizes_typical_and_floors():
    assert rc._split_sizes(100) == {"train": 60, "val": 20, "test": 20}
    assert rc._split_sizes(3) == {"train": 1, "val": 1, "test": 1}
    assert rc._split_sizes(2) is None  # too small to give every bucket >= 1


# ------------------------------------------------------------------ split_rows
def test_split_rows_partitions_and_is_deterministic():
    rows = [_row(i, "pass") for i in range(1, 101)]
    a = rc.split_rows(rows, seed=1234)
    assert (len(a["train"]), len(a["val"]), len(a["test"])) == (60, 20, 20)

    ids = lambda bucket: {r.id for r in a[bucket]}
    all_ids = ids("train") | ids("val") | ids("test")
    assert len(all_ids) == 100  # disjoint + complete
    assert ids("train").isdisjoint(ids("val"))
    assert ids("train").isdisjoint(ids("test"))
    assert ids("val").isdisjoint(ids("test"))

    b = rc.split_rows(rows, seed=1234)
    assert {r.id for r in a["test"]} == {r.id for r in b["test"]}  # reproducible


def test_split_rows_too_small_raises():
    try:
        rc.split_rows([_row(1, "pass"), _row(2, "fail")], seed=1)
    except rc.RecalibrateError:
        return
    raise AssertionError("expected RecalibrateError for a 2-row dataset")


# ------------------------------------------------------------------ scoring
def test_score_counts_agreement_errors_and_kappa():
    rows = [_row(1, "pass"), _row(2, "fail"), _row(3, "pass"), _row(4, "fail")]
    verdicts = {
        rows[0].id: "pass",    # agree
        rows[1].id: "fail",    # agree
        rows[2].id: "fail",    # disagree
        rows[3].id: "error",   # excluded, counted as an error
    }
    s = rc._score(rows, verdicts)
    assert s["n"] == 3
    assert s["errors"] == 1
    assert s["agreements"] == 2
    assert s["agreement_pct"] == 66.7
    assert s["cohen_kappa"] == 0.4  # hand-computed
    assert s["confusion"]["pass"]["fail"] == 1


def test_score_perfect_agreement_kappa_one():
    rows = [_row(1, "pass"), _row(2, "fail")]
    verdicts = {rows[0].id: "pass", rows[1].id: "fail"}
    s = rc._score(rows, verdicts)
    assert s["agreement_pct"] == 100.0
    assert s["cohen_kappa"] == 1.0


# ------------------------------------------------------------------ flips
def test_flips_fixed_and_broke():
    rows = [_row(1, "pass"), _row(2, "fail"), _row(3, "pass")]
    before = {rows[0].id: "pass", rows[1].id: "pass", rows[2].id: "fail"}
    after = {rows[0].id: "fail", rows[1].id: "fail", rows[2].id: "pass"}
    f = rc._flips(rows, before, after)
    assert len(f["fixed"]) == 2  # r2, r3 went wrong -> right
    assert len(f["broke"]) == 1  # r1 went right -> wrong
    assert {e["pair_index"] for e in f["fixed"]} == {2, 3}


# ------------------------------------------------------------------ sampling
def test_stratified_respects_budget_and_covers_cells():
    import random
    items = []
    for cell, n in {("pass", "fail"): 5, ("fail", "pass"): 3, ("na", "pass"): 2}.items():
        items += [{"row": object(), "cell": cell} for _ in range(n)]
    out = rc._stratified(random.Random(0), items, 5)
    assert len(out) == 5
    assert len({id(it["row"]) for it in out}) == 5  # no duplicates
    assert len({it["cell"] for it in out}) == 3  # one per cell first


def test_stratified_returns_all_when_under_budget():
    import random
    items = [{"row": object(), "cell": ("pass", "fail")} for _ in range(3)]
    out = rc._stratified(random.Random(0), items, 10)
    assert len(out) == 3


# ------------------------------------------------------------------ optimizer parsing / guardrail
def test_valid_prompt_guardrail():
    good = (
        '## Verdicts\n- "pass" - ...\n- "borderline" - ...\n- "fail" - ...\n- "na" - ...\n'
        '```json\n{ "verdict": "pass", "reason": "..." }\n```'
    )
    assert rc._valid_prompt(good) is True
    assert rc._valid_prompt(good.replace('"na"', "")) is False  # dropped a verdict
    assert rc._valid_prompt('no verdicts here') is False


def test_parse_optimizer_plain_and_fenced_and_nested_json():
    rubric = '# Rubric\n```json\n{ "verdict": "pass" | "fail", "reason": "..." }\n```'
    payload = {"themes": "root causes", "summary": "tightened the fail band", "prompt": rubric}
    raw = json.dumps(payload)
    parsed = rc._parse_optimizer(raw)
    assert parsed is not None
    assert parsed["themes"] == "root causes"
    assert parsed["summary"] == "tightened the fail band"  # per-candidate change description
    assert parsed["prompt"] == rubric  # inner ```json survives intact

    fenced = "```json\n" + raw + "\n```"
    assert rc._parse_optimizer(fenced)["prompt"] == rubric

    # summary is optional — absent => empty string, never missing
    no_summary = rc._parse_optimizer(json.dumps({"themes": "x", "prompt": rubric}))
    assert no_summary["summary"] == ""

    assert rc._parse_optimizer("not json, no braces") is None
    assert rc._parse_optimizer(json.dumps({"themes": "x"})) is None  # missing prompt


# ------------------------------------------------------------------ estimate
def test_estimate_no_grader_mode_is_ineligible():
    pv = rc.estimate(18)  # mode #18 is deck-level, has no VLM grader
    assert pv["eligible"] is False
    assert "no VLM grader" in (pv["reason"] or "")


# ------------------------------------------------------------------ adopt: clear stale scores
def test_clear_stale_ai_grades_keeps_current_drops_others():
    import shutil
    import tempfile

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="aigrades_test_"))
    orig = config.AI_GRADES_DIR
    config.AI_GRADES_DIR = tmp
    try:
        mid, other = 1, 2
        cur, old = "newhash", "oldhash"

        def cell(h):
            return {"verdict": "pass", "prompt_hash": h, "grader": "g", "model": "m"}

        ag.store_ai_verdicts(mid, [
            ("d1", "ideal", 1, cell(cur)),   # current  -> keep
            ("d1", "ideal", 2, cell(old)),   # stale    -> drop
            ("d2", "ideal", 1, cell(old)),   # stale    -> drop
        ])
        ag.store_ai_verdicts(other, [("d1", "ideal", 1, cell(old))])  # other mode -> untouched

        removed = ag.clear_stale_ai_grades_for_mode(mid, cur)
        assert removed == 2

        s1 = ag.load_ai_grades("d1", "ideal")
        assert str(mid) in s1["pairs"]["1"]        # current verdict kept
        assert str(mid) not in s1["pairs"]["2"]    # stale verdict dropped
        assert str(other) in s1["pairs"]["1"]      # other mode untouched
        assert str(mid) not in ag.load_ai_grades("d2", "ideal")["pairs"]["1"]

        # idempotent: a second pass finds nothing stale
        assert ag.clear_stale_ai_grades_for_mode(mid, cur) == 0
    finally:
        config.AI_GRADES_DIR = orig
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------ runner
def _main() -> None:
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
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    _main()
