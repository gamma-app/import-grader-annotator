# Icons Dropped or Swapped

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether any **icons** present in the source slide are dropped, swapped for wrong glyphs, or replaced with placeholders in the output.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify all icons in the source slide. Icons are small symbolic graphics — checkmarks, arrows, social media icons, industry icons, emoji, custom glyphs, etc. Distinguish icons from logos (brand marks) and decorative photos.
2. For each icon in the source, check whether it appears correctly in the output.
3. Note any of these failure patterns:
   - Icon is completely missing
   - Icon is replaced with a different/wrong glyph (e.g., a phone icon replaced with a generic circle)
   - Icon is shown as a gray placeholder or broken image indicator
   - Icon is replaced with plain text

## Verdicts

- **pass** — All icons from the source are present in the output and are the correct glyphs. Minor color or size differences are acceptable.
- **borderline** — Most icons are present and correct, but one or two have minor issues (slightly different glyph variant, minor color difference) that don't significantly impact comprehension.
- **fail** — One or more icons are completely dropped, replaced with wrong glyphs, shown as placeholders, or converted to plain text.

If the source slide contains no icons, verdict is **pass**.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
