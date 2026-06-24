"""FastAPI app for the Slide-Pair Failure-Mode Grader."""
from __future__ import annotations

from typing import Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ai_grader, config, export, gitutil, grader_author, reports, storage
from .modes import (
    DECK_MODE_IDS,
    ELEMENT_ORDER,
    GRADES,
    MODE_BY_ID,
    MODE_GRADER_NOTES,
    MODE_GRADERS,
    MODES,
    PAIR_MODE_IDS,
)

config.ensure_dirs()

app = FastAPI(title="Import Slide-Pair Grader", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------- models
class Cell(BaseModel):
    grade: Literal["ungraded", "pass", "borderline", "fail", "na"] = "ungraded"
    note: str = ""


class PairUpdate(BaseModel):
    modes: Dict[str, Cell]
    annotator: Optional[str] = None


class DeckLevelUpdate(BaseModel):
    modes: Dict[str, Cell]
    annotator: Optional[str] = None


class ModeDescriptionUpdate(BaseModel):
    text: str = ""
    annotator: Optional[str] = None


class ReinitGraderRequest(BaseModel):
    annotator: Optional[str] = None


class CommitGraderRequest(BaseModel):
    message: Optional[str] = None
    annotator: Optional[str] = None


class AIRunRequest(BaseModel):
    modes: Optional[List[int]] = None  # subset of mode ids; None = all mapped modes
    force: bool = False  # re-grade even if a fresh cached result exists


class AIBulkRunRequest(BaseModel):
    scope: Literal["deck", "all"]
    variant: str
    slug: Optional[str] = None  # required when scope == "deck"
    force: bool = False


def _cells_to_dict(modes: Dict[str, Cell]) -> Dict[str, Dict]:
    return {k: v.model_dump() for k, v in modes.items()}


# ----------------------------------------------------------------- api
@app.get("/api/health")
def health() -> Dict:
    return {"status": "ok", "data_dir": str(config.DATA_DIR)}


@app.get("/api/modes")
def get_modes() -> Dict:
    return {
        "modes": MODES,
        "element_order": ELEMENT_ORDER,
        "grades": GRADES,
        "pair_mode_ids": PAIR_MODE_IDS,
        "deck_mode_ids": DECK_MODE_IDS,
        "mode_graders": MODE_GRADERS,
        "variants": config.VARIANTS,
    }


@app.get("/api/mode-directory")
def get_mode_directory() -> Dict:
    """Every failure mode + its editable description + its VLM grader prompt."""
    descs = storage.load_mode_descriptions().get("descriptions", {})
    git_state = gitutil.graders_status()
    dirty = set(git_state.get("dirty_graders") or [])
    out: List[Dict] = []
    for m in MODES:
        entry = descs.get(str(m["id"]), {})
        rec = {
            **m,
            "description": entry.get("text", ""),
            "description_updated_at": entry.get("updated_at"),
            "grader_name": None,
            "model": None,
            "prompt": None,
            "prompt_hash": None,
            "prompt_status": "no_grader",
            "prompt_message": "",
            "uncommitted": False,
        }
        grader = MODE_GRADERS.get(m["id"])
        if not grader:
            rec["prompt_message"] = MODE_GRADER_NOTES.get(m["id"], "No VLM grader for this mode.")
        else:
            rec["grader_name"] = grader
            try:
                g = ai_grader.load_grader(grader)
                rec["model"] = g["model"]
                rec["prompt"] = g["prompt"]
                rec["prompt_hash"] = g["prompt_hash"]
                rec["prompt_status"] = "ok"
                rec["uncommitted"] = grader in dirty
            except ai_grader.AIGraderError as exc:
                rec["prompt_status"] = "unavailable"
                rec["prompt_message"] = str(exc)
        out.append(rec)
    return {"modes": out, "element_order": ELEMENT_ORDER, "git": git_state}


@app.put("/api/modes/{mode_id}/description")
def put_mode_description(mode_id: int, body: ModeDescriptionUpdate) -> Dict:
    if mode_id not in MODE_BY_ID:
        raise HTTPException(status_code=404, detail=f"unknown mode #{mode_id}")
    return storage.set_mode_description(mode_id, body.text, body.annotator)


@app.get("/api/modes/{mode_id}/grader-score-count")
def grader_score_count(mode_id: int) -> Dict:
    if mode_id not in MODE_BY_ID:
        raise HTTPException(status_code=404, detail=f"unknown mode #{mode_id}")
    return {"mode_id": mode_id, "count": ai_grader.count_ai_grades_for_mode(mode_id)}


@app.post("/api/modes/{mode_id}/reinitialize-grader")
def reinitialize_grader(mode_id: int, body: ReinitGraderRequest) -> Dict:
    """Regenerate a mode's VLM grader prompt from its description, write it to the
    git-tracked prompt.md, and clear that grader's AI scores (they must be re-run).
    The new prompt is left uncommitted for the user to review then commit + push."""
    if mode_id not in MODE_BY_ID:
        raise HTTPException(status_code=404, detail=f"unknown mode #{mode_id}")
    try:
        gen = grader_author.generate_prompt(mode_id)
    except grader_author.GraderAuthorError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    ai_grader.write_grader_prompt(gen["grader_name"], gen["prompt"])
    cleared = ai_grader.clear_ai_grades_for_mode(mode_id)
    return {
        "mode_id": mode_id,
        "grader_name": gen["grader_name"],
        "model": gen["model"],
        "prompt": gen["prompt"],
        "cleared": cleared,
        "latency_ms": gen.get("latency_ms"),
        "uncommitted": True,
    }


@app.post("/api/modes/{mode_id}/commit-grader")
def commit_grader(mode_id: int, body: CommitGraderRequest) -> Dict:
    """Commit + push this mode's grader prompt to GitHub. Scoped to the grader's
    files via a pathspec so unrelated working-tree changes are never swept in."""
    if mode_id not in MODE_BY_ID:
        raise HTTPException(status_code=404, detail=f"unknown mode #{mode_id}")
    grader = MODE_GRADERS.get(mode_id)
    if not grader:
        raise HTTPException(status_code=400, detail=f"mode #{mode_id} has no VLM grader")
    mode = MODE_BY_ID[mode_id]
    message = (body.message or "").strip() or f'graders: reinitialize "{mode["name"]}" prompt (#{mode_id})'
    res = gitutil.commit_and_push([grader], message)
    if res.get("error") and not res.get("committed"):
        raise HTTPException(status_code=502, detail=res["error"])
    return {"mode_id": mode_id, "grader_name": grader, **res}


@app.get("/api/git/status")
def git_status() -> Dict:
    """Git state of the graders dir (branch, ahead/behind, uncommitted graders)."""
    return gitutil.graders_status()


@app.get("/api/decks")
def get_decks() -> Dict:
    decks = storage.list_decks()
    n_modes = len(ai_grader.gradeable_pair_modes())
    for d in decks:
        for vkey, stats in d.get("variants", {}).items():
            counts = ai_grader.store_counts(d["slug"], vkey)
            stats["ai_graded"] = counts["graded"]
            stats["ai_errors"] = counts["errors"]
            stats["ai_total"] = stats.get("pair_count", 0) * n_modes
    return {"decks": decks}


@app.post("/api/rescan")
def rescan() -> Dict:
    slugs = storage.list_slugs()
    for slug in slugs:
        storage.ensure_rendered(slug, force=True)
        storage.sync_annotation(slug)
    return {"rescanned": len(slugs), "decks": storage.list_decks()}


def _require_deck(slug: str) -> None:
    if not storage.deck_dir(slug).is_dir():
        raise HTTPException(status_code=404, detail=f"deck '{slug}' not found")


def _require_variant(variant: str) -> None:
    if variant not in config.VARIANT_BY_KEY:
        raise HTTPException(status_code=404, detail=f"unknown variant '{variant}'")


@app.get("/api/decks/{slug}/{variant}")
def get_deck(slug: str, variant: str) -> Dict:
    _require_deck(slug)
    _require_variant(variant)
    return storage.get_deck_detail(slug, variant)


@app.put("/api/decks/{slug}/{variant}/pairs/{index}")
def put_pair(slug: str, variant: str, index: int, body: PairUpdate) -> Dict:
    _require_deck(slug)
    _require_variant(variant)
    try:
        return storage.update_pair(slug, variant, index, _cells_to_dict(body.modes), body.annotator)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.put("/api/decks/{slug}/{variant}/deck-level")
def put_deck_level(slug: str, variant: str, body: DeckLevelUpdate) -> Dict:
    _require_deck(slug)
    _require_variant(variant)
    return {"deck_level": storage.update_deck_level(slug, variant, _cells_to_dict(body.modes), body.annotator)}


# ----------------------------------------------------------------- ai graders
@app.get("/api/ai-grades/status")
def ai_status() -> Dict:
    return ai_grader.status()


# NOTE: the /run and /jobs routes are declared before /{slug}/{variant} so the
# 2-segment "/jobs/{job_id}" path isn't captured as slug="jobs".
@app.post("/api/ai-grades/run")
def run_ai_bulk(body: AIBulkRunRequest) -> Dict:
    _require_variant(body.variant)
    if body.scope == "deck":
        if not body.slug:
            raise HTTPException(status_code=400, detail="scope 'deck' requires a slug")
        _require_deck(body.slug)
    try:
        return ai_grader.start_run(body.scope, body.variant, slug=body.slug, force=body.force)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ai_grader.AIGraderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/ai-grades/jobs")
def list_ai_jobs() -> Dict:
    return ai_grader.list_jobs()


@app.get("/api/ai-grades/jobs/{job_id}")
def get_ai_job(job_id: str) -> Dict:
    job = ai_grader.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"job '{job_id}' not found")
    return job


