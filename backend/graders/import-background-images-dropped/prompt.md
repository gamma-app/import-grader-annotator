# Background / Hero Images Dropped

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether any **background or hero images** from the source slide are missing in the output.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify any background images in the source slide: full-bleed photographs, title slide backgrounds, landscape/hero images that span most of the slide, gradient backgrounds with embedded imagery, or any image used as a slide backdrop.
2. Check whether these background/hero images are preserved in the output.
3. Note any of these failure patterns:
   - Background image is completely dropped, leaving a plain/solid background
   - Full-bleed image is missing entirely
   - Title slide photo background is gone
   - Decorative swoosh or gradient image used as background is missing

## Verdicts

- **pass** — All background/hero images from the source are present in the output. Minor differences in exact cropping, positioning, or color tone are acceptable as long as the image is clearly there.
- **borderline** — The background image is partially preserved but significantly degraded — e.g., heavily cropped, very different color treatment, or partially obscured in a way that changes the slide's visual character.
- **fail** — One or more background/hero images are completely dropped, leaving a plain or solid-color background where an image should be.

If the source slide has no background/hero images (just a solid color or plain background), verdict is **pass**.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
