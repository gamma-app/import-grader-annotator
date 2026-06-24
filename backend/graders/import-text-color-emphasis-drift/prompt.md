# Text color / emphasis drift

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether text colors and emphasis formatting (bold, italic, underline) in the imported slide match those in the source slide.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. In `input_slide`, identify all text elements and note: (a) text colors (headings, body text, colored accents or highlighted keywords), and (b) emphasis formatting (which words or phrases are bold, italic, or underlined).
2. In `output_slide`, compare each text element against the source for: (a) color fidelity — do heading, body, and accent colors match? and (b) emphasis fidelity — is bold preserved, italic unchanged, underline retained?
3. Note any of these failure patterns:
   - Arbitrary color swaps (e.g., white text → navy, orange accent → black)
   - Bold text losing its bold weight
   - Italic added to text that was not italic in the source
   - Underline dropped from text that was underlined in the source
   - Any combination of the above affecting multiple elements

## Verdicts

- **pass** - All text colors (headings, body, accents) and all emphasis formatting (bold, italic, underline) in the output match the source with no meaningful differences.
- **borderline** - Minor drift only: one or two text-color changes that do not dramatically alter readability, or a single minor emphasis change (e.g., one word loses its bold) — but no arbitrary color swaps and no structural change to the overall emphasis pattern.
- **fail** - Significant drift: arbitrary color swaps (e.g., white→navy, orange→black), bold text losing its bold across one or more elements, italic added where it did not exist in the source, or underline dropped — any change that alters the emphasis structure of the slide. When multiple elements have mixed severity, grade by the most severe: any arbitrary color swap or structural emphasis change → Fail.
- **na** - The source slide contains no text at all.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
