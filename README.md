# Import Slide-Pair Grader

A local tool for manually annotating PPTX→Gamma import quality. It shows each
**input slide** (original deck) next to its **output slide** and lets you (or a teammate)
grade + note each import failure mode from the *Import Evals Taxonomy (PSSL)* — a built-in set of
**24** that you can edit, extend, disable, or delete in-app.

Each deck has **three output variants**, surfaced as pages via the header switcher:

- **Deck Doctor** — `input` vs `ideal_output.pdf` (the hand-crafted ideal Gamma)
- **Current Import** — `input` vs `current_output.pdf` (the live import flow)
- **Programmatic Import** — `input` vs `programmatic_output.pdf` (the programmatic import flow)

Grades are **independent per variant** (including a per-deck `#18`), so you can compare
the ideal target against what the current and programmatic importers actually produce.

- **23 modes graded per slide pair**, **#18 (brand color) graded once per deck**
- Grades: **Pass / Borderline / Fail** (+ free-text note), defaulting to *ungraded*
- Synchronized side-by-side **zoom/pan** viewer
- **Autosave**, auto-resume, and per-variant progress tracking
- **Failure-mode filter** — focus the grading rail on a chosen subset of modes (quick toggles by severity/element). It's view-only and resets on reload, so it never affects grades, progress, or exports.
- **Editable failure-mode directory** — add, edit, enable/disable, or delete modes (including the built-in 24), write per-mode descriptions, and generate a VLM grader for a mode that doesn't have one yet. The taxonomy is stored in `modes.json` in the shared folder, so edits sync to the team (disabling keeps past grades; deleting is only allowed when a mode has no stored data).
- Exports a **consolidated JSON** + a **tidy/long CSV** (with a `variant` column)

## Team Setup (for teammates)

Everyone runs the app **locally**; decks and grades are shared through one **Google Drive**
folder. You only need to do this once.

**First, get access to:**

- The GitHub repo: `gamma-app/import-grader-annotator`
- The shared Google **Shared drive** folder (e.g. `import-slide-grader-data`)
- **Google Drive for Desktop** installed, with that Shared drive synced to your Mac/PC

**Then:**

```bash
# 1. Get the code
git clone https://github.com/gamma-app/import-grader-annotator.git
cd import-grader-annotator

# 2. Install (Python venv + deps, frontend deps, and builds the UI)
./setup.sh

# 3. Point the app at the shared Drive folder
cp .env.example .env
#    Edit .env and set SLIDE_GRADER_DATA to YOUR local path to the synced folder, e.g.
#    SLIDE_GRADER_DATA="$HOME/Library/CloudStorage/GoogleDrive-<you>@gamma.app/Shared drives/<Name>/import-slide-grader-data"

# 4. Run it (serves the app at http://127.0.0.1:8000 and opens your browser)
./run.sh
```

> **Finding your Drive path:** in Finder, right-click the folder → hold **⌥ Option** →
> **“Copy … as Pathname”**, or drag the folder into a Terminal window. The path contains
> spaces, so keep it wrapped in quotes in `.env`.

**The one rule:** split the decks between you — don't grade the *same* deck at the same time
(grades are one file per deck and Drive is last-write-wins). Everything autosaves to the
shared folder and syncs to the team within seconds.

New to the tool? See **Adding decks**, **Export**, and **Keyboard** below. Setting it up for
the team for the first time? See **Sharing with a teammate (Google Drive)**.

## Stack

- **Backend:** FastAPI (Python) — scans decks, renders PDFs→PNGs (PyMuPDF), stores annotations as JSON, builds exports.
- **Frontend:** React + Vite + Tailwind.

## Prerequisites

- Python 3.10+ and Node 18+

## Setup

```bash
./setup.sh             # backend venv + deps, frontend deps, and builds the UI
cp .env.example .env   # then set SLIDE_GRADER_DATA (see Sharing)
```

Or manually:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm install && npm run build
```

## Run

```bash
./run.sh          # one local service at http://127.0.0.1:8000
```

`run.sh` serves the API, the built UI, and rendered images on a single port and opens
your browser. It reads `.env` for the shared data location (see **Sharing**).

> Dev mode (hot reload, two ports) is still available: run the backend with
> `backend/.venv/bin/python -m uvicorn app.main:app --port 8000` and, separately,
> `cd frontend && npm run dev` (Vite on :5173).

## Adding decks (data convention)

Stage one folder per deck under `data/decks/`:

```
data/decks/<slug>/
    input.pdf                # original deck (export the Google Drive link to PDF)
    ideal_output.pdf         # Deck Doctor Gamma — the "ideal" target
    current_output.pdf       # current-import Gamma — the live import flow
    programmatic_output.pdf  # programmatic-import Gamma — the programmatic flow
