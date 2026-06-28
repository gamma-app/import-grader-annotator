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
# Grader recalibration run records (audit + reproducibility), shared like
# annotations so a teammate can review a past run.
RECALIBRATIONS_DIR = DATA_DIR / "recalibrations"

# Human-authored, editable descriptions for each failure mode (shared like
# annotations). Keyed by mode id; the taxonomy itself lives in modes.py.
MODE_DESCRIPTIONS_PATH = DATA_DIR / "mode_descriptions.json"

# NOTE: regenerated VLM grader prompts are NOT stored here. They are the single
# source of truth in git at backend/graders/<name>/prompt.md, rewritten in place
# by a reinit and committed/pushed from the tool (see gitutil.py).

# Rendered PNGs are a local-only cache, kept OUT of DATA_DIR so a shared/synced
# data folder (e.g. Google Drive) never has to sync hundreds of regenerable
# images. Each machine renders its own PNGs from the shared PDFs on first open.
RENDER_CACHE_DIR = Path(
    os.environ.get("SLIDE_GRADER_CACHE") or (PROJECT_ROOT / ".cache" / "renders")
).resolve()

# Rendered slide width in pixels (height scales to preserve aspect ratio).
RENDER_WIDTH = int(os.environ.get("SLIDE_GRADER_RENDER_WIDTH", "1600"))

# --- VLM grader integration (gamma's import-evals graders, run in-process) ---
# Grading runs IN-PROCESS via app/llm.py, which reads the rendered PNGs and calls
# Anthropic's Messages API directly (see the ANTHROPIC_* settings below).
# EVAL_SERVER_URL is legacy/unused — grading no longer routes through gamma's
# eval-server — and is kept only for backward compatibility with older .env files.
EVAL_SERVER_URL = (os.environ.get("EVAL_SERVER_URL") or "http://127.0.0.1:5190").rstrip("/")
# Graders are vendored under backend/graders/ (prompt.md + grader.yml). The env
# var can still repoint elsewhere (e.g. a gamma checkout); default is the
# vendored copy so grading needs no external dependency.
_graders_dir = os.environ.get("IMPORT_EVALS_GRADERS_DIR") or ""
IMPORT_EVALS_GRADERS_DIR = (
    Path(_graders_dir).expanduser().resolve()
    if _graders_dir
    else (PROJECT_ROOT / "backend" / "graders")
)
# Optional model override; empty = use each grader.yml's declared model.
AI_GRADER_MODEL = os.environ.get("AI_GRADER_MODEL") or ""

# Anthropic API - the grader rubrics target claude. Key read from .env (copied
# from gamma's .envrc). This in-repo client replaces the gamma eval-server.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY") or ""
ANTHROPIC_BASE_URL = (os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").rstrip("/")
ANTHROPIC_VERSION = os.environ.get("ANTHROPIC_VERSION") or "2023-06-01"
# Cap on a grader response (verdict + short reason).
AI_GRADER_MAX_TOKENS = int(os.environ.get("AI_GRADER_MAX_TOKENS", "1024"))
# Parallel grader requests for deck / all-decks runs (matches the suite default).
AI_GRADER_CONCURRENCY = int(os.environ.get("AI_GRADER_CONCURRENCY", "3"))
# Legacy/unused: the base URL the old eval-server used to fetch this app's rendered
# PNGs. In-process grading reads PNGs straight off disk, so this is ignored now.
SELF_BASE_URL = (os.environ.get("SLIDE_GRADER_SELF_URL") or "http://127.0.0.1:8000").rstrip("/")

# --- Grader recalibration (optimize a grader prompt from human labels) ---
# Optimizer model that writes candidate prompts; empty = use the grader's own model.
RECALIBRATE_MODEL = os.environ.get("RECALIBRATE_MODEL") or ""
# Number of independent, diverse candidate prompts generated per run.
RECALIBRATE_CANDIDATES = int(os.environ.get("RECALIBRATE_CANDIDATES", "5"))
# Train/validation/test split fractions (comma-separated; train is the remainder).
RECALIBRATE_SPLIT = os.environ.get("RECALIBRATE_SPLIT") or "0.6,0.2,0.2"
# Temperature for candidate diversity. Grading itself always runs at 0.0.
RECALIBRATE_TEMPERATURE = float(os.environ.get("RECALIBRATE_TEMPERATURE", "0.7"))
# RNG seed for the split + case sampling (reproducible runs).
RECALIBRATE_SEED = int(os.environ.get("RECALIBRATE_SEED", "1234"))
# Per candidate: how many disagreements get images (K) + correct-case anchors (M).
RECALIBRATE_IMAGE_CASES = int(os.environ.get("RECALIBRATE_IMAGE_CASES", "12"))
RECALIBRATE_ANCHORS = int(os.environ.get("RECALIBRATE_ANCHORS", "5"))
# Token cap for the optimizer's {themes, prompt} JSON response.
RECALIBRATE_MAX_TOKENS = int(os.environ.get("RECALIBRATE_MAX_TOKENS", "4096"))
# Smallest dataset (pooled labeled pairs) a recalibration will run on.
RECALIBRATE_MIN_DATASET = int(os.environ.get("RECALIBRATE_MIN_DATASET", "10"))

INPUT_PDF = "input.pdf"
INPUT_DIR = "input"

# Output variants: each deck pairs `input` against one or more outputs.
VARIANTS = [
    {"key": "ideal", "label": "Deck Doctor", "pdf": "ideal_output.pdf", "dir": "ideal"},
    {"key": "current", "label": "Current Import", "pdf": "current_output.pdf", "dir": "current"},
    {"key": "programmatic", "label": "Programmatic Import", "pdf": "programmatic_output.pdf", "dir": "programmatic"},
]
VARIANT_KEYS = [v["key"] for v in VARIANTS]
VARIANT_BY_KEY = {v["key"]: v for v in VARIANTS}
DEFAULT_VARIANT = "ideal"

# Legacy single-output layout (pre-variants), kept only for cleanup/migration.
LEGACY_OUTPUT_DIR = "output"

ANNOTATION_SCHEMA_VERSION = 2


def ensure_dirs() -> None:
    for d in (DECKS_DIR, ANNOTATIONS_DIR, EXPORTS_DIR, AI_GRADES_DIR, RECALIBRATIONS_DIR, RENDER_CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)
