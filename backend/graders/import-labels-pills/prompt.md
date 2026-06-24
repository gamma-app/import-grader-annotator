# Labels / Pills

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether **labels and pills** (badge-like elements with text inside a colored background shape) have maintained their styling.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify all label/pill elements in the source slide. These are typically small, colored, rounded-rectangle or badge-shaped elements containing short text — used for tags, categories, status indicators, or feature labels.
2. For each pill/label, compare source vs output:
   - **Presence**: Is the pill still rendered as a pill, or flattened to plain text?
   - **Styling**: Background color, text color, border radius, border/outline
   - **Casing**: Text casing preserved (uppercase, lowercase, title case)
   - **Nesting**: Pills within pills or complex pill layouts maintained
3. The most common failure is pills being flattened to plain text, losing the visual container entirely.

## Verdicts

- **pass** — All pills/labels maintain their pill appearance with correct styling. Minor color shade differences or slight size variations are acceptable.
- **borderline** — Pills are present as pills but with noticeable styling issues: wrong background color, wrong text casing, or slightly different shape. The pill form factor is preserved.
- **fail** — One or more pills are flattened to plain text (losing their container), have completely wrong styling, or are missing entirely.

If the source slide contains no labels or pills, verdict is **pass**.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
