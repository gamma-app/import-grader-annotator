# AGENTS.md — working in the Import Slide-Pair Grader

Orientation for an AI agent (or new dev) making changes in this repo: the fast path to
being productive without breaking things. For product/usage + team setup see `README.md`;
for env vars see `.env.example`; for design docs see `docs/`.

## What this project is
A **local** tool to grade PPTX→Gamma slide-import quality across a set of **"failure modes"**
(the *Import Evals Taxonomy / PSSL* — seeded with **24**, editable in-app). For each deck it shows the original **input** slide
beside an **output** slide and captures a Pass/Borderline/Fail grade + note per mode.
Optionally a VLM ("AI") grader produces verdicts that are compared against the human grades
in agreement **reports**. Data is shared across the team via one Google Drive folder — there
is no hosted server.

Every deck has three output **variants**, graded independently:
- `ideal` → label **"Deck Doctor"** (`ideal_output.pdf`)
- `current` → label **"Current Import"** (`current_output.pdf`)
- `programmatic` → label **"Programmatic Import"** (`programmatic_output.pdf`)

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
The API client is a thin `fetch` wrapper. The optional **PPTX importer** adds Playwright
(headless Chromium) + LibreOffice (`soffice`) — both lazy/runtime, so the app runs without them.

## Architecture

