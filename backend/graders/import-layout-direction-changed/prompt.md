# Layout direction changed

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether the arrangement/direction of content groups (rows, columns, grids, asymmetric splits) is preserved after import.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify all distinct content groups in `input_slide` — a content group is a logical block of related text and/or image elements. Determine how these groups are arranged: horizontal row, vertical list/column, grid (e.g., 2×2, 3×2), or asymmetric split (e.g., text left + image right, 2/3 + 1/3). If there is only one content group, note this and apply the **na** verdict.
2. In `output_slide`, identify the same content groups and check whether their arrangement direction and structure match the source — rows should still be rows, grids should retain their dimensions, and reading order should be preserved.
3. Note any of these failure patterns:
   - A horizontal row of groups becomes a vertical stack
   - A grid (e.g., 2×2 or 3×2) collapses into a single column or linear list
   - A multi-column layout becomes fully stacked/vertical
   - Reading order of groups is broken (e.g., left-to-right becomes top-to-bottom or reordered)
   - An asymmetric split (text left + image right) becomes a stacked arrangement

## Verdicts

- **pass** - Layout direction and arrangement match the source: groups in a row stay in a row, grids retain their dimensions, asymmetric splits are preserved, and reading order is unchanged.
- **borderline** - Overall direction is preserved but with minor arrangement changes — groups are still in a row or grid orientation but spacing is very different, or a 3-column layout becomes 2 columns with one group wrapping to a second row.
- **fail** - Clear direction change: rows become vertical lists, grids collapse to a single column, a multi-column layout becomes fully stacked, or reading order is broken. When multiple content groups are present, grade by the most disruptive change — any row/grid collapsed or reading order broken results in **fail**.
- **na** - The source slide has only a single content group with no multi-group arrangement to evaluate (e.g., one centered block, a single full-bleed image, or a title-only slide).

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
