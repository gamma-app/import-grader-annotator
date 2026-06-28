"""Grader recalibration: optimize a VLM grader's prompt from human labels.

For one pair-level failure mode we pool every human-labeled slide pair (across all
decks and all variants), split it train/validation/test, score the current prompt
(baseline), then generate N independent candidate prompts. Each candidate is one
vision call that returns ``{themes, summary, prompt}`` — a root-cause diagnosis of
the training disagreements, a brief plain-language description of what the rewrite
changed, and the rewritten rubric (wording/rules only). Candidates are
scored on validation; the best by Cohen's kappa is re-scored on the held-out test
set for an honest before/after, and the whole run is saved for human review.

Adoption (separate, explicit) writes the winning prompt to the canonical
``prompt.md`` and persists the winner's already-computed verdicts so the agreement
report is instantly current. Nothing here mutates ``prompt.md`` until ``adopt_run``.
"""
from __future__ import annotations

import json
import os
import random
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import ai_grader, config, llm, reports, storage
from .modes import MODE_BY_ID, MODE_GRADERS

# The comparable verdicts on both sides (human + agent); mirrors reports.py.
_GRADES = reports._GRADES


class RecalibrateError(RuntimeError):
    """Bad input or a run that can't proceed (too little data, model failure)."""


class _Cancelled(Exception):
    """Internal: raised to unwind a run when its job is cancelled."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------- dataset
@dataclass
class Row:
    """One human-labeled slide pair: the unit of the dataset/split."""
    slug: str
    variant: str
    index: int
    input_path: Path
    output_path: Path
    human_grade: str
    human_note: str
    input_url: str
    output_url: str

    @property
    def id(self) -> str:
        return f"{self.slug}__{self.variant}__{self.index}"


def _labeled_count(mode_id: int) -> int:
    """Count human-labeled, gradeable pairs for a mode (cheap; no rendering)."""
    mkey = str(mode_id)
    total = 0
    for slug in storage.list_slugs():
        for variant in config.VARIANT_KEYS:
            hv = storage.annotation_variant(slug, variant)
            if not hv or not hv.get("available"):
                continue
            if not storage.is_variant_gradeable(slug, variant):
                continue
            for p in hv.get("pairs", []):
                cell = (p.get("modes") or {}).get(mkey) or {}
                if cell.get("grade") in _GRADES:
                    total += 1
    return total


def build_dataset(mode_id: int) -> List[Row]:
    """Pool every human-labeled, gradeable pair for a mode across decks + variants.

    Renders each contributing deck once so the slide PNGs exist on disk. Rows whose
    images are still missing are skipped (counted out of the dataset)."""
    mkey = str(mode_id)
    rows: List[Row] = []
    for slug in storage.list_slugs():
        rendered = False
        for variant in config.VARIANT_KEYS:
            hv = storage.annotation_variant(slug, variant)
            if not hv or not hv.get("available"):
                continue
            if not storage.is_variant_gradeable(slug, variant):
                continue
            labeled = [
                p for p in hv.get("pairs", [])
                if ((p.get("modes") or {}).get(mkey) or {}).get("grade") in _GRADES
            ]
            if not labeled:
                continue
            if not rendered:
                storage.ensure_rendered(slug)
                rendered = True
            for p in labeled:
                in_url = p.get("input_image")
                out_url = p.get("output_image")
                if not in_url or not out_url:
                    continue
                ip = ai_grader._image_path(in_url)
                op = ai_grader._image_path(out_url)
                if not ip.exists() or not op.exists():
                    continue
                cell = (p.get("modes") or {}).get(mkey) or {}
                rows.append(Row(
                    slug=slug, variant=variant, index=int(p.get("index")),
                    input_path=ip, output_path=op,
                    human_grade=cell.get("grade"), human_note=cell.get("note", "") or "",
                    input_url=in_url, output_url=out_url,
                ))
    return rows


# --------------------------------------------------------------- split
def _fractions() -> Tuple[float, float, float]:
    """(train, val, test) fractions from config, normalized to sum to 1."""
    try:
        parts = [float(x) for x in config.RECALIBRATE_SPLIT.split(",")]
    except ValueError:
        parts = [0.6, 0.2, 0.2]
    if len(parts) != 3 or any(p <= 0 for p in parts):
        parts = [0.6, 0.2, 0.2]
    s = sum(parts)
    return parts[0] / s, parts[1] / s, parts[2] / s


def _split_sizes(n: int) -> Optional[Dict[str, int]]:
    """Bucket sizes for n rows, with a floor of 1 in val/test. None if too small."""
    _, fv, fte = _fractions()
    n_test = max(1, round(n * fte))
    n_val = max(1, round(n * fv))
    n_train = n - n_val - n_test
    if n_train < 1:
        return None
    return {"train": n_train, "val": n_val, "test": n_test}


def split_rows(rows: List[Row], seed: int) -> Dict[str, object]:
    """Seeded, fully-random per-pair split into train/val/test."""
    sizes = _split_sizes(len(rows))
    if sizes is None:
        raise RecalibrateError(
            f"only {len(rows)} labeled pairs — too few to split train/val/test"
        )
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    nt, nv = sizes["test"], sizes["val"]
    test = shuffled[:nt]
    val = shuffled[nt:nt + nv]
    train = shuffled[nt + nv:]
    return {"train": train, "val": val, "test": test, "sizes": sizes}


# --------------------------------------------------------------- scoring
def _score(rows: List[Row], verdicts: Dict[str, Optional[str]]) -> Dict:
    """Agreement of `verdicts` (row id -> verdict) against the human grades."""
    human_dist = {g: 0 for g in _GRADES}
    ai_dist = {g: 0 for g in _GRADES}
    confusion = {h: {a: 0 for a in _GRADES} for h in _GRADES}
    agreements = n = errors = 0
    for r in rows:
        v = verdicts.get(r.id)
        if v not in _GRADES:
            errors += 1
            continue
        n += 1
        human_dist[r.human_grade] += 1
        ai_dist[v] += 1
        confusion[r.human_grade][v] += 1
        if v == r.human_grade:
            agreements += 1
    return {
        "n": n,
        "errors": errors,
        "agreements": agreements,
        "agreement_pct": round(100 * agreements / n, 1) if n else None,
        "cohen_kappa": reports._cohen_kappa(human_dist, ai_dist, agreements, n),
        "confusion": confusion,
        "human_distribution": human_dist,
        "ai_distribution": ai_dist,
    }


def _flip_entry(r: Row, before: str, after: str) -> Dict:
    return {
        "slug": r.slug,
        "title": storage.prettify(r.slug),
        "variant": r.variant,
        "pair_index": r.index,
        "input_image": r.input_url,
        "output_image": r.output_url,
        "human_grade": r.human_grade,
        "human_note": r.human_note,
        "before": before,
        "after": after,
    }


def _flips(rows: List[Row], before: Dict[str, Optional[str]],
           after: Dict[str, Optional[str]]) -> Dict[str, List[Dict]]:
    """Which rows the candidate fixed (wrong->right) or broke (right->wrong)."""
    fixed, broke = [], []
    for r in rows:
        b, a = before.get(r.id), after.get(r.id)
        if b not in _GRADES or a not in _GRADES:
            continue
        b_ok, a_ok = (b == r.human_grade), (a == r.human_grade)
        if not b_ok and a_ok:
            fixed.append(_flip_entry(r, b, a))
        elif b_ok and not a_ok:
            broke.append(_flip_entry(r, b, a))
    return {"fixed": fixed, "broke": broke}


def _verdict_map(cells: Dict[str, Dict]) -> Dict[str, Optional[str]]:
    return {rid: c.get("verdict") for rid, c in cells.items()}


# --------------------------------------------------------------- grading
def _grade_baseline(rows: List[Row], mode_id: int, *,
                    on_tick: Callable[..., None], cancel) -> Dict[str, Dict]:
    """Grade rows with the LIVE grader prompt (cached where fresh, persisted)."""
    results: Dict[str, Dict] = {}

    def task(r: Row) -> Tuple[str, Dict]:
        return r.id, ai_grader.grade_pair_mode(
            r.slug, r.variant, r.index, mode_id,
            input_path=r.input_path, output_path=r.output_path,
        )

    workers = max(1, config.AI_GRADER_CONCURRENCY)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(task, r) for r in rows]):
            rid, cell = fut.result()
            results[rid] = cell
            on_tick()
            if cancel is not None and cancel.is_set():
                raise _Cancelled()
    return results


def _grade_candidate(rows: List[Row], prompt: str, model: str, *,
                     on_tick: Callable[..., None], cancel) -> Dict[str, Dict]:
    """Grade rows inline with a candidate prompt (temp 0.0, not persisted)."""
    results: Dict[str, Dict] = {}

    def task(r: Row) -> Tuple[str, Dict]:
        res = llm.run_grader(prompt, model, r.input_path, r.output_path)
        verdict, reason = ai_grader.parse_verdict(res.get("rawResponse"))
        return r.id, {
            "verdict": verdict or "error",
            "reason": reason or (res.get("error") or "could not parse a verdict"),
        }

    workers = max(1, config.AI_GRADER_CONCURRENCY)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(task, r) for r in rows]):
            rid, cell = fut.result()
            results[rid] = cell
            on_tick()
            if cancel is not None and cancel.is_set():
                raise _Cancelled()
    return results


# --------------------------------------------------------------- optimizer
_SYSTEM = (
    "You are an expert at improving VLM grader rubrics that judge how faithfully "
    "PowerPoint slides are imported into Gamma. You are given a grader's current "
    "rubric and cases where its verdict disagreed with an expert human's grade. "
    "Diagnose why the disagreements happen, then rewrite the rubric to agree better "
    "with the human — changing ONLY wording, criteria, and the pass/borderline/fail/na "
    "band descriptions. You MUST keep the same task, the same four verdicts (pass, "
    "borderline, fail, na), the same input_slide/output_slide image naming, and the "
    "same JSON response format. Do not change the model or invent new verdicts. "
    "Also summarize, in one or two plain sentences, the key changes your rewrite makes."
)


def _case_items(train_rows: List[Row], baseline: Dict[str, Dict]):
    """Split train rows into disagreement / anchor case items for sampling."""
    dis, anc = [], []
    for r in train_rows:
        v = baseline.get(r.id, {}).get("verdict")
        if v not in _GRADES:
            continue
        if v == r.human_grade:
            anc.append({"row": r, "cell": (r.human_grade,)})
        else:
            dis.append({"row": r, "cell": (r.human_grade, v)})
    return dis, anc


def _stratified(rng: random.Random, items: List[Dict], budget: int) -> List[Dict]:
    """Sample up to `budget` items, one per confusion cell first then fill."""
    if budget <= 0 or not items:
        return []
    if len(items) <= budget:
        out = list(items)
        rng.shuffle(out)
        return out
    groups: Dict[object, List[Dict]] = {}
    for it in items:
        groups.setdefault(it["cell"], []).append(it)
    for g in groups.values():
        rng.shuffle(g)
    selected: List[Dict] = []
    keys = list(groups.keys())
    rng.shuffle(keys)
    for key in keys:  # floor: one per non-empty cell
        if len(selected) >= budget:
            break
        selected.append(groups[key].pop())
    remaining = [it for g in groups.values() for it in g]
    rng.shuffle(remaining)
    while len(selected) < budget and remaining:
        selected.append(remaining.pop())
    rng.shuffle(selected)
    return selected


def _confusion_summary_text(train_rows: List[Row], baseline: Dict[str, Dict]) -> str:
    counts: Dict[Tuple[str, str], int] = {}
    for r in train_rows:
        v = baseline.get(r.id, {}).get("verdict")
        key = (r.human_grade, v if v in _GRADES else "error")
        counts[key] = counts.get(key, 0) + 1
    lines = []
    for (h, a), c in sorted(counts.items()):
        tag = "agree" if h == a else "DISAGREE"
        lines.append(f"- human={h} ai={a}: {c} ({tag})")
    return "\n".join(lines) or "(none)"


def _build_parts(mode: Dict, current_prompt: str, train_rows: List[Row],
                 baseline: Dict[str, Dict], dis_items: List[Dict],
                 anchor_items: List[Dict]) -> List[object]:
    """Assemble the interleaved text+image payload for one optimizer call."""
    n_dis = sum(
        1 for r in train_rows
        if baseline.get(r.id, {}).get("verdict") in _GRADES
        and baseline.get(r.id, {}).get("verdict") != r.human_grade
    )
    parts: List[object] = [
        (
            f"# Failure mode: {mode['name']} (#{mode['id']})\n"
            f"Element: {mode['element']} \u00b7 Dimension: {mode['dimension']} \u00b7 "
            f"Severity: {mode['severity']}\n\n"
            f"The current rubric below disagrees with expert human grades on "
            f"{n_dis} of {len(train_rows)} training slide pairs. Diagnose the root "
            "causes, then rewrite the rubric so it agrees better with the human."
        ),
        "## Current rubric\n\n" + current_prompt.strip(),
        "## Confusion summary (training set)\n\n"
        + _confusion_summary_text(train_rows, baseline),
    ]

    dtxt = ["## All training disagreements (human grade vs. current AI verdict)\n"]
    for r in train_rows:
        cell = baseline.get(r.id, {})
        v = cell.get("verdict")
        if v in _GRADES and v != r.human_grade:
            note = (r.human_note or "").strip().replace("\n", " ") or "(none)"
            reason = (cell.get("reason") or "").strip().replace("\n", " ") or "(none)"
            dtxt.append(f"- human={r.human_grade} ai={v} | human_note: {note} | ai_reason: {reason}")
    parts.append("\n".join(dtxt))

    if dis_items:
        parts.append(
            "## Selected disagreements with images\n\nEach case shows the human's "
            "grade + note and the current AI verdict + reason, then the two slides."
        )
        for it in dis_items:
            r = it["row"]
            cell = baseline.get(r.id, {})
            parts.append(
                f"### Disagreement {r.id}\n"
                f"human={r.human_grade} \u00b7 ai={cell.get('verdict')}\n"
                f"human_note: {r.human_note or '(none)'}\n"
                f"ai_reason: {cell.get('reason') or '(none)'}\ninput_slide:"
            )
            parts.append(r.input_path)
            parts.append("output_slide:")
            parts.append(r.output_path)

    if anchor_items:
        parts.append(
            "## Correct examples to keep right\n\nThe AI currently agrees with the "
            "human on these — your rewrite must not break them."
        )
        for it in anchor_items:
            r = it["row"]
            parts.append(
                f"### Anchor {r.id}\nhuman={r.human_grade} (AI agrees)\ninput_slide:"
            )
            parts.append(r.input_path)
            parts.append("output_slide:")
            parts.append(r.output_path)

    parts.append(
        "## Your response\n\nReturn ONLY a JSON object of the form:\n"
        '```json\n{ "themes": "<root-cause analysis of the disagreements>", '
        '"summary": "<1-2 sentence, plain-language description of the key changes '
        'this rewrite makes to the rubric vs. the current one>", '
        '"prompt": "<the full revised rubric in Markdown>" }\n```\n'
        'The "prompt" must be the complete rubric with the same structure as the '
        "current one, including the Verdicts section (pass/borderline/fail/na) and "
        "the JSON response-format block."
    )
    return parts


def _parse_optimizer(text: Optional[str]) -> Optional[Dict[str, str]]:
    """Pull {themes, prompt} out of the optimizer's JSON response."""
    t = (text or "").strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if len(lines) >= 2 and lines[-1].strip().startswith("```"):
            t = "\n".join(lines[1:-1]).strip()
    obj = None
    try:
        obj = json.loads(t)
    except json.JSONDecodeError:
        obj = ai_grader._extract_json_obj(t)
    if not isinstance(obj, dict):
        return None
    prompt = obj.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return None
    themes = obj.get("themes")
    summary = obj.get("summary")
    return {
        "themes": themes if isinstance(themes, str) else "",
        "summary": summary if isinstance(summary, str) else "",
        "prompt": prompt.strip(),
    }


