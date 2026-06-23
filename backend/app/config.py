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
# VLM grader outputs (import-evals) live beside annotations in the shared folder,
# in their own files so they never collide with the human autosave.
AI_GRADES_DIR = DATA_DIR / "ai_grades"

# Rendered PNGs are a local-only cache, kept OUT of DATA_DIR so a shared/synced
# data folder (e.g. Google Drive) never has to sync hundreds of regenerable
# images. Each machine renders its own PNGs from the shared PDFs on first open.
RENDER_CACHE_DIR = Path(
    os.environ.get("SLIDE_GRADER_CACHE") or (PROJECT_ROOT / ".cache" / "renders")
).resolve()

# Rendered slide width in pixels (height scales to preserve aspect ratio).
RENDER_WIDTH = int(os.environ.get("SLIDE_GRADER_RENDER_WIDTH", "1600"))

# --- VLM grader integration (gamma packages/import-evals via eval-server) ---
# Local eval-server (`yarn dev:eval-server` in the gamma monorepo) that runs a
# grader prompt against claude through gamma's model gateway.
EVAL_SERVER_URL = (os.environ.get("EVAL_SERVER_URL") or "http://127.0.0.1:5190").rstrip("/")
# Absolute path to the import-evals graders dir (…/packages/import-evals/graders).
# Empty until the teammate points .env at their monorepo checkout.
_graders_dir = os.environ.get("IMPORT_EVALS_GRADERS_DIR") or ""
IMPORT_EVALS_GRADERS_DIR = Path(_graders_dir).expanduser().resolve() if _graders_dir else None
# Optional model override; empty = use each grader.yml's declared model.
AI_GRADER_MODEL = os.environ.get("AI_GRADER_MODEL") or ""
# Parallel grader requests for deck / all-decks runs (matches the suite default).
AI_GRADER_CONCURRENCY = int(os.environ.get("AI_GRADER_CONCURRENCY", "3"))
# Base URL the eval-server uses to fetch this app's rendered PNGs (same machine).
SELF_BASE_URL = (os.environ.get("SLIDE_GRADER_SELF_URL") or "http://127.0.0.1:8000").rstrip("/")

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
    for d in (DECKS_DIR, ANNOTATIONS_DIR, EXPORTS_DIR, AI_GRADES_DIR, RENDER_CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)
