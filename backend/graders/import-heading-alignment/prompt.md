# Heading Alignment

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether **heading and body text alignment** is preserved — checking for top↔center swaps, left↔center changes, or other alignment shifts.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. In the source slide, note the vertical and horizontal alignment of headings and body text:
   - **Vertical**: Is the heading at the top of the slide/section, or vertically centered?
   - **Horizontal**: Is text left-aligned, center-aligned, or right-aligned?
2. In the output slide, check if these alignments are preserved:
   - Top-aligned headings should stay at the top (not be pushed to center)
   - Center-aligned content should stay centered
   - Left-aligned body text should not become centered
   - Right-aligned text should not shift to left or center
3. Also note if the alignment change affects readability or the overall visual balance of the slide.

## Verdicts

- **pass** — Text alignment matches the source for both headings and body text, both vertically and horizontally.
- **borderline** — Minor alignment differences that don't dramatically alter the slide's appearance — e.g., very slight vertical shift, or a secondary text block's alignment changed while the main heading is correct.
- **fail** — Clear alignment changes: top→center swap for headings, left-aligned body text centered, or other alignment shifts that noticeably change the slide's visual structure.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
