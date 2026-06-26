# AGENTS.md — working in the Import Slide-Pair Grader

Orientation for an AI agent (or new dev) making changes in this repo: the fast path to
being productive without breaking things. For product/usage + team setup see `README.md`;
for env vars see `.env.example`; for design docs see `docs/`.

## What this project is
A **local** tool to grade PPTX→Gamma slide-import quality across **24 "failure modes"**
(the *Import Evals Taxonomy / PSSL*). For each deck it shows the original **input** slide
beside an **output** slide and captures a Pass/Borderline/Fail grade + note per mode.
Optionally a VLM ("AI") grader produces verdicts that are compared against the human grades
in agreement **reports**. Data is shared across the team via one Google Drive folder — there
is no hosted server.

Every deck has two output **variants**, graded independently:
- `ideal` → label **"Deck Doctor"** (`ideal_output.pdf`)
- `current` → label **"Current Import"** (`current_output.pdf`)

## TL;DR dev loop (READ THIS FIRST)
- One-time setup: `./setup.sh` (creates `backend/.venv`, pip installs, `npm install`,
  `npm run build`). Then `cp .env.example .env`.
- Run the whole app: `./run.sh` → http://127.0.0.1:8000 (FastAPI serves API + built UI +
  images on one port; it sources `.env`).
- **`run.sh` runs uvicorn with NO `--reload`** → after **backend** edits you MUST restart
  `./run.sh`.
- **`run.sh` serves `frontend/dist`** → after **frontend** edits you MUST run `npm run build`
  (in `frontend/`) for them to appear there.
- Fast iteration (hot reload, two ports):
  - backend: `cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000`
  - frontend: `cd frontend && npm run dev` → Vite on :5173, proxies `/api` → :8000.

## Stack
Backend = FastAPI (Python 3.10+, PyMuPDF for PDF→PNG). Frontend = React 18 + Vite +
TailwindCSS + lucide-react. **No router lib, no state-management lib, no test framework.**
The API client is a thin `fetch` wrapper.

## Architecture

