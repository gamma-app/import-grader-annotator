# Table styling / size

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether tables retain their styling, proportions, and structure after import.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify every table in `input_slide`: note header-row styling (background color, text color, font weight), cell background colors (alternating rows, highlighted/filled cells), border styling (presence, thickness, color), row heights, column proportions, padding, overall table size, and all cell text content.
2. For each table found, locate its counterpart in `output_slide` and compare all of the above attributes as well as data completeness (no missing rows, columns, or changed text).
3. Note any of these failure patterns:
   - Header row background color wrong or missing
   - Alternating row colors absent or incorrect
   - Highlighted or filled cells lost their background color
   - Borders missing where they existed, added where they didn't, or changed in thickness/color
   - Row heights, column widths, or padding noticeably different from source
   - Overall table dramatically larger or smaller than source
   - Merged cells split apart or columns collapsed
   - Rows, columns, or cell text dropped or altered

## Verdicts

- **pass** - Every table preserves its styling and data: header colors match, cell backgrounds are correct, borders are present with similar styling, and proportions are preserved. Minor pixel-level spacing differences or slight color-shade variation are acceptable.
- **borderline** - At least one table has correct data but noticeable styling differences: wrong header background, missing alternating row colors, changed border style, or spacing/size that looks noticeably off. Grade by the most severe table.
- **fail** - At least one table has significant styling or structural loss: completely wrong colors, borders missing where they should exist (or added where they shouldn't), dramatic size change, or broken structure (merged cells unmerged, columns collapsed, rows/columns or text dropped). Grade by the most severe table.
- **na** - The `input_slide` contains no tables.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
