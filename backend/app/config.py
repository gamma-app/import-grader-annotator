"""Filesystem paths and rendering settings for the Slide-Pair Grader."""
from __future__ import annotations

import os
from pathlib import Path

# Project root = slide-grader/ (this file lives at backend/app/config.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Data dir can be overridden so a teammate can point at any folder of decks.
DATA_DIR = Path(os.environ.get("SLIDE_GRADER_DATA") or (PROJECT_ROOT / "data")).resolve()
DECKS_DIR = DATA_DIR / "decks"
ANNOTATIONS_DIR = DATA_DIR / "annotations"
EXPORTS_DIR = DATA_DIR / "exports"

# Rendered PNGs are a local-only cache, kept OUT of DATA_DIR so a shared/synced
# data folder (e.g. Google Drive) never has to sync hundreds of regenerable
# images. Each machine renders its own PNGs from the shared PDFs on first open.
RENDER_CACHE_DIR = Path(
    os.environ.get("SLIDE_GRADER_CACHE") or (PROJECT_ROOT / ".cache" / "renders")
).resolve()

# Rendered slide width in pixels (height scales to preserve aspect ratio).
RENDER_WIDTH = int(os.environ.get("SLIDE_GRADER_RENDER_WIDTH", "1600"))

INPUT_PDF = "input.pdf"
INPUT_DIR = "input"

# Output variants: each deck pairs `input` against one or more outputs.
VARIANTS = [
    {"key": "ideal", "label": "Deck Doctor", "pdf": "ideal_output.pdf", "dir": "ideal"},
    {"key": "current", "label": "Current Import", "pdf": "current_output.pdf", "dir": "current"},
]
VARIANT_KEYS = [v["key"] for v in VARIANTS]
VARIANT_BY_KEY = {v["key"]: v for v in VARIANTS}
DEFAULT_VARIANT = "ideal"

# Legacy single-output layout (pre-variants), kept only for cleanup/migration.
LEGACY_OUTPUT_DIR = "output"

ANNOTATION_SCHEMA_VERSION = 2


def ensure_dirs() -> None:
    for d in (DECKS_DIR, ANNOTATIONS_DIR, EXPORTS_DIR, RENDER_CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)
