"""FastAPI app for the Slide-Pair Failure-Mode Grader."""
from __future__ import annotations

from typing import Dict, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, export, storage
from .modes import (
    DECK_MODE_IDS,
    ELEMENT_ORDER,
    GRADES,
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
        "variants": config.VARIANTS,
    }


@app.get("/api/decks")
def get_decks() -> Dict:
    return {"decks": storage.list_decks()}


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
