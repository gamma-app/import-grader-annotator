# Slides Too Tall / 16:9 Broken

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether the **output card's aspect ratio** has deviated from the standard 16:9 ratio, resulting in a card that is taller than expected.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide (typically 16:9)
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Compare the aspect ratios of the source and output:
   - The source PPTX slide is typically 16:9 (widescreen) or 4:3 (standard)
   - The Gamma output card should maintain a similar aspect ratio
2. Check whether the output card has grown taller than the source:
   - Is there significantly more vertical space in the output?
   - Has content been stretched vertically or has extra whitespace been added?
   - Does the output look like a tall scrollable card rather than a fixed-ratio slide?
3. Common causes: oversized fonts forcing content to wrap, diagram expansion, or the Gamma card growing vertically to accommodate content that was tightly fit in the source.

## Verdicts

- **pass** — The output card maintains roughly the same aspect ratio as the source. Content fits within a similar vertical space.
- **borderline** — The output is somewhat taller than the source but not dramatically so — perhaps 10-20% taller, with slightly more whitespace or one section expanded.
- **fail** — The output card is significantly taller than the source: clearly broken 16:9 ratio, large amounts of extra vertical space, or the card looks like a scrollable page rather than a slide.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