def _valid_prompt(prompt: str) -> bool:
    """Guardrail: candidate must keep the verdict set + JSON response shape."""
    required = ('"verdict"', '"reason"', '"pass"', '"borderline"', '"fail"', '"na"')
    return all(tok in prompt for tok in required)


def _make_candidate(cand_id: str, rng: random.Random, mode: Dict, current_prompt: str,
                    train_rows: List[Row], baseline: Dict[str, Dict],
                    optimizer_model: str, temperature: float) -> Dict:
    """One independent candidate: diagnose + rewrite (up to 2 attempts)."""
    dis_all, anc_all = _case_items(train_rows, baseline)
    k = config.RECALIBRATE_IMAGE_CASES
    m = config.RECALIBRATE_ANCHORS
    last_error = "optimizer produced no valid prompt"
    sampled_ids: List[str] = []
    themes = ""
    summary = ""
    for _ in range(2):
        dis = _stratified(rng, dis_all, k)
        anc = _stratified(rng, anc_all, m)
        sampled_ids = [d["row"].id for d in dis] + [a["row"].id for a in anc]
        parts = _build_parts(mode, current_prompt, train_rows, baseline, dis, anc)
        res = llm.generate_vision_text(
            parts, optimizer_model, system=_SYSTEM,
            max_tokens=config.RECALIBRATE_MAX_TOKENS, temperature=temperature,
        )
        if res.get("error") or not res.get("text"):
            last_error = res.get("error") or "empty response from optimizer"
            continue
        parsed = _parse_optimizer(res["text"])
        if not parsed:
            last_error = "optimizer response was not valid JSON {themes, prompt}"
            continue
        themes = parsed["themes"]
        summary = parsed["summary"]
        if not _valid_prompt(parsed["prompt"]):
            last_error = "candidate prompt dropped the verdict set or JSON format (guardrail)"
            continue
        return {
            "id": cand_id, "temperature": temperature, "themes": themes,
            "summary": summary, "prompt": parsed["prompt"],
            "sampled_ids": sampled_ids, "error": None,
        }
    return {
        "id": cand_id, "temperature": temperature, "themes": themes,
        "summary": summary, "prompt": None,
        "sampled_ids": sampled_ids, "error": last_error,
    }


