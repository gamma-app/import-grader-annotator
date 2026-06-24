# Divider mishandling

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether dividers and rules (horizontal lines, vertical separators, decorative rules, thin bars) are faithfully preserved in the imported output.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify all dividers/rules in `input_slide`: horizontal lines, vertical separators, decorative rules between sections, and thin bars separating content areas. Note each one's color, thickness, position, and line style (solid/dashed/dotted). If none exist, note that.
2. Check `output_slide` for: (a) whether each source divider is present, (b) whether its color, thickness, position, and line style match the source, and (c) whether any dividers appear that were not in the source (phantom dividers).
3. Note any of these failure patterns:
   - A source divider is completely absent (dropped)
   - A divider's color has changed noticeably, altering its visual meaning
   - A divider's thickness has changed noticeably
   - A divider has been significantly repositioned so that content separation is disrupted
   - A divider's line style has changed (e.g., solid → dashed)
   - A phantom divider appears in the output where none existed in the source
   - When multiple dividers are present, apply the most severe individual verdict across all of them

## Verdicts

- **pass** - All source dividers are present with matching color, thickness, position, and line style; no phantom dividers added. Minor positional shifts that do not affect visual separation are acceptable.
- **borderline** - Dividers are mostly preserved but with noticeable differences: a color change, thickness change, or slight repositioning that alters visual separation; or a minor phantom divider added.
- **fail** - One or more dividers are dropped entirely, dramatically recolored (changing visual meaning), significantly resized or moved so content separation breaks, or clear phantom dividers are added where none existed. When multiple dividers are present, any dropped divider or prominent phantom divider results in Fail.
- **na** - The source slide contains no dividers/rules of any kind, and the output also adds none.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
