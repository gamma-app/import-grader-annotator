# Bullet Size, Shape, and Color

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether **bullet styling** is preserved — bullet shape, size, and color.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify bulleted lists in the source slide and their bullet styling:
   - **Shape**: Square bullets, arrow bullets, dash bullets, checkmark bullets, custom bullet characters, numbered lists
   - **Size**: Bullet size relative to text
   - **Color**: Bullet color (often matches text color, but sometimes uses an accent color)
2. Compare bullet styling in the output:
   - Are custom bullet shapes preserved, or have they been converted to generic round dots?
   - Is bullet sizing proportional to the source?
   - Are bullet colors maintained?
3. The most common failure pattern is all custom bullets (square, arrow, dash, checkmark) being converted to standard round dots.

## Verdicts

- **pass** — Bullet shapes, sizes, and colors match the source. Custom bullet types are preserved.
- **borderline** — Bullets are present and functional but with noticeable styling differences: slightly different shape variant, minor size difference, or color variation. The list structure is still clear.
- **fail** — Custom bullet shapes are replaced with generic round dots, bullet sizing is dramatically off, or bullet colors are completely wrong.

If the source slide contains no bulleted lists, verdict is **pass**.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
