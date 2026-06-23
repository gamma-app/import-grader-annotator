# Grader Recalibration — Design

> **Status:** design only — not yet built. Captures the decisions from the
> 2026-06-22 design discussion so we can pick this up after more labels are added.
> Nothing here is implemented yet.

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
- A **Recalibrate** button where the user picks one grader (failure mode).
- **No "Grader Lab"** — that larger surface (leaderboard, disagreement queue, adjudication)
  is deferred. See [Deferred](#deferred--future).

## The recalibration flow

1. **Gather data for the chosen mode.** Pull *all* existing human annotations
   (`label` + `note`) for that mode, across **all decks and both variants** — the grader
   is variant-agnostic (it just sees an input/output image pair), so `ideal` and `current`
   labels are both valid training data. Join each with the grader's **current output**
   (`verdict` + `reason`) from the AI-grades store (`load_ai_grades`).
2. **Split.** Reserve a **random holdout** slice the optimizer never sees; train on the rest.
   (Assumes enough coverage. Holdout fraction is a build-time default, e.g. ~20%.)
3. **Baseline.** Score the current prompt's agreement on train + holdout. Where the cached
   AI output's `prompt_hash` still matches the live prompt, this is **free** (reuse cache).
4. **Iterate — fixed N rounds, keep best:**
   - The **optimizer (a VLM)** is shown the **disagreements**: each one's human label +
     note, the grader's verdict + reason, and the **input/output slide images** (images on
     disagreements only — it sees the visual cue it's missing without paying to re-view
     passing slides). It proposes a revised prompt.
   - Evaluate the candidate by running it **inline** through the eval-server
     (`_post_run_grader(prompt, model, input, output)` already accepts the full prompt
     text — no file writes needed) over the **train** labels; compute agreement.
   - Repeat for N rounds (N ≈ 3–5, configurable). Keep the candidate with the best
     **holdout** agreement.
5. **Review + approve.** Show the **prompt diff**, before/after agreement (train + holdout),
   and which slides flipped (correct→wrong and wrong→correct). The optimizer also reports
   the **themes it found** ("7 false-fails were minor color shifts → added a tolerance
   clause"). Approve → saved as a new **in-app version** (becomes the active prompt the app
   grades with); reject → discarded.
6. **Adopt to the pipeline (separate, explicit).** A **"Push to `prompt.md`"** action writes
   the chosen version to the canonical grader file in `IMPORT_EVALS_GRADERS_DIR`, from which
   it can be committed/PR'd into the import-evals repo.

## Metric

Symmetric agreement: **Cohen's kappa + raw agreement %**, with the **3×3 confusion matrix**
(pass / borderline / fail) as the diagnostic. Kappa is the headline so a pass-heavy base rate
can't fake a good score. Reported on the **holdout**, before vs. after.

## Key decisions (and why)

| Decision | Choice | Why |
|---|---|---|
| What "better" means | Symmetric agreement (kappa + %) | Treat all mismatches equally; kappa guards against the pass-heavy base rate. |
| Holdout | Auto **random** holdout | Honest generalization signal; simplest given partial coverage. |
| Optimizer inputs | Label + note + grader verdict/reason + **images on disagreements** | Best info-per-dollar; VLM sees the missed visual cue without re-viewing every passing slide. |
| Action space | **Prompt wording/rules + text-distilled few-shot** | Keep rubric meaning + model fixed so gains are attributable and old labels stay valid. Few-shot exemplars are drawn only from **train**. |
| Stopping | **Fixed N rounds, keep best** | Predictable cost/runtime. |
| Where prompts live | **Versioned in-app + push button** | Experiments isolated from the shared repo; canonical `prompt.md` changes only on explicit push; reversible. |
| Human gate | Approve before a version goes active | No silent auto-adopt. |
| Labels | Trusted as-is (no in-loop adjudication) | Simpler v1; adjudication deferred (see below). |

## Data model additions

- **Per-grader version store** (e.g. `<data>/grader-versions/<grader_name>.json`):
  an ordered list of versions, each `{ id, prompt, model, agreement, kappa, parent_id,
  created_at, changelog, source: "recalibration" | "manual", status }`, plus an
  `active_version_id`.
- **Active-version override:** `load_grader()` should prefer the in-app active version's
  prompt over `prompt.md` when one is set (so in-app grading uses the recalibrated prompt
  until it's pushed or rolled back). The canonical file is the fallback / push target.
- **Rollback** = set `active_version_id` to an earlier entry.

## How it hooks into the existing code

- `backend/app/ai_grader.py`
  - `_post_run_grader(prompt, model, input_url, output_url)` — sends the prompt **inline**;
    this is what makes inline candidate evaluation possible (no file writes to test).
  - `load_grader()` / `load_ai_grades()` — current prompt/model and cached grader outputs.
  - The **M2 bulk-job system** (`start_run`, `_run_job`, the in-memory job registry + the
    dashboard progress banner) is the template for running recalibration as a background job.
- `backend/app/modes.py` — `MODE_GRADERS` (mode → grader name); the v1 pair-level set.
- `backend/app/config.py` — `IMPORT_EVALS_GRADERS_DIR`, `EVAL_SERVER_URL`, `AI_GRADER_MODEL`,
  `AI_GRADER_CONCURRENCY`.
- Human labels live in `<data>/annotations/<slug>.json` (per-variant, label + note).

## Cost model

Per round ≈ `(# train labels)` eval-server calls + the optimizer's VLM call(s) on the
disagreement set. Total ≈ `N × train_size` grader calls + `N` optimizer calls, plus a
one-time holdout scoring for kept candidates. Baseline scoring is mostly free (reuses cache).
The cost knob is `N × train_size`, so a Recalibrate run should be a **background job** with a
progress banner and a cost estimate in the confirm dialog.

## Open questions / build-time defaults

- **Optimizer model** — which VLM drives the rewrite (likely the same family as the graders;
  make it configurable, e.g. `RECALIBRATE_MODEL`).
- **Defaults** — N rounds (≈3–5), holdout fraction (≈20%).
- **Minimum coverage** — soft-warn / disable Recalibrate when a mode has too few labels to
  hold out meaningfully.
- **Regression guardrail** — consider feeding the optimizer a sample of currently-*correct*
  cases as "keep these right" anchors so it doesn't fix disagreements by breaking agreements;
  the holdout score is the backstop either way.
- **Exact optimizer payload** — how disagreements + images are formatted into the prompt.

## Deferred / future

Explicitly out of scope for v1, but the design above shouldn't preclude them:

- The full **Grader Lab** — mode leaderboard (worst-kappa first), per-grader workspace,
  clickable confusion matrix, disagreement queue.
- **Adjudication** — confirm / flip / mark-rubric-ambiguous on disagreements (fixing the
  ground truth itself). v1 trusts existing labels.
- **Deck-level graders** (#18, #21) — whole-deck inputs, per-deck labels; different
  disagreement/image handling.
- **Stronger guards** — deck-split holdout (leakage-proof), McNemar significance gate,
  "do no harm" flip budget as a hard gate, k-fold.
- **Trust scores** surfaced on the dashboard; structured failure-tag taxonomy.
