# Background / hero images dropped

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether full-bleed, title-slide, or hero/landscape background images are preserved after import.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Examine `input_slide` for background or hero images: full-bleed photos, title-slide photo backgrounds, hero/landscape images spanning most of the slide, or gradient/textured images used as a backdrop. Ignore small inline content images, icons, and logos.
2. For each such backdrop image found, check whether it is present in `output_slide` and still reads as the slide's background.
3. Note any of these failure patterns:
   - The backdrop is completely absent — replaced by a plain solid color where an image should be.
   - The backdrop is replaced by an unrelated image or a generic gradient not present in the source.
   - The backdrop image is so heavily altered (extreme recoloring, near-total obscuring) that the original is no longer recognizable.
   - The backdrop is present but significantly degraded: heavily cropped, shrunk from full-bleed to a small panel, strongly recolored or overlaid, or partially obscured — yet still identifiable.
   - When multiple backdrop images exist: if the main hero image fails, the overall verdict is Fail; if a secondary backdrop is degraded while the main hero is intact, the overall verdict is Borderline.

## Verdicts

- **pass** - Every backdrop image identified in `input_slide` is present in `output_slide` and still reads as the slide's background. Acceptable differences include changes in crop, position, zoom, or color tone, as long as the image is clearly there.
- **borderline** - A backdrop image is present in `output_slide` but significantly degraded so the slide's character changes: heavily cropped, shrunk from full-bleed to a smaller panel, strongly recolored/overlaid, or partially obscured — yet the original image is still identifiable. Also applies when a secondary backdrop is degraded while the main hero image is intact.
- **fail** - A background/hero image is effectively gone: completely dropped (plain color where an image should be), replaced by an unrelated image or generic gradient, or so altered that the original is no longer recognizable. If any hero image meets this bar, the verdict is Fail.
- **na** - The `input_slide` has no background or hero image — its background is a plain solid color or simple flat design with no photo, textured, or gradient backdrop image.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
