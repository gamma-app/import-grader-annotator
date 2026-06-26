# Grader Recalibration — Design

> **Status:** implemented — see `backend/app/recalibrate.py`,
> `frontend/src/components/RecalibratePanel.jsx`, and the `/api/.../recalibration/...`
> routes in `backend/app/main.py`. This doc records the v1 design that was built (locked
> **2026-06-25** in a follow-up design session); it **supersedes** the original 2026-06-22 sketch
> (which used fixed-N rounds, a single random holdout, and an in-app version override).
> The v1 design below uses a **train / validation / test** split, **best-of-N selection on
> validation**, a **per-candidate VLM diagnosis**, and **adoption straight to `prompt.md`**.
> Intended to be run only on modes with ample labels (≈**200+** pairs that have *both* a
> human grade and an AI verdict).

## Goal

Let a human iteratively **improve a single VLM grader's prompt** so its verdicts agree
better with human annotations. The human supplies ground-truth labels (and notes) by
grading slides as usual; a one-click **Recalibrate** action then runs a prompt-iteration
loop that rewrites that grader's prompt and reports an honest before/after agreement.

## Background: two separate jobs

The existing grading UI conflates two activities. Recalibration only touches the second:

- **Labeling** — *creating* ground truth (grade + note per `(pair, mode)`). Upstream,
  ongoing as new decks arrive. The grading page stays the intake tool for this.
- **Calibration** — *improving graders against* that ground truth. This is recalibration.
  Once labels exist, "where do grader and human disagree?" is a deterministic set
  difference — no grading needed for detection. The only genuinely useful human input to
  the loop is the **label** plus a free-text **why** (the note), which points the
  optimizer at the fix.

## Scope (v1)

