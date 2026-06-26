# Deck Alignment (misaligned-deck repair) — Design

**Status:** Implemented — align + one-click Reset (restores the kept backup).
**Author:** pairing session, 2026-06-23 (updated 2026-06-25)

## Summary

Some decks are *misaligned*: a variant's output deck has a different number of
slides than the input deck, so the positional input↔output pairing is wrong and
the per-slide grade comparison is meaningless. This feature lets an annotator
**drop extra output slides** from a misaligned variant until it lines up 1:1 with
the input, **destructively editing the output PDF** (with a one-time backup so the
edit can be **Reset**). Misaligned variants are **locked from grading** until aligned.

## Decisions (locked with the user)

1. **Destructive** — physically remove the dropped pages from the output PDF, not a
   non-destructive overlay.
2. **Output-only** — the annotator can only drop slides from the *output* deck. The
   input PDF is never modified.
3. **Automatic re-pairing** — after the drop, remaining output slides re-pair with
   inputs strictly by order (the existing positional zip).
4. **Grading is locked** for a misaligned variant until it is aligned, so we never
   have to remap existing grades across shifting indices.
5. **Reversible via Reset** — a one-time `*.original.pdf` backup is written on the
   first align; an in-app **Reset** restores it (re-locking the deck) so a wrong
   drop is easy to undo. Alignment is **shared** (not per-annotator).
6. **Align mode is only offered for misaligned variants.**
7. Assume **`output_count >= input_count`** in practice. `output_count < input_count`
   cannot be fixed by output-removal and stays locked (guarded edge case).

## How decks work today (grounding)

- A deck is a folder `data/decks/<slug>/` containing **PDFs only**:
  `input.pdf`, `ideal_output.pdf`, `current_output.pdf` (`config.INPUT_PDF`,
  `config.VARIANTS`). These PDFs are the **shared source of truth**, synced to the
  team Drive folder by `scripts/seed_drive.sh`.
- PNGs are a **local, regenerable cache** under `.cache/renders/<slug>/{input,ideal,current}/NNN.png`
  (`config.RENDER_CACHE_DIR`). `storage.ensure_rendered()` re-renders a PDF→PNGs
  whenever the PDF is newer than the newest PNG or PNGs are missing
  (`storage._needs_render`). Rendering is `pdf_split.render_pdf_to_pngs()` (PyMuPDF
  `fitz`), which **clears stale PNGs and re-renders the whole PDF**.
- Pairing is a **positional zip** of the sorted input vs. output PNGs
  (`storage._pairs_from_images`): pair `i` = (`inputs[i]`, `outputs[i]`); leftover
  slides go to `unpaired.{input,output}`.
- The computed per-variant `alignment` block is
  `{input_count, output_count, pair_count, misaligned}` where
  `misaligned = available and input_count != output_count` (`storage._sync_variant`).
- Human grades live per **pair index** (`storage.update_pair`); AI grades are also
  keyed by index (`ai_grader`, `ai_grades/<slug>__<variant>.json`).
- `storage._sync_variant` rebuilds pairs from images on every load, carrying prior
  annotations forward by index.

**Consequence:** because PNGs regenerate from the PDF, the *only* durable way to drop
an output slide is to **delete that page from the output PDF** and re-render. And
because pairing is recomputed from the rendered PDF, once counts match the existing
machinery produces the correct 1:1 pairing with **no pairing-code changes**.

## Core idea

Align mode = a guided "delete the extra output pages" workspace.

1. The variant is misaligned (`output_count > input_count`). Target = drop
   `K = output_count - input_count` output slides.
2. The annotator selects which output slides to drop (typically inserted/duplicated
   slides), with a **live preview** of the resulting `input[i] ↔ remaining output[i]`
   pairing so they can confirm content lines up.
3. **Save** (enabled only when `remaining output == input_count`): back up the
   original output PDF once, delete the selected pages from the output PDF, re-render
   PNGs, recompute pairing. `misaligned` becomes `false` → grading unlocks.

**Reset** undoes an align: it restores the one-time `*.original.pdf` backup over
`*_output.pdf`, re-renders, clears the variant's grades, and re-locks the deck as
misaligned so the annotator can re-align. (The backup can also be restored by hand.)

Alignment is **per-variant**: editing `ideal_output.pdf` aligns `ideal`;
`current_output.pdf` aligns `current`. The shared `input.pdf` is never touched.

## Filesystem & data-model changes

### Output PDF backup (reset + recovery)

On the first align edit of a variant, copy the canonical output PDF to a sibling
backup, then edit the canonical file in place:

```
data/decks/<slug>/ideal_output.pdf            # working (edited) — synced, drives pairing
data/decks/<slug>/ideal_output.original.pdf   # pristine backup — synced, used by Reset
```

- Editing the canonical `*_output.pdf` means every teammate pointing at the shared
  Drive folder sees the aligned deck automatically (shared alignment ✓), and each
  machine's render cache self-heals (the PDF mtime changes → `_needs_render` true).
- The backup lives in the shared data folder, so **Reset** works for any teammate
  (and it's there for manual recovery too). `scripts/seed_drive.sh` carries it
  (`--include='*_output.original.pdf'`) so a fresh seed keeps originals around.

### Persisted alignment record (provenance)

Add a per-variant `alignment_edit` block to the annotation JSON (distinct from the
computed `alignment` block, which stays as-is):

```json
"alignment_edit": {
  "dropped_output_pages": [3, 7],        // original 1-based page numbers removed
  "original_output_count": 12,
  "edited_at": "2026-06-23T22:10:00Z",
  "edited_by": "eric"
}
```

This is **provenance only** — pairing is still derived from the edited PDF. Its
presence drives the "aligned · dropped N · Reset" control in the UI. `storage._migrate`
is unaffected (new key); Reset clears it.

## Backend

### `pdf_split.py`

Add a page-removal helper (PyMuPDF supports this directly):

```python
def write_pdf_without_pages(src: Path, dst: Path, drop_pages_1based: list[int]) -> int:
    """Write `src` to `dst` keeping every page except those in drop_pages (1-based).
    Returns the new page count."""
```

### `storage.py`

- `_variant_pdf_backup(slug, vkey) -> Path` → `…/<pdf-stem>.original.pdf`.
- `align_variant(slug, vkey, drop_pages, annotator)`:
  1. Lock the deck (`_deck_lock`). Load detail; require `alignment.misaligned` and
     `output_count > input_count`.
  2. Validate `drop_pages` ⊆ `[1..output_count]`, unique, and
     `output_count - len(drop_pages) == input_count`.
  3. If no backup exists, copy the current output PDF → `*.original.pdf`.
  4. `write_pdf_without_pages(output_pdf, tmp, drop_pages)` then atomically replace
     the canonical output PDF.
  5. `ensure_rendered(slug, force=True)` (re-render that variant's PNGs).
  6. **Clear that variant's grades** defensively: reset pair + deck-level cells to
     `ungraded` and delete `ai_grades/<slug>__<variant>.json` (a truly-misaligned
     deck shouldn't have grades, but we clear to avoid any stale index attribution).
  7. Write `alignment_edit`, save annotation, return refreshed deck detail.
- `is_variant_gradeable(slug, vkey) -> bool` → `not alignment.misaligned`.
- `reset_alignment(slug, vkey, annotator)`: require a `*.original.pdf` backup (else
  409); atomically restore it over the output PDF, delete the backup, re-render,
  delete `ai_grades/<slug>__<variant>.json`, reset the variant to a clean slate
  (drops grades + `alignment_edit`), save, return refreshed detail. The restored
  original is (re)misaligned, so the deck re-locks.

### Grading lock enforcement

- `update_pair` / `update_deck_level`: raise if the variant is misaligned.
- `ai_grader.grade_pair` and the bulk job builder: skip/refuse misaligned variants
  (bulk runs already iterate decks — filter them out so "Run AI · all" never grades a
  misaligned variant).

### `main.py` — new/changed routes

```
POST /api/decks/{slug}/{variant}/align         body: { drop_pages: [int], annotator? }
POST /api/decks/{slug}/{variant}/align/reset   body: { annotator? }
```

- Both validate deck + variant (existing `_require_deck` / `_require_variant`),
  map `ValueError`/`KeyError` → 400/404, `RuntimeError` (locked) → 409.
- Enforce the lock in `put_pair`, `put_deck_level`, and the AI run routes → **409**
  with a clear message when the variant is misaligned.
- Extend the deck list (`storage.deck_summary` → `/api/decks`) to expose per-variant
  `misaligned` (already present) + the `alignment_edit` provenance so the Dashboard
  can badge/route without extra calls.

## Frontend

### `AlignView.jsx` (new) — the align workspace

- Header: deck name, variant chip, "Drop K slides to align" target, live counter
  ("remaining 11 / input 11 ✓"), **Save** (disabled until counts match), Back.
- Two ordered columns built from the existing detail (`pairs[*].input_image +
  unpaired.input` = full input list; `pairs[*].output_image + unpaired.output` = full
  output list):
  - **Left: input slides** (read-only reference, numbered).
  - **Right: output slides** (selectable; clicking toggles a "drop" mark with a clear
    struck-through/dimmed style and a trash badge).
- **Live pairing preview:** as slides are marked for dropping, show the resulting
  `input[i] ↔ remaining output[i]` alignment (e.g., connector lines or a synced
  two-row strip) so the annotator verifies content correspondence, not just counts.
- Save → `api.alignDeck(slug, variant, dropPages)`; on success route into the now-
  unlocked DeckView.

### `DeckView.jsx` — locked state

When the variant is misaligned, replace the grading grid with a lock banner:
"This deck is misaligned (12 output vs 11 input). Align it before grading." + an
**Align deck** button → AlignView. (Reuses existing `alignment` from the detail.)

When the variant **was aligned** (`alignment_edit` present), the normal grading
sub-header shows an "aligned · dropped N" chip with a **Reset** button →
`api.resetAlignment(slug, variant)` (confirm first; it clears grades + re-locks).

### `Dashboard.jsx`

- Per-variant **misaligned badge** + **Align** button on affected deck cards.
- Disable per-deck/all **Run AI** for misaligned variants; the bulk path skips them
  server-side too (belt and suspenders).

### `App.jsx` / `api.js`

- `App.jsx`: add a `view = { name: 'align', slug, variant }` route → `AlignView`.
- `api.js`: `alignDeck(slug, variant, dropPages)`, `resetAlignment(slug, variant)`.

## Sharing / sync

- The edited `*_output.pdf` is already in `seed_drive.sh`'s include list → shared
  automatically. **Add `*_output.original.pdf`** to that include list so the backup
  travels with a fresh seed (manual-recovery safety net).
- Render caches are local and self-heal from the changed PDF mtime — nothing to sync.
- Concurrency across machines on the same deck is governed by the existing
  last-write-wins note in `storage.py`; align edits are rare and deck-scoped.

## Edge cases

- **`output_count < input_count`:** cannot be aligned by output removal → Align
  disabled with a "can't align by dropping output slides" note; the variant stays
  locked. (User expects this not to occur in practice.)
- **Equal counts but content-shifted** (insert + drop nets to same count): not flagged
  as misaligned today and out of scope — documented limitation.
- **Save guard:** server re-validates `remaining == input_count`; never writes a PDF
  that wouldn't align.
- **Recovery:** **Reset** (in the aligned deck's header) restores `*.original.pdf`
  over `*_output.pdf`, re-renders, and re-locks. The backup can also be restored by
  hand. Reset on a deck with no backup → 409.
- **Pre-existing grades** on a deck graded before the lock existed: cleared on
  align (see storage step 6) to avoid stale index attribution.

## Out of scope (for now)

- Manual re-pairing / pinning / inserting blank gaps (we do automatic positional
  re-pairing only).
- Editing the input deck.
- Splitting/merging slides.

## Implementation plan (file-by-file)

- `backend/app/pdf_split.py` — `write_pdf_without_pages()`.
- `backend/app/storage.py` — `_variant_pdf_backup`, `align_variant`,
  `reset_alignment`, `is_variant_gradeable`; clear-grades on align/reset; expose
  per-variant `misaligned` + `alignment_edit` in `deck_summary`.
- `backend/app/ai_grader.py` — refuse/skip misaligned variants (single + bulk).
- `backend/app/main.py` — `/align` + `/align/reset` routes; 409 lock in `put_pair`,
  `put_deck_level`, AI run routes.
- `frontend/src/api.js` — `alignDeck`, `resetAlignment`.
- `frontend/src/components/AlignView.jsx` — new.
- `frontend/src/components/DeckView.jsx` — locked banner + Align CTA; "aligned · Reset" chip.
- `frontend/src/components/Dashboard.jsx` — misaligned badges, Align buttons, disable AI.
- `frontend/src/App.jsx` — `align` view route.
- `scripts/seed_drive.sh` — include `*_output.original.pdf`.
- `README.md` — short "Aligning misaligned decks" note.

## Testing / verification

- **Backend smoke:** synthetic deck with output = input + 1 page.
  - `POST /align {drop_pages:[k]}` → 200, `alignment.misaligned == false`,
    `output_count == input_count`; AI grades file removed; `*.original.pdf` written.
  - Grading a misaligned variant (`PUT pair`, AI run) → **409**.
  - Invalid drop (wrong count / out-of-range page) → 400; `output<input` → 409/400.
  - `POST /align/reset` → 200, original restored (page count back), backup removed,
    `misaligned == true` again, grades cleared; reset with no backup → 409.
- **Frontend (Playwright):** open misaligned deck → locked banner → Align → mark K
  outputs → Save → grid unlocks. Assert no console errors.