### Backend (`backend/app/`)
| File | Responsibility |
|---|---|
| `main.py` | FastAPI app: ALL routes + Pydantic models + static mounts. **Source of truth for the API.** |
| `config.py` | Paths + env vars (`SLIDE_GRADER_DATA`, cache, `PORT`, AI-grader settings), `VARIANTS`, `MODES_PATH` (the `modes.json` registry file), `ensure_dirs()`. |
| `modes.py` | The failure-mode **registry**, data-backed by `<data>/modes.json` (seeded from the built-in 24 `_DEFAULT_*` taxonomy/graders/notes on first use, shared via Drive). Single read/write surface — everything calls **accessors at call time** (`all_modes`/`enabled_modes`/`mode_by_id`/`pair_mode_ids`/`deck_mode_ids`/`mode_graders`/`grader_name`/`element_order`) + **mutators** (`add_mode`/`update_mode`/`set_enabled`/`set_grader`/`delete_mode`, raising `RegistryError`). Also `ELEMENT_ORDER`, `GRADES`. |
| `storage.py` | Deck scanning, PNG render coordination, annotation persistence (atomic temp-file writes + per-deck `RLock`), deck list/detail, `sync_annotation` (preserves any recorded cell whose mode still exists, so soft-disable + level edits are lossless), mode-description store, `count_human_grades_for_mode` (delete-guard). |
| `pdf_split.py` | `pdf_page_count`, `render_pdf_to_pngs` (PyMuPDF). |
| `ai_grader.py` | VLM grader integration: load grader prompt, grade a pair **in-process via `llm.py`**, bulk/background jobs, the `ai_grades/` store, `status()`, prompt read/write, counts. Optional (needs `ANTHROPIC_API_KEY`). |
| `reports.py` | Read-only per-mode human-vs-AI **agreement report** (distributions, confusion matrix, Cohen's κ, disagreements). |
| `recalibrate.py` | Grader **recalibration**: pool human labels, split train/val/test, generate N candidate prompts, score on a held-out test set, save runs to `recalibrations/`; `adopt_run` writes `prompt.md`. |
| `export.py` | `consolidated.json` + tidy/long `tidy.csv` into `<data>/exports/`. |
| `grader_author.py` | LLM-authors/regenerates a grader's `prompt.md` from a mode description. |
| `gitutil.py` | Git status/commit/push scoped to the graders dir (committing regenerated prompts). |
| `llm.py` | Direct **Anthropic** vision/text client (stdlib `urllib`, no SDK). Runs grader rubrics in-process; used by `ai_grader`, `recalibrate`, `grader_author`. Replaces the old eval-server. |
| `importer.py` | **PPTX import automation**: PPTX→`input.pdf` (headless LibreOffice `soffice`) + drives gamma.app in a headless browser (Playwright, sync API in a worker thread) to produce `current_output.pdf`, then places + renders the deck. Reproduces the manual click-path: **Import → AI import → upload → Visual import → 3× Continue** (import-settings, pick-a-theme, then the slide-**preview** Continue that calls `generate()`; that one is disabled until slides finish importing, so it's polled) → wait for `/docs/<id>` → **Share → Export → Export to PDF** (the `Export` tab is a button sitting next to `Export 0 cards`/`Export…` decoys, so clicks use exact-name-first + first-visible matching). Single-active background job (mirrors `ai_grader`). Gamma UI labels/step-hints/selectors are env-overridable constants (`GAMMA_*`); screenshot+DOM debug artifacts under `.cache/imports/debug/<job>/` on failure. Optional (needs `playwright`, `soffice`, a saved gamma session). |
| `gamma_login.py` | One-time interactive `python -m app.gamma_login` (headed) — captures a gamma.app Playwright `storageState` to `GAMMA_AUTH_STATE_PATH` for the importer to reuse headlessly. |

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
| `components/ModeDirectory.jsx` | Failure-mode directory: **add / edit / enable-disable / delete** modes, editable descriptions, read-only grader prompts + **generate**/reinitialize/commit/**recalibrate** grader. |
| `components/RecalibratePanel.jsx` | Recalibration UI inside the directory: preview, run/poll a job, review a run, adopt/reject. |
| `components/AiStatusDot.jsx` | AI availability indicator. |
| `components/ImportPanel.jsx` | **Import PPTX** toolbar button + upload modal + live job polling; gates on importer readiness (playwright/soffice/gamma session) and shows what's missing. |

## Domain model
- **Failure modes:** an editable registry seeded with **24** built-ins (`modes.py` → `<data>/modes.json`).
  Add custom modes, edit/disable/delete (incl. the built-ins), and give grader-less pair-level modes a
  grader from the directory. 22 built-ins ship with a VLM grader; #18 (deck-level brand color) and #21
  (cross-slide) have none. Per-mode fields: `id, name, element, dimension, severity, level, enabled,
  builtin, grader_name` where `level` ∈ {`pair`, `deck`}. **Disable** (soft) keeps stored grades and hides
  the mode from grading; **delete** (hard) is allowed only when the mode has zero stored data — else 409.
- **Variants:** `ideal` / `current` / `programmatic` (`config.VARIANTS`). Almost everything is
  keyed by `(slug, variant)`.
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
| Source PDFs (added by hand) | `<data>/decks/<slug>/{input,ideal_output,current_output,programmatic_output}.pdf` |
| Human annotations (autosaved) | `<data>/annotations/<slug>.json` (per-variant, schema v2) |
| AI grades | `<data>/ai_grades/<slug>__<variant>.json` |
| Mode descriptions | `<data>/mode_descriptions.json` |
| Failure-mode registry (taxonomy) | `<data>/modes.json` (seeded from `modes.py` defaults; shared, last-write-wins) |
| Exports | `<data>/exports/{consolidated.json,tidy.csv}` |
| Rendered PNGs (**local cache, never synced**) | `.cache/renders/<slug>/{input,ideal,current,programmatic}/NNN.png` → served at `/images/...` |
| gamma session + import scratch (**local, never synced; session is sensitive**) | `.cache/gamma_auth_state.json`, `.cache/imports/{uploads,work,debug}/` |

Persistence pattern: read-modify-write JSON under a per-deck `RLock`, written atomically
(`tempfile` + `os.replace`). One file per deck; Drive is last-write-wins (the team "divides
decks").

## API surface (`main.py` is authoritative)
- **Registry/decks:** `GET /api/modes`, `GET /api/mode-directory`, `GET /api/decks`,
  `POST /api/rescan`, `GET /api/decks/{slug}/{variant}`.
- **Grading:** `PUT /api/decks/{slug}/{variant}/pairs/{index}`,
  `PUT /api/decks/{slug}/{variant}/deck-level`.
- **Registry CRUD:** `POST /api/modes` (add custom), `PATCH /api/modes/{id}` (edit fields /
  enable-disable), `DELETE /api/modes/{id}` (hard-delete; **409** if it has stored data).
- **Directory/graders:** `PUT /api/modes/{id}/description`,
  `GET /api/modes/{id}/grader-score-count`, `POST /api/modes/{id}/reinitialize-grader`
  (also **creates** a grader for a grader-less pair-level mode),
  `POST /api/modes/{id}/commit-grader`, `GET /api/git/status`.
- **AI grading:** `GET /api/ai-grades/status`, `POST /api/ai-grades/run`,
  `GET /api/ai-grades/jobs[/{id}]`, `POST /api/ai-grades/jobs/{id}/cancel`,
  `GET /api/ai-grades/{slug}/{variant}`,
  `POST /api/ai-grades/{slug}/{variant}/pairs/{index}/run`.
- **Recalibration:** `GET /api/modes/{id}/recalibration[/preview]`,
  `POST /api/modes/{id}/recalibration/run`, `GET /api/recalibration/jobs/{id}`,
  `POST /api/recalibration/jobs/{id}/cancel`, `GET /api/recalibration/runs/{id}`,
  `POST /api/recalibration/runs/{id}/{adopt,reject}`.
- **PPTX import:** `GET /api/imports/status`, `POST /api/imports` (multipart `.pptx` upload),
  `GET /api/imports/jobs[/{id}]`, `POST /api/imports/jobs/{id}/cancel`.
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
- **No required test suite** — verify manually (build the UI, restart/curl the API, click through
  the affected page). `backend/tests/` does have plain-python unit tests for pure logic
  (`test_recalibrate.py`, `test_modes_registry.py`), runnable directly or via pytest.
- Don't add/remove code comments wholesale; keep them purposeful as in the existing files.

## Verifying a change
- Backend import check: `backend/.venv/bin/python -c "from app import main"`.
- Unit tests (pure logic): `backend/.venv/bin/python tests/test_modes_registry.py` (and
  `tests/test_recalibrate.py`).
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