```

- `<slug>` is the folder name (e.g. `deck-01-sales-pitch`).
- Export **one slide per page**; don't reorder/cull pages.
- The app renders each PDF to PNGs in a **local cache** (`.cache/renders/<slug>/…`,
  one `NNN.png` per page) on first open (or via **Rescan**), pairs `input` against the
  chosen output **1:1 by page order**, and flags a deck **misaligned** (per variant) if
  the page counts differ. The cache is per-machine and never synced.
- A variant is gradable when `input.pdf` plus that variant's output PDF are present.
  A deck missing one output still works on the other page; the missing one shows under
  **Awaiting output**.

### Aligning misaligned decks

If a variant's output PDF has **more** pages than the input, the 1:1 pairing is wrong
and the deck is flagged **misaligned** and **locked from grading**. To fix it, open the
deck (or click **Align** on its card) and use **Align mode**:

1. The input slides show on the left for reference; click the **extra output slides** to
   mark them for dropping (a live preview shows the resulting `input ↔ output` pairing).
2. When the remaining output count matches the input, click **Save alignment**.

This **destructively edits the output PDF** (dropping the marked pages), re-renders, and
unlocks the deck. The original is backed up once to `<variant>_output.original.pdf` beside
it. **Dropped the wrong slide?** Click **Reset** in the aligned deck's header to restore
the original, re-lock the deck, and re-align (you can also restore that backup over the
output PDF by hand). Decks where the output has *fewer* pages than the input can't be
fixed this way.

### Adding a deck to the shared Drive

Day-to-day the data dir *is* your Google Drive folder, so adding a deck is just:

1. Drop a new `decks/<slug>/` folder (with the PDFs above) into the shared Drive folder.
2. Let Google Drive finish syncing — it's on your own disk immediately; teammates get it
   once their Drive syncs.
3. In the app, click **Rescan / re-render**. The deck appears and renders on first open —
   no restart and no code change.
4. Teammates pick it up the same way (Rescan after their Drive syncs).

**PDFs only** — never add PNGs; the app renders those locally per machine, and they're
never synced to Drive.

## Importing a deck from PowerPoint (automated)

Instead of running gamma's import by hand and copying the result into Drive, click
**Import PPTX** on the dashboard, upload a `.pptx`, and the app builds a gradable
**`current`** pair for you:

1. **`input.pdf`** — the PowerPoint rendered to PDF with headless **LibreOffice**.
2. **`current_output.pdf`** — gamma's **current import** of that PPTX, driven in a
   headless browser (Playwright) using your saved gamma.app login, then exported to PDF.

For `current_output.pdf` the importer reproduces the manual gamma click-path end-to-end:
**Import → AI import → upload the `.pptx` → Visual import → Continue** (import settings)
**→ Continue** (pick-a-theme) **→ Continue** (slide preview — this one starts generation) →
wait for the generated deck to open at `/docs/<id>` → **Share → Export → Export to PDF**. It
logs each step and waits out gamma's slide-import and generation, which can take a few
minutes for large decks.

Both land in `decks/<slug>/` (slug derived from the filename, or set a title), the pair is
rendered, and it shows up ready to grade. It runs as a background job with live progress
(stages: *converting → importing → finalizing*); the upload is blocked if the slug already exists.

**One-time setup (per machine that will import):**

- `backend/.venv/bin/playwright install chromium` (also run by `setup.sh`).
- Install **LibreOffice** so `soffice` is available for PPTX→PDF.
- Capture a gamma session once: `backend/.venv/bin/python -m app.gamma_login` — log in
  in the window that opens, then press Enter. Re-run if the importer says it expired.

The **Import PPTX** dialog shows exactly what's missing until all three are satisfied.
Only the `current` variant is automated; `ideal`/`programmatic` are still added by hand.

> The gamma.app import/export UI is feature-flagged and evolves, so the click-path may
> need a one-time **calibration** against your account. On any failure the importer saves
> a screenshot + DOM under `.cache/imports/debug/<job>/`, and the button labels, per-step
> text hints, and selectors are all overridable via `GAMMA_*` env vars (see `.env.example`).
> Set `GAMMA_IMPORT_HEADLESS=0` to watch it run.

## Data & storage

Paths below are relative to the **data dir** (`SLIDE_GRADER_DATA`, default `./data`; point
it at your shared Google Drive folder — see **Sharing**). Rendered PNGs are the one
exception: they live in a **local** cache, never in the data dir.

| What | Where |
|---|---|
| Source PDFs (you add) | `<data>/decks/<slug>/input.pdf`, `ideal_output.pdf`, `current_output.pdf`, `programmatic_output.pdf` |
| Annotations (autosaved) | `<data>/annotations/<slug>.json` (per-variant, schema v2) |
| Failure-mode registry + descriptions | `<data>/modes.json`, `<data>/mode_descriptions.json` (shared, last-write-wins) |
| Exports | `<data>/exports/consolidated.json`, `tidy.csv` |
| Rendered PNGs (auto, **local**) | `.cache/renders/<slug>/{input,ideal,current,programmatic}/` (`SLIDE_GRADER_CACHE`) |

## Export

Click **Export** in the header (or `POST /api/export`). Produces:

- `consolidated.json` — every deck's full annotations + the mode registry.
- `tidy.csv` — one row per (variant × slide pair × mode); deck-level #18 appears as
  `level=deck` rows. Columns: `deck_slug, title, variant, variant_label, annotator,
  level, pair_index, input_image, output_image, mode_id, mode_name, element, dimension,
  severity, grade, note, updated_at`.

## Sharing with a teammate (Google Drive)

Everyone runs the app **locally** but points it at **one shared Google Drive folder**, so
decks and grades stay in sync with no server to host. Grades are one JSON file per deck, so
the safe workflow is **divide the decks** — don't have two people grade the *same* deck at once.

**One-time, by whoever owns the data:**

1. Create a Google **Shared drive** folder, e.g. `slide-grader-data/`, and share it with the team.
2. Make sure everyone has **Google Drive for Desktop** installed and that folder synced locally.
3. Seed it with the existing decks (safe to re-run; never overwrites):
   ```bash
   ./scripts/seed_drive.sh "/path/to/Drive/slide-grader-data"
   # add --with-annotations to also copy local grades, --dry-run to preview
   ```

**Each teammate:** follow the [Team Setup](#team-setup-for-teammates) quickstart near the top
(clone → `./setup.sh` → set `SLIDE_GRADER_DATA` in `.env` → `./run.sh`).

**Add a deck later:** drop its three PDFs into `<data>/decks/<slug>/` in the Drive folder (or
re-run `seed_drive.sh`). It shows up for everyone; PNGs render locally on first open.

**Backup / undo:** Google Drive keeps per-file **version history** (right-click a `.json` →
*Version history*). **Export** any time for a consolidated snapshot.

**Caveat:** Drive is last-write-wins. If two people grade the *same* deck at the same moment,
Drive may create a "conflicted copy" of that one `<slug>.json`. Dividing decks avoids this.

## Keyboard

- **← / →** — previous / next slide pair (when not typing in a field)
- **Double-click** an image — reset zoom

## API

`GET /api/modes` · `GET /api/mode-directory` · `GET /api/decks` · `POST /api/rescan` ·
`GET /api/decks/{slug}/{variant}` · `PUT /api/decks/{slug}/{variant}/pairs/{index}` ·
`PUT /api/decks/{slug}/{variant}/deck-level` · `POST /api/decks/{slug}/{variant}/align` ·
`POST /api/decks/{slug}/{variant}/align/reset` ·
`POST /api/modes` · `PATCH /api/modes/{id}` · `DELETE /api/modes/{id}` (edit the registry) ·
`POST /api/export` ·
images served at `/images/<slug>/{input|ideal|current|programmatic}/...` (`{variant}` is `ideal`, `current`, or `programmatic`)

## Design docs

- [`docs/alignment-design.md`](docs/alignment-design.md) — the **deck alignment**
  (misaligned-deck repair) feature described above. Implemented.
- [`docs/recalibration-design.md`](docs/recalibration-design.md) — the per-grader
  **Recalibrate** flow (a prompt-iteration loop that tunes a grader's prompt against human
  labels). Implemented (`backend/app/recalibrate.py`, `frontend/src/components/RecalibratePanel.jsx`).