@app.post("/api/ai-grades/jobs/{job_id}/cancel")
def cancel_ai_job(job_id: str) -> Dict:
    job = ai_grader.cancel_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"job '{job_id}' not found")
    return job


@app.get("/api/ai-grades/{slug}/{variant}")
def get_ai_grades(slug: str, variant: str) -> Dict:
    _require_deck(slug)
    _require_variant(variant)
    return ai_grader.get_ai_grades(slug, variant)


@app.post("/api/ai-grades/{slug}/{variant}/pairs/{index}/run")
def run_ai_pair(slug: str, variant: str, index: int, body: AIRunRequest) -> Dict:
    _require_deck(slug)
    _require_variant(variant)
    try:
        return ai_grader.grade_pair(slug, variant, index, modes=body.modes, force=body.force)
    except ai_grader.AIGraderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/reports/mode/{mode_id}")
def get_mode_report(mode_id: int, variant: str) -> Dict:
    """Human-vs-AI agreement report for one pair-level mode + variant."""
    _require_variant(variant)
    if mode_id not in MODE_GRADERS:
        raise HTTPException(status_code=404, detail=f"mode #{mode_id} has no AI grader")
    return reports.mode_report(mode_id, variant)


@app.post("/api/export")
def post_export() -> Dict:
    return export.run_export()


# --------------------------------------------------- static (images + SPA)
app.mount("/images", StaticFiles(directory=str(config.RENDER_CACHE_DIR)), name="images")

_frontend_dist = config.PROJECT_ROOT / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
