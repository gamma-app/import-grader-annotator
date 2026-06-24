# Bullet size / shape / color

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether bullet styling — including shape, size, and color — is faithfully preserved across all bulleted lists on the slide.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify all bulleted lists in `input_slide` and note: the bullet shape (e.g., square, arrow, dash, checkmark, custom character, number, or round dot), the bullet size relative to the accompanying text, and the bullet color (whether it matches the text color or uses an accent color).
2. Compare each of those bullet attributes in `output_slide` against the source, checking whether shapes, sizes, and colors are preserved — paying special attention to any custom or non-standard bullet types.
3. Note any of these failure patterns:
   - Custom bullet shapes (squares, arrows, dashes, checkmarks, custom characters, numbers) replaced with generic round dots
   - Bullet size dramatically larger or smaller relative to the text than in the source
   - Bullet color completely changed (e.g., accent color replaced with black, or text-matching color replaced with a different hue)
   - Minor shape variant differences (e.g., filled vs. outline circle), small size discrepancies, or slight color variation that still preserves the overall list structure

## Verdicts

- **pass** - Bullet shapes, sizes, and colors all match the source; any custom bullet types are fully preserved.
- **borderline** - Bullets are present and the list structure is clear, but there are noticeable styling differences: a slightly different shape variant, a minor size difference, or a small color variation that does not completely change the intended appearance.
- **fail** - Custom bullet shapes are replaced with generic round dots, bullet sizing is dramatically off relative to the text, or bullet colors are completely wrong. When multiple lists are present, grade by the most severe: if any list has custom bullets flattened to round dots or dramatic mis-sizing, the verdict is fail.
- **na** - The source slide contains no bulleted lists.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
