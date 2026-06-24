# Card Frames / Borders

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether **slide borders or frames** from the source are maintained in the output.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Check the source slide for any border or frame treatment:
   - A colored border/frame around the entire slide edge
   - A partial border (top/bottom/sides only)
   - A decorative frame pattern around the slide content
   - A highlighted/tinted border region
2. Compare whether these borders/frames are preserved in the output.
3. Note: this is about the slide's own border/frame styling, not about borders on individual elements like tables or images.

## Verdicts

- **pass** — All slide borders/frames from the source are present in the output with matching color and style.
- **borderline** — Borders are partially present but with differences — e.g., the border is there but a different color, or present on some sides but missing on others.
- **fail** — Slide borders/frames from the source are completely dropped in the output, or added where none existed.

If the source slide has no border or frame treatment, verdict is **pass**.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