### Backend (`backend/app/`)
| File | Responsibility |
|---|---|
| `main.py` | FastAPI app: ALL routes + Pydantic models + static mounts. **Source of truth for the API.** |
| `config.py` | Paths + env vars (`SLIDE_GRADER_DATA`, cache, `PORT`, AI-grader settings), `VARIANTS`, `ensure_dirs()`. |
| `modes.py` | The 24-mode registry: `MODES`, `MODE_BY_ID`, `MODE_GRADERS` (mode→VLM grader), `MODE_GRADER_NOTES`, `ELEMENT_ORDER`, `GRADES`, pair/deck id lists. |
| `storage.py` | Deck scanning, PNG render coordination, annotation persistence (atomic temp-file writes + per-deck `RLock`), deck list/detail, `sync_annotation`, mode-description store. |
| `pdf_split.py` | `pdf_page_count`, `render_pdf_to_pngs` (PyMuPDF). |
| `ai_grader.py` | VLM grader integration: load grader prompt, grade a pair **in-process via `llm.py`**, bulk/background jobs, the `ai_grades/` store, `status()`, prompt read/write, counts. Optional (needs `ANTHROPIC_API_KEY`). |
| `reports.py` | Read-only per-mode human-vs-AI **agreement report** (distributions, confusion matrix, Cohen's κ, disagreements). |
| `recalibrate.py` | Grader **recalibration**: pool human labels, split train/val/test, generate N candidate prompts, score on a held-out test set, save runs to `recalibrations/`; `adopt_run` writes `prompt.md`. |
| `export.py` | `consolidated.json` + tidy/long `tidy.csv` into `<data>/exports/`. |
| `grader_author.py` | LLM-authors/regenerates a grader's `prompt.md` from a mode description. |
| `gitutil.py` | Git status/commit/push scoped to the graders dir (committing regenerated prompts). |
| `llm.py` | Direct **Anthropic** vision/text client (stdlib `urllib`, no SDK). Runs grader rubrics in-process; used by `ai_grader`, `recalibrate`, `grader_author`. Replaces the old eval-server. |

### Frontend (`frontend/src/`)
| File | Responsibility |
|---|---|
| `App.jsx` | Root. View state machine (`dashboard` / `deck` / `align` / `report` / `directory`), header nav + variant switcher + Export + toast. **Add new top-level pages here.** |
| `api.js` | Thin REST wrapper (`api.getModes()`, …). **Add new endpoints here.** |
| `constants.js` | Shared UI constants (e.g. AI verdict chips/labels). |
| `index.css` | Tailwind entry + a few globals (e.g. `thin-scroll`). |
| `components/Dashboard.jsx` | Deck grid/cards, progress, AI run controls. |
| `components/DeckView.jsx` | The grading screen for one deck+variant (slide pairs, viewer, grading rail). |
| `components/AlignView.jsx` | Align mode: drop extra output pages to fix a misaligned deck (1:1 input↔output). |
| `components/ModePanel.jsx` | Per-mode grade buttons + note (the grading rail). |
| `components/ModeFilter.jsx` | View-only failure-mode filter (session-only, never affects data). |
| `components/ImageViewer.jsx` | Synchronized side-by-side zoom/pan. |
| `components/ReportView.jsx` | Agreement report page. |
| `components/ReportPdfDocument.jsx` | PDF export of one agreement report (lazy-loaded `@react-pdf/renderer`). |
| `components/ModeDirectory.jsx` | Failure-mode directory: editable descriptions + read-only grader prompts + reinitialize/commit/**recalibrate** grader. |
| `components/RecalibratePanel.jsx` | Recalibration UI inside the directory: preview, run/poll a job, review a run, adopt/reject. |
| `components/AiStatusDot.jsx` | AI availability indicator. |

## Domain model
- **Failure modes:** 24, in `modes.py`. 22 have a VLM grader (`MODE_GRADERS`); #18 (deck-level
  brand color) and #21 (cross-slide) have none. Fields: `id, name, element, dimension,
  severity, level` where `level` ∈ {`pair`, `deck`}.
- **Variants:** `ideal` / `current` (`config.VARIANTS`). Almost everything is keyed by
  `(slug, variant)`.
- **Human grades:** `ungraded | pass | borderline | fail` (+ free-text note).
  **AI verdicts:** `pass | borderline | fail | na`.
- **AI grader (optional):** reads vendored grader prompts from `backend/graders/` (override
  with `IMPORT_EVALS_GRADERS_DIR`) and grades **in-process** by calling Anthropic's Messages API
  directly (`backend/app/llm.py`, `ANTHROPIC_API_KEY`) — no eval-server or gamma monorepo. If the
  key is missing it degrades gracefully (status dot red, run buttons disabled). Verdicts are
  written to the shared `ai_grades/` folder, so whoever has a key runs them and results sync to
  everyone. Never assume it's available.

## Data & storage (under `SLIDE_GRADER_DATA`, default `./data`)
| What | Where |
|---|---|
| Source PDFs (added by hand) | `<data>/decks/<slug>/{input,ideal_output,current_output}.pdf` |
| Human annotations (autosaved) | `<data>/annotations/<slug>.json` (per-variant, schema v2) |
| AI grades | `<data>/ai_grades/<slug>__<variant>.json` |
| Mode descriptions | `<data>/mode_descriptions.json` |
| Exports | `<data>/exports/{consolidated.json,tidy.csv}` |
| Rendered PNGs (**local cache, never synced**) | `.cache/renders/<slug>/{input,ideal,current}/NNN.png` → served at `/images/...` |

Persistence pattern: read-modify-write JSON under a per-deck `RLock`, written atomically
(`tempfile` + `os.replace`). One file per deck; Drive is last-write-wins (the team "divides
decks").

## API surface (`main.py` is authoritative)
- **Registry/decks:** `GET /api/modes`, `GET /api/mode-directory`, `GET /api/decks`,
  `POST /api/rescan`, `GET /api/decks/{slug}/{variant}`.
- **Grading:** `PUT /api/decks/{slug}/{variant}/pairs/{index}`,
  `PUT /api/decks/{slug}/{variant}/deck-level`.
- **Directory/graders:** `PUT /api/modes/{id}/description`,
  `GET /api/modes/{id}/grader-score-count`, `POST /api/modes/{id}/reinitialize-grader`,
  `POST /api/modes/{id}/commit-grader`, `GET /api/git/status`.
- **AI grading:** `GET /api/ai-grades/status`, `POST /api/ai-grades/run`,
  `GET /api/ai-grades/jobs[/{id}]`, `POST /api/ai-grades/jobs/{id}/cancel`,
  `GET /api/ai-grades/{slug}/{variant}`,
  `POST /api/ai-grades/{slug}/{variant}/pairs/{index}/run`.
- **Recalibration:** `GET /api/modes/{id}/recalibration[/preview]`,
  `POST /api/modes/{id}/recalibration/run`, `GET /api/recalibration/jobs/{id}`,
  `POST /api/recalibration/jobs/{id}/cancel`, `GET /api/recalibration/runs/{id}`,
  `POST /api/recalibration/runs/{id}/{adopt,reject}`.
- **Reports/export:** `GET /api/reports/mode/{id}?variant=`, `POST /api/export`.
- **Static:** `/images` (render cache), `/` (built UI).

## Conventions & guardrails
- **Match existing style.** Backend: small focused modules, plain `dict` responses,
  `_require_deck` / `_require_variant` guards, atomic writes + locks. Frontend: dark Tailwind
  theme (slate/indigo), lucide icons, thin `api.js`; don't add libraries unless necessary.
- **New top-level page:** add a `view.name` branch + header button in `App.jsx` (mirror how
  `report` / `directory` are wired), plus a component in `components/`.
- **New endpoint:** add it in `main.py`, put logic in the relevant module (or a new one),
  expose it in `api.js`.
- **Restart/rebuild after edits** per the TL;DR (backend = restart `run.sh`; frontend served
  by `run.sh` = `npm run build`).
- **Never write test data into the shared `SLIDE_GRADER_DATA` folder.** For backend checks,
  point `SLIDE_GRADER_DATA` at a `mktemp -d` directory.
- **Don't add PNGs to the data dir** — renders are a local-only cache.
- **No automated test suite** — verify manually (build the UI, restart/curl the API, click
  through the affected page).
- Don't add/remove code comments wholesale; keep them purposeful as in the existing files.

## Verifying a change
- Backend import check: `backend/.venv/bin/python -c "from app import main"`.
- Hit a route: `curl -s 127.0.0.1:8000/api/...` (run against a temp `SLIDE_GRADER_DATA` if it
  writes data).
- Frontend: `cd frontend && npm run build` (catches JSX/build errors), then exercise via
  `npm run dev` (:5173) or the built app at :8000.

## Pointers
- `README.md` — product overview, team/Drive setup, data conventions, keyboard, export format.
- `.env.example` — every env var, with explanations (incl. the optional AI-grader setup).
- `docs/recalibration-design.md`, `docs/alignment-design.md` — design docs for features that are
  now **implemented** (grader recalibration + deck alignment).
- `scripts/seed_drive.sh`, `scripts/split_pdf.py` — data helper scripts.