- **Pair-level graders only** — the 22 per-slide-pair modes in `MODE_GRADERS`
  (`backend/app/modes.py`). Each label/disagreement maps cleanly to one input/output
  image pair. Deck-level modes (#18 brand color, #21 flaky) are **out of scope** for v1.
- A **one-click Recalibrate** button in the **Failure Mode Directory**
  (`frontend/src/components/ModeDirectory.jsx`), beside the existing *Reinitialize from
  description* and *Commit & push* controls — recalibration is a smarter sibling of reinit.
- **Enough-data assumption:** run only on modes with ample labels (≈200+ pairs with both a
  human grade and an AI verdict). **No minimum-coverage gate** is built for v1; the operator
  picks eligible modes.
- **No "Grader Lab"** — that larger surface (leaderboard, disagreement queue, adjudication)
  is deferred. See [Deferred](#deferred--future).

## The recalibration flow

1. **Gather data for the chosen mode.** Pull *all* existing human annotations
   (`grade` + `note`) for that mode, across **all decks and both variants** — the grader is
   variant-agnostic (it just sees an input/output image pair), so `ideal` and `current`
   labels are both valid data. Join each with the grader's **current output**
   (`verdict` + `reason`) from the AI-grades store, keeping only pairs that have **both** a
   human grade and an AI verdict in {pass, borderline, fail, na}. This is the join + scoring
   already implemented in `reports.py` (`mode_report`), generalized to **pool both variants**
   instead of one.
2. **Split — train / validation / test.** Shuffle the pooled rows with a stored **seed** and
   split **per slide-pair, fully random** (default **60 / 20 / 20**). Persist the split (the
   exact pair ids per bucket) with the run so before/after is reproducible. *Train* feeds the
   optimizer; *validation* selects the winner; *test* is the honest, report-only read.
   - *Known v1 limitation:* a per-pair random split can place near-identical slides from the
     same deck — or the two variants of the same source slide — in different buckets, so the
     **test number may be optimistic**. Deck-grouped splitting is deferred (see below).
3. **Baseline.** Score the current prompt's agreement (κ + %) on train / validation / test
   from the joined verdicts. Where a cached AI verdict's `prompt_hash` still matches the live
   prompt this is **free**; otherwise the current prompt is run to fill gaps (note: the AI
   grade store may be empty on a fresh machine, so this step can require grading the split).
4. **Generate N candidates (independent + diverse).** Each of **N** candidates (default 5) is
   **one VLM call** returning JSON `{ themes, prompt }` — the root-cause analysis first (it
   acts as reasoning), then the revised prompt:
   - **What it sees.** A system prompt fixing the constraints (below); the **current rubric
     verbatim** + the mode description + a **confusion-matrix count summary**; the **full text
     of every train disagreement** (confusion cell + human grade & note + grader verdict &
     reason); and — to bound cost/context — **images for a re-sampled, confusion-cell-balanced
     subset** (K ≈ 10–12) plus **M ≈ 4–6 correct-case "anchors,"** each case laid out as a text
     header immediately followed by its input+output PNGs (images **interleaved** with their
     case, not dumped in one block). Re-sampling per candidate adds input-level diversity on
     top of temperature.
   - **What it may change (wording/rules only).** Sharpen instructions, criteria, and the
     pass/borderline/fail band *wording* — but **keep the model, the verdict set, the band
     *meaning*, and the JSON response format fixed**. A **structural guardrail** rejects (and
     regenerates) any candidate whose prompt drops the required verdict labels or output
     schema, so gains stay attributable and existing labels stay valid.
5. **Select on validation.** Run each candidate **inline** over the **validation** pairs via
   `llm.run_grader(prompt, model, input_path, output_path)` (temperature 0.0), parse verdicts,
   compute κ, and **keep the candidate with the best validation κ** (tie-break: agreement %,
   then fewest regressions vs. baseline). The optimizer never sees validation, so selection
   stays honest. Parallelize across pairs/candidates at `AI_GRADER_CONCURRENCY`.
6. **Test (report-only).** Run the winner over **train + test** for the final before/after
   κ + % + confusion matrices and the **flip lists** (test pairs that went correct→wrong and
   wrong→correct). Test is never used for selection.
7. **Review + approve (human gate).** Show the **prompt diff**, before/after κ + % on all
   three splits, the test confusion matrices, the flip lists (with thumbnails + human notes),
   the winner's **themes**, and an N-candidate **validation leaderboard**. No silent adopt.
8. **Adopt → `prompt.md`.** On approve, write the winning prompt to the canonical grader file
   via `write_grader_prompt()` (the same path *Reinitialize* uses) and mark the grader
   **uncommitted**. Instead of clearing, **persist the winning candidate's already-computed
   verdicts** for every labeled split pair into the AI-grades store under the new `prompt_hash`
   (deterministic at temp 0.0, so identical to a fresh grade) — the agreement report is
   **immediately complete** with no wasted compute. A full bulk re-grade (to also cover
   *unlabeled* pairs, which don't appear in the report) is **optional and operator-triggered**
   via the existing bulk AI job. The operator then uses the existing **Commit & push** control
   (`gitutil`) to land it. `prompt.md` is the **single source of truth** — no in-app version
   override; rollback is a git operation.

## Metric

Symmetric agreement: **Cohen's κ (headline) + raw agreement %**, with the **3×3 confusion
matrix** (pass / borderline / fail; `na` handled as a first-class class as in `reports.py`)
as the diagnostic. κ is the headline so a pass-heavy base rate can't fake a good score.
**Validation** κ selects the winning candidate; **test** κ (vs. baseline) is the honest
before/after reported to the human.

## Key decisions (and why)

| Decision | Choice | Why |
|---|---|---|
| What "better" means | Cohen's κ (headline) + agreement % | Treat all mismatches equally; κ guards against the pass-heavy base rate. |
| Split | **Train / validation / test**, per-pair random, **variants pooled** | Validation gives an honest selection signal; test gives an honest final read; per-pair maximizes scarce data (leakage accepted for v1). |
| Selection / stopping | **Best-of-N on validation** (fixed N) | Predictable cost; an out-of-sample gate the optimizer never sees. |
| Optimizer inputs | Grade + note + verdict/reason (all, as text) + **images on a stratified disagreement subset** + **correct-case anchors** | Full textual picture with bounded image cost; anchors discourage fixing disagreements by breaking agreements. |
| Candidate generation | **N independent, diverse**; each does its own **VLM diagnosis → rewrite** | Explores different root-cause framings, not just wordings; winner's diagnosis becomes the reported themes. |
| Action space | **Wording / rules only** (model + band meaning + JSON fixed) | Gains are attributable and previously-collected labels stay valid. (Few-shot exemplars deferred.) |
| Where prompts live | **`prompt.md` is the single source of truth** | Approve writes it (reuse *Reinitialize* path); history/rollback live in git; no second prompt layer to keep in sync. |
| Human gate | Approve before write | No silent auto-adopt. |
| Labels | Trusted as-is (no in-loop adjudication) | Simpler v1; adjudication deferred (see below). |

## Data model additions

- **Run-record store** (e.g. `<data>/recalibrations/<grader_name>__<timestamp>.json`): one
  record per run for audit + reproducibility — `{ id, mode_id, grader, model, created_at,
  seed, split: {train[], validation[], test[]} (pair ids), baseline: {train, validation,
  test: {kappa, agreement_pct, confusion}}, candidates: [{ id, themes, prompt, sampled_ids,
  validation: {kappa, agreement_pct}, raw_verdicts }], winner_id, winner_test, status:
  "proposed" | "approved" | "rejected" }`.
- **No version override.** Adoption writes `prompt.md` directly (single source of truth);
  there is no `active_version_id` and no `load_grader()` override. **Rollback = git.**
- **Verdicts on adopt.** Writing `prompt.md` busts the in-memory grader cache
  (`write_grader_prompt`) and changes `prompt_hash`. Rather than clearing (as *Reinitialize*
  does), adopt **overwrites the mode's labeled-pair verdicts with the winner's** (carrying the
  new `prompt_hash`, `model`, `graded_at`), so the report stays consistent with the live
  prompt. Unlabeled pairs go stale (flagged by `prompt_hash` mismatch) until an optional bulk
  re-grade.

## How it hooks into the existing code

- `backend/app/reports.py` — `mode_report(mode_id, variant)` already joins human + AI grades
  and emits agreement %, κ, the confusion matrix, and a structured **disagreements** list
  (with image paths, grade+note, verdict+reason). Generalize it to **pool both variants** to
  build the dataset and to score baseline / candidates.
- `backend/app/llm.py`
  - `run_grader(rubric, model, input_path, output_path, temperature=0.0)` — runs a prompt
    **inline** over a pair (reads the PNGs off disk). This is the candidate-evaluation
    primitive (no file writes); pair it with `ai_grader.parse_verdict`.
  - **New `generate_vision_text(prompt, model, images, system=…)`** — the optimizer needs to
    *see* slides; today `generate_text` is text-only.
- `backend/app/ai_grader.py` — `load_grader`, `load_ai_grades` (+ the store writer that
  `grade_pair_mode` uses, to persist the winner's verdicts), `write_grader_prompt`,
  `parse_verdict`; the bulk-job system (`start_run`, `_run_job`, the in-memory `_jobs`
  registry + dashboard progress banner) is the template for running a recalibration as a
  **background job** with progress + cancel.
- `backend/app/modes.py` — `MODE_GRADERS` / `PAIR_MODE_IDS` (the v1 pair-level set).
- `backend/app/storage.py` — `annotation_variant`, `list_slugs`, `prettify`; human labels in
  `<data>/annotations/<slug>.json` (per-variant, grade + note).
- `backend/app/config.py` — `IMPORT_EVALS_GRADERS_DIR`, `AI_GRADER_MODEL`,
  `AI_GRADER_CONCURRENCY`, `AI_GRADES_DIR`, `RENDER_CACHE_DIR`; **add** recalibration knobs
  (below).
- `backend/app/gitutil.py` + existing routes `reinitialize-grader`, `commit-grader`,
  `grader-score-count` — reused for adopt + commit; add a new `recalibrate` module + routes
  and `api.js` methods, surfaced in `ModeDirectory.jsx`.

## Cost model

Per run ≈ baseline scoring (mostly **free** when cached `prompt_hash` matches; otherwise
`≤ split_size` grader calls) + **N** VLM diagnosis calls + **N** rewrite calls +
**N × validation_size** candidate grader calls + **(train_size + test_size)** grader calls to
score the winner. With N = 5 and ~200 labels at 60/20/20 (train ≈ 120, val ≈ 40, test ≈ 40):
≈ 5 × 40 = **200** candidate calls + ~160 winner calls + ~10 optimizer calls + baseline. The
dominant knob is **N × validation_size**, so a Recalibrate run is a **background job** with a
progress banner, cancel, and a **cost/time estimate in the confirm dialog** (mirroring the
*Reinitialize* warning, which also reports how many AI scores will be cleared).

## Build-time defaults

- **Defaults** — `RECALIBRATE_CANDIDATES` N = **5**; split = **60 / 20 / 20**
  (`RECALIBRATE_SPLIT`); candidate-generation temperature ≈ **0.7**
  (`RECALIBRATE_TEMPERATURE`), grading temperature **0.0**; `RECALIBRATE_SEED`; imaged
  disagreements **K ≈ 10–12** and anchors **M ≈ 4–6**, with a per-non-empty-cell floor so
  rare cells (e.g. false-fail) always appear.
- **Optimizer model** — `RECALIBRATE_MODEL`, default = the grader's own model
  (`AI_GRADER_MODEL` / `grader.yml`).
- **Optimizer call** — one VLM call per candidate returning `{ themes, prompt }` (themes
  first, as reasoning); images interleaved per case; a structural guardrail
  rejects/regenerates prompts that drop the verdict set or JSON schema. See flow step 4.
- **Regression guardrail** — anchors + the validation gate are the v1 backstop against fixing
  disagreements by breaking agreements; a hard flip-budget is deferred.
- **Adopt refresh** — the winner's verdicts for labeled pairs are persisted on approve (report
  is instantly current); a full bulk re-grade of unlabeled pairs is optional/operator-triggered.
  See flow step 8.

## Deferred / future

Explicitly out of scope for v1, but the design above shouldn't preclude them:

- The full **Grader Lab** — mode leaderboard (worst-κ first), per-grader workspace,
  clickable confusion matrix, disagreement queue.
- **Few-shot exemplars** in the action space (text-distilled, train-only) — v1 is
  wording/rules only.
- **In-app prompt versioning / rollback / A-B** — v1 keeps `prompt.md` as the single source
  of truth and relies on git for history.
- **Adjudication** — confirm / flip / mark-rubric-ambiguous on disagreements (fixing the
  ground truth itself). v1 trusts existing labels.
- **Deck-level graders** (#18, #21) — whole-deck inputs, per-deck labels; different
  disagreement/image handling.
- **Stronger guards** — **deck-grouped split** (leakage-proof), McNemar significance gate,
  "do no harm" flip budget as a hard gate, k-fold for small modes.
- **Minimum-coverage gate** — auto warn/disable when a mode has too few labels (v1 assumes
  the operator only runs well-covered modes).
- **Trust scores** surfaced on the dashboard; structured failure-tag taxonomy.