def _candidate_sort_key(c: Dict) -> Tuple[float, float, int]:
    s = c.get("val_score") or {}
    k = s.get("cohen_kappa")
    return (-1.0 if k is None else k, s.get("agreement_pct") or 0.0, -(s.get("errors") or 0))


# --------------------------------------------------------------- estimate
def estimate(mode_id: int) -> Dict:
    """Preview for the confirm dialog: dataset/split sizes + estimated model calls.

    Cheap — counts labels and never renders or grades."""
    grader_name = MODE_GRADERS.get(mode_id)
    if not grader_name:
        return {"eligible": False, "reason": "this mode has no VLM grader",
                "dataset_size": 0, "min_dataset": config.RECALIBRATE_MIN_DATASET,
                "candidates": config.RECALIBRATE_CANDIDATES, "split": None,
                "estimated_calls": None}
    n = _labeled_count(mode_id)
    sizes = _split_sizes(n)
    N = config.RECALIBRATE_CANDIDATES
    eligible = n >= config.RECALIBRATE_MIN_DATASET and sizes is not None
    reason = None
    if not eligible:
        reason = (f"needs at least {config.RECALIBRATE_MIN_DATASET} labeled pairs "
                  f"(has {n})")
    est = (n + N + N * sizes["val"] + sizes["train"] + sizes["test"]) if sizes else None
    return {
        "eligible": eligible,
        "reason": reason,
        "dataset_size": n,
        "min_dataset": config.RECALIBRATE_MIN_DATASET,
        "candidates": N,
        "split": sizes,
        "estimated_calls": est,
    }


