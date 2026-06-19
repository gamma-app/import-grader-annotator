# Import Slide-Pair Grader

A local tool for manually annotating PPTX→Gamma import quality. It shows each
**input slide** (original deck) next to its **output slide** and lets you (or a teammate)
grade + note each of the 24 import failure modes from the *Import Evals Taxonomy (PSSL)*.

Each deck has **two output variants**, surfaced as two pages via the header switcher:

- **Deck Doctor** — `input` vs `ideal_output.pdf` (the hand-crafted ideal Gamma)
- **Current Import** — `input` vs `current_output.pdf` (the live import flow)

Grades are **independent per variant** (including a per-deck `#18`), so you can compare
the ideal target against what the current importer actually produces.

- **23 modes graded per slide pair**, **#18 (brand color) graded once per deck**
- Grades: **Pass / Borderline / Fail** (+ free-text note), defaulting to *ungraded*
- Synchronized side-by-side **zoom/pan** viewer
- **Autosave**, auto-resume, and per-variant progress tracking
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
    input.pdf            # original deck      (export the Google Drive link to PDF)
    ideal_output.pdf     # Deck Doctor Gamma   (the "ideal" target)
    current_output.pdf   # current-import Gamma (the live import flow)
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

## Data & storage

Paths below are relative to the **data dir** (`SLIDE_GRADER_DATA`, default `./data`; point
it at your shared Google Drive folder — see **Sharing**). Rendered PNGs are the one
exception: they live in a **local** cache, never in the data dir.

| What | Where |
|---|---|
| Source PDFs (you add) | `<data>/decks/<slug>/input.pdf`, `ideal_output.pdf`, `current_output.pdf` |
| Annotations (autosaved) | `<data>/annotations/<slug>.json` (per-variant, schema v2) |
| Exports | `<data>/exports/consolidated.json`, `tidy.csv` |
| Rendered PNGs (auto, **local**) | `.cache/renders/<slug>/{input,ideal,current}/` (`SLIDE_GRADER_CACHE`) |

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

`GET /api/modes` · `GET /api/decks` · `POST /api/rescan` ·
`GET /api/decks/{slug}/{variant}` · `PUT /api/decks/{slug}/{variant}/pairs/{index}` ·
`PUT /api/decks/{slug}/{variant}/deck-level` · `POST /api/export` ·
images served at `/images/<slug>/{input|ideal|current}/...` (`{variant}` is `ideal` or `current`)
