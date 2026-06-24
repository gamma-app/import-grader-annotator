# Text Color and Emphasis Drift

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether **text colors and emphasis formatting** (bold, italic, underline) have drifted from the source on a per-slide basis.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Compare text colors between source and output:
   - Are heading colors the same?
   - Are body text colors preserved?
   - Are any text colors arbitrarily swapped (e.g., white text turned navy, orange text turned black)?
   - Are colored text accents (key words in a different color) preserved?
2. Compare emphasis formatting:
   - **Bold**: Is bold text in the source still bold in the output? Is non-bold text still non-bold?
   - **Italic**: Is italic preserved where it existed? Is italic NOT added where it didn't exist?
   - **Underline**: Is underline preserved?
3. Focus on per-slide drift — individual text color or emphasis changes on this specific slide, not deck-wide theme issues.

## Verdicts

- **pass** — Text colors and emphasis formatting match the source. All bold, italic, and underline formatting is preserved, and text colors are consistent.
- **borderline** — Minor drift: one or two text color changes that don't dramatically alter readability, or a minor emphasis change (e.g., one word lost its bold).
- **fail** — Significant color or emphasis drift: arbitrary text color swaps (white→navy, orange→black), bold text losing its bold, italic added where it didn't exist, or underline formatting dropped.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
