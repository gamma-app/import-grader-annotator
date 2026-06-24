# Forced Into Accent Treatment

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether any images that were **inline or full-width** in the source are **forced into an accent mask** (cropped into a small decorative shape, zoomed, or placed into an accent container) in the output.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify images in the source slide and note their placement: inline with text, full-width, in their own section, or positioned freely on the slide.
2. In the output slide, check whether the same images have been forced into an accent treatment — this means the image has been:
   - Cropped into a circular, rounded-rectangle, or other decorative mask shape when the source had it rectangular/unmasked
   - Zoomed in significantly and placed as a small accent beside text, when the source had it larger
   - Moved from an inline/content position to a small decorative accent position
3. The key question is: did an image that was prominently placed in the source get demoted to a small accent decoration in the output?

## Verdicts

- **pass** — All images maintain roughly the same placement style as in the source. Images that were inline stay inline, full-width stay full-width. Minor position adjustments are fine.
- **borderline** — An image's treatment changed somewhat (e.g., slightly different cropping or a minor mask applied) but it still occupies a similar visual role and size on the slide.
- **fail** — One or more images are clearly forced into an accent treatment: cropped into a decorative mask, zoomed and shrunk into a small accent area, or moved from a prominent position to a small decorative role.

If the source slide contains no images, verdict is **pass**.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
