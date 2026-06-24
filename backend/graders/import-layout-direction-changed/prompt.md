# Layout Direction Changed

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether the **layout direction and arrangement** of content groups has changed — rows/columns converted to grids, grids to vertical lists, or reading order broken.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify the layout structure of the source slide:
   - **Horizontal row**: Items arranged left-to-right in a single row
   - **Vertical column/list**: Items stacked top-to-bottom
   - **Grid**: Items in a multi-row, multi-column arrangement (e.g., 2x2, 3x2, 4x3)
   - **Asymmetric layout**: Content split (e.g., text left + image right, or 2/3 + 1/3 split)
2. Compare the layout direction in the output:
   - Have horizontal rows become vertical lists?
   - Have grids been collapsed to a single column?
   - Has a 4-column layout become a 2x2 grid?
   - Has the reading order changed? (e.g., left-to-right items now appear top-to-bottom)
3. Focus on the arrangement of **content groups** (blocks of text+image that form a logical unit), not individual elements.

## Verdicts

- **pass** — The layout direction and arrangement match the source. Items that were in a row are still in a row, grids retain their dimensions, reading order is preserved.
- **borderline** — The overall layout direction is preserved but with minor arrangement changes: e.g., items are still in a row but spacing is very different, or a 3-column layout becomes 2 columns with one wrapping.
- **fail** — Clear layout direction change: rows become vertical lists, grids collapse to a single column, a multi-column layout becomes stacked, or reading order is broken.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