# --------------------------------------------------------------- engine
def _noop(*_args, **_kwargs) -> None:
    pass


def _run(mode_id: int, *, cancel=None,
         on_total: Callable[[int], None] = _noop,
         on_tick: Callable[..., None] = _noop,
         on_stage: Callable[[str], None] = _noop) -> Dict:
    """Execute a full recalibration and return the saved run record."""
    mode = MODE_BY_ID[mode_id]
    grader_name = MODE_GRADERS.get(mode_id)
    if not grader_name:
        raise RecalibrateError(f"mode #{mode_id} has no VLM grader")
    grader = ai_grader.load_grader(grader_name)
    optimizer_model = config.RECALIBRATE_MODEL or grader["model"]
    seed = config.RECALIBRATE_SEED
    N = config.RECALIBRATE_CANDIDATES

    on_stage("building dataset")
    rows = build_dataset(mode_id)
    if len(rows) < config.RECALIBRATE_MIN_DATASET:
        raise RecalibrateError(
            f"only {len(rows)} usable labeled pairs (need "
            f"{config.RECALIBRATE_MIN_DATASET}); grade more slides for this mode first"
        )
    splits = split_rows(rows, seed)
    train: List[Row] = splits["train"]  # type: ignore[assignment]
    val: List[Row] = splits["val"]      # type: ignore[assignment]
    test: List[Row] = splits["test"]    # type: ignore[assignment]
    n_val = len(val)

    on_total(len(rows) + N + N * n_val + len(train) + len(test))

    # ---- baseline (current prompt) over the whole dataset
    on_stage("scoring the current prompt")
    baseline_cells = _grade_baseline(rows, mode_id, on_tick=on_tick, cancel=cancel)
    baseline_v = _verdict_map(baseline_cells)
    baseline = {
        "train": _score(train, baseline_v),
        "val": _score(val, baseline_v),
        "test": _score(test, baseline_v),
    }

    # ---- N independent candidates, each scored on validation
    candidates: List[Dict] = []
    for i in range(N):
        if cancel is not None and cancel.is_set():
            raise _Cancelled()
        on_stage(f"generating candidate {i + 1}/{N}")
        rng = random.Random(seed + 1 + i)
        cand = _make_candidate(
            f"c{i + 1}", rng, mode, grader["prompt"], train, baseline_cells,
            optimizer_model, config.RECALIBRATE_TEMPERATURE,
        )
        on_tick()  # the optimizer call
        if cand.get("prompt"):
            on_stage(f"validating candidate {i + 1}/{N}")
            cells = _grade_candidate(
                val, cand["prompt"], grader["model"], on_tick=on_tick, cancel=cancel,
            )
            cand["val_score"] = _score(val, _verdict_map(cells))
        else:
            on_tick(n_val)  # keep the progress bar honest for a failed candidate
        candidates.append(cand)

    valid = [c for c in candidates if c.get("prompt") and c.get("val_score")]
    if not valid:
        why = next((c["error"] for c in candidates if c.get("error")), "unknown error")
        raise RecalibrateError(f"no usable candidate prompt was produced ({why})")
    winner = max(valid, key=_candidate_sort_key)

    # ---- score the winner on train + test for the honest before/after
    on_stage("scoring the winner on train + test")
    win_train = _grade_candidate(train, winner["prompt"], grader["model"],
                                 on_tick=on_tick, cancel=cancel)
    win_test = _grade_candidate(test, winner["prompt"], grader["model"],
                                on_tick=on_tick, cancel=cancel)
    win_val = _grade_candidate(val, winner["prompt"], grader["model"],
                               on_tick=_noop, cancel=cancel)
    win_cells = {**win_train, **win_val, **win_test}
    win_v = _verdict_map(win_cells)
    winner_scores = {
        "train": _score(train, win_v),
        "val": _score(val, win_v),
        "test": _score(test, win_v),
    }
    test_flips = _flips(test, baseline_v, win_v)

    winner_verdicts = [
        {
            "slug": r.slug, "variant": r.variant, "index": r.index,
            "verdict": win_cells[r.id]["verdict"],
            "reason": (win_cells[r.id].get("reason") or "")[:600],
        }
        for r in rows if r.id in win_cells
    ]

    record = {
        "id": uuid.uuid4().hex[:12],
        "mode_id": mode_id,
        "mode_name": mode["name"],
        "grader": grader_name,
        "model": grader["model"],
        "optimizer_model": optimizer_model,
        "created_at": _now(),
        "seed": seed,
        "split_fractions": list(_fractions()),
        "dataset_size": len(rows),
        "split_sizes": splits["sizes"],
        "split": {
            "train": [r.id for r in train],
            "val": [r.id for r in val],
            "test": [r.id for r in test],
        },
        "current_prompt": grader["prompt"],
        "baseline": baseline,
        "candidates": [
            {k: v for k, v in c.items() if k != "prompt"} | {"has_prompt": bool(c.get("prompt"))}
            for c in candidates
        ],
        "winner_id": winner["id"],
        "winner": {
            "prompt": winner["prompt"],
            "themes": winner.get("themes", ""),
            "summary": winner.get("summary", ""),
            "scores": winner_scores,
            "test_flips": test_flips,
            "verdicts": winner_verdicts,
        },
        "status": "proposed",
    }
    save_run(record)
    return record


