"""FastAPI app for the Slide-Pair Failure-Mode Grader."""
from __future__ import annotations

from typing import Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ai_grader, config, export, storage
from .modes import (
    DECK_MODE_IDS,
    ELEMENT_ORDER,
    GRADES,
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
    grade: Literal["ungraded", "pass", "borderline", "fail"] = "ungraded"
    note: str = ""


class PairUpdate(BaseModel):
    modes: Dict[str, Cell]
    annotator: Optional[str] = None


class DeckLevelUpdate(BaseModel):
    modes: Dict[str, Cell]
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
