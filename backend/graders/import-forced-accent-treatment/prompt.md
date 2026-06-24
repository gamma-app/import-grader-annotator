# Forced into accent treatment

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether content images that had a clear placement role in the source have been forced into a decorative accent treatment in the imported version.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify every image in `input_slide` and classify its placement role: inline with text, full-width, occupying its own section, or prominently positioned. If the source has no images, or its only image is already a small decorative accent, mark **na**.
2. For each identified content image, check in `output_slide` whether it retains roughly the same placement role and relative size.
3. Note any of these failure patterns:
   - The image is cropped into a decorative mask (circle, rounded shape, or other ornamental cutout) that was not present in the source.
   - The image is zoomed in and shrunk into a small accent element placed beside text, reducing it from a prominent to a minor role.
   - The image is moved from a content position (inline, full-width, own section, prominent) to a minor decorative slot at the edge or corner of the layout.

## Verdicts

- **pass** - All content images keep roughly the same placement role and size in the output (inline stays inline, full-width stays full-width, unmasked stays unmasked). Minor positional or size adjustments are acceptable.
- **borderline** - The treatment has shifted for one or more images (a mild mask applied, a modest crop, or the image is somewhat smaller) but the image still occupies a similar visual role and comparable size overall.
- **fail** - One or more content images are clearly forced into accent treatment: cropped into a decorative mask, zoomed and shrunk into a small accent, or moved from a prominent content position to a minor decorative role.
- **na** - The source slide has no images, or its only image is already a small decorative accent in the source (there is no content image to demote).

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