# --------------------------------------------------------------- run store
def _run_path(run_id: str) -> Path:
    return config.RECALIBRATIONS_DIR / f"{run_id}.json"


def save_run(record: Dict) -> None:
    config.RECALIBRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = _run_path(record["id"])
    fd, tmp = tempfile.mkstemp(dir=str(config.RECALIBRATIONS_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def load_run(run_id: str) -> Dict:
    path = _run_path(run_id)
    if not path.exists():
        raise RecalibrateError(f"recalibration run '{run_id}' not found")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _iter_runs() -> List[Dict]:
    if not config.RECALIBRATIONS_DIR.is_dir():
        return []
    out = []
    for p in config.RECALIBRATIONS_DIR.glob("*.json"):
        try:
            with p.open("r", encoding="utf-8") as f:
                out.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
    return out


def latest_run(mode_id: int) -> Optional[Dict]:
    runs = [r for r in _iter_runs() if r.get("mode_id") == mode_id]
    if not runs:
        return None
    runs.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return runs[0]


def run_summary(record: Dict) -> Dict:
    """Strip the heavy winner.verdicts list for list views."""
    rec = dict(record)
    winner = dict(rec.get("winner") or {})
    winner.pop("verdicts", None)
    rec["winner"] = winner
    return rec


# --------------------------------------------------------------- adopt / reject
def adopt_run(run_id: str) -> Dict:
    """Write the winning prompt to prompt.md and persist its verdicts.

    The grader is left uncommitted for the operator to Commit & push."""
    rec = load_run(run_id)
    if rec.get("status") != "proposed":
        raise RecalibrateError(f"run '{run_id}' is '{rec.get('status')}', not awaiting review")
    mode_id = rec["mode_id"]
    grader_name = rec["grader"]
    prompt = (rec.get("winner") or {}).get("prompt")
    if not prompt:
        raise RecalibrateError("run has no winning prompt to adopt")

    ai_grader.write_grader_prompt(grader_name, prompt)
    grader = ai_grader.load_grader(grader_name)  # recomputes prompt_hash from new prompt.md
    now = _now()
    entries: List[Tuple[str, str, int, Dict]] = []
    for v in (rec.get("winner") or {}).get("verdicts", []):
        if v.get("verdict") not in _GRADES:
            continue
        cell = {
            "verdict": v["verdict"],
            "reason": v.get("reason", ""),
            "grader": grader_name,
            "model": grader["model"],
            "prompt_hash": grader["prompt_hash"],
            "graded_at": now,
            "recalibrated_from": run_id,
        }
        entries.append((v["slug"], v["variant"], int(v["index"]), cell))
    persisted = ai_grader.store_ai_verdicts(mode_id, entries)
    # Drop every other AI verdict for this mode (graded under the old prompt) so the
    # UI/report never shows stale scores. The just-persisted dataset cells carry the
    # new prompt_hash and are kept; the rest become ungraded until a re-grade.
    cleared = ai_grader.clear_stale_ai_grades_for_mode(mode_id, grader["prompt_hash"])

    rec["status"] = "approved"
    rec["adopted_at"] = now
    rec["persisted"] = persisted
    rec["cleared"] = cleared
    save_run(rec)
    return {
        "run_id": run_id,
        "mode_id": mode_id,
        "grader_name": grader_name,
        "model": grader["model"],
        "prompt": prompt,
        "persisted": persisted,
        "cleared": cleared,
        "uncommitted": True,
    }


def reject_run(run_id: str) -> Dict:
    rec = load_run(run_id)
    if rec.get("status") == "approved":
        raise RecalibrateError("run was already adopted")
    rec["status"] = "rejected"
    rec["rejected_at"] = _now()
    save_run(rec)
    return {"run_id": run_id, "status": "rejected"}


# --------------------------------------------------------------- jobs
# In-memory only: a single background recalibration at a time, polled by the UI.
_jobs: Dict[str, Dict] = {}
_jobs_lock = threading.Lock()
_active_job_id: Optional[str] = None


def _public_job(job: Optional[Dict]) -> Optional[Dict]:
    if not job:
        return None
    return {k: v for k, v in job.items() if not k.startswith("_")}


def get_job(job_id: str) -> Optional[Dict]:
    with _jobs_lock:
        return _public_job(_jobs.get(job_id))


def list_jobs() -> Dict:
    with _jobs_lock:
        jobs = [_public_job(j) for j in _jobs.values()]
        active = _public_job(_jobs.get(_active_job_id)) if _active_job_id else None
    jobs.sort(key=lambda j: j["started_at"], reverse=True)
    return {"jobs": jobs[:20], "active": active}


def active_job_for_mode(mode_id: int) -> Optional[Dict]:
    with _jobs_lock:
        job = _jobs.get(_active_job_id) if _active_job_id else None
        if job and job["mode_id"] == mode_id and job["status"] in ("running", "cancelling"):
            return _public_job(job)
    return None


def cancel_job(job_id: str) -> Optional[Dict]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        if job["status"] == "running":
            job["_cancel"].set()
            job["status"] = "cancelling"
        return _public_job(job)


def start_recalibration(mode_id: int) -> Dict:
    """Start a background recalibration. Only one runs at a time (returns the
    active job unchanged if one is already in flight)."""
    if mode_id not in MODE_GRADERS:
        raise RecalibrateError(f"mode #{mode_id} has no VLM grader")
    st = ai_grader.status()
    if not st["llm_configured"]:
        raise ai_grader.AIGraderError("ANTHROPIC_API_KEY is not set in .env")
    if not st["graders_dir_ok"]:
        raise ai_grader.AIGraderError("graders dir not found")
    pv = estimate(mode_id)
    if not pv["eligible"]:
        raise RecalibrateError(pv.get("reason") or "not enough labeled data to recalibrate")

    global _active_job_id
    with _jobs_lock:
        active = _jobs.get(_active_job_id) if _active_job_id else None
        if active and active["status"] in ("running", "cancelling"):
            return _public_job(active)
        job_id = uuid.uuid4().hex[:12]
        job = {
            "id": job_id,
            "mode_id": mode_id,
            "mode_name": MODE_BY_ID[mode_id]["name"],
            "grader": MODE_GRADERS[mode_id],
            "status": "running",
            "stage": "starting",
            "message": "starting",
            "total": pv.get("estimated_calls") or 0,
            "done": 0,
            "dataset_size": pv.get("dataset_size"),
            "run_id": None,
            "error": None,
            "started_at": _now(),
            "finished_at": None,
            "_cancel": threading.Event(),
        }
        _jobs[job_id] = job
        _active_job_id = job_id

    threading.Thread(target=_run_job, args=(job_id,), daemon=True).start()
    return _public_job(job)


def _run_job(job_id: str) -> None:
    global _active_job_id
    job = _jobs[job_id]
    cancel = job["_cancel"]

    def on_total(t: int) -> None:
        with _jobs_lock:
            job["total"] = t

    def on_tick(n: int = 1) -> None:
        with _jobs_lock:
            job["done"] += n

    def on_stage(s: str) -> None:
        with _jobs_lock:
            job["stage"] = s
            job["message"] = s

    try:
        rec = _run(job["mode_id"], cancel=cancel, on_total=on_total,
                   on_tick=on_tick, on_stage=on_stage)
        with _jobs_lock:
            if cancel.is_set():
                job["status"] = "cancelled"
            else:
                job["status"] = "done"
                job["run_id"] = rec["id"]
                job["stage"] = "done"
                job["message"] = "proposal ready for review"
    except _Cancelled:
        with _jobs_lock:
            job["status"] = "cancelled"
    except (RecalibrateError, ai_grader.AIGraderError) as exc:
        with _jobs_lock:
            job["status"] = "error"
            job["error"] = str(exc)
    except Exception as exc:  # noqa: BLE001 - never let the worker die silently
        with _jobs_lock:
            job["status"] = "error"
            job["error"] = str(exc)
    finally:
        with _jobs_lock:
            job["finished_at"] = _now()
            if _active_job_id == job_id:
                _active_job_id = None
