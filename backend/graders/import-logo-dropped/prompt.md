# Logo Dropped

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether any **logos** present in the source slide are missing, degraded, or mishandled in the output.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify all logos in the source slide (company logos, brand marks, partner logos, product logos). Logos are typically small, recognizable brand images — not decorative photos or icons.
2. For each logo found in the source, check whether it appears in the output slide.
3. Note any of these failure patterns:
   - Logo is completely missing
   - Logo is replaced by text, a pill/badge, or a placeholder
   - Logo is rendered at a dramatically wrong scale (e.g., tiny logo blown up to fill half the slide, or large logo shrunk to unrecognizable size)

## Verdicts

- **pass** — All logos from the source slide are present in the output at roughly appropriate scale and recognizable form. Minor differences in exact positioning or slight size variations are acceptable.
- **borderline** — Logos are present but with noticeable issues: one logo is at a significantly wrong scale, or a secondary/minor logo is missing while primary logos are intact.
- **fail** — One or more logos are completely dropped, replaced by text/pills/placeholders, or rendered at a scale that makes them unrecognizable. Also fail if the source has no logos (nothing to evaluate — grade as pass in that case).

If the source slide contains no logos, verdict is **pass** (no failure mode to detect).

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
