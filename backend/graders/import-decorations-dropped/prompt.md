# Decorations Dropped

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether **decorative shapes and visual embellishments** from the source are dropped in the output.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify decorative elements in the source slide. These are non-content visual elements that contribute to the brand/design feel:
   - Decorative shapes: clouds, blobs, abstract curves, swooshes
   - Geometric accents: quarter-circles, triangles, angular shapes in corners or edges
   - Gradient bars or colored bands
   - Background grids or dot patterns
   - Decorative lines or borders that aren't functional dividers
2. Check whether these decorative elements are preserved in the output.
3. Decorations are distinct from functional content (text, images, charts) and from backgrounds. They are the "brand flavor" shapes that make a slide look polished and on-brand.

## Verdicts

- **pass** — All decorative elements from the source are present in the output. Minor differences in exact shape rendering or position are acceptable.
- **borderline** — Some decorations are preserved while others are missing, or decorations are present but noticeably altered (different shape, color, or size). The overall brand feel is partially maintained.
- **fail** — Decorative shapes are dropped entirely, leaving the slide looking generic or "off-brand" compared to the source. Multiple decorative elements are missing.

If the source slide contains no decorative elements (plain/minimal design), verdict is **pass**.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
