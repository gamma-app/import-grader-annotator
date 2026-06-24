# Heading alignment

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether the vertical and horizontal alignment of headings and body text is preserved after import.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify all text elements in `input_slide` — note the main heading, any subheadings, and body text blocks. For each, observe its **horizontal alignment** (left / center / right) and **vertical alignment** (top / middle / bottom within its container).
2. Compare each text element in `output_slide` against its counterpart in `input_slide`, checking whether horizontal and vertical alignment has changed.
3. Note any of these failure patterns:
   - Main heading shifts from top-aligned to vertically centered (or vice versa)
   - Main heading shifts from left-aligned to centered (or vice versa), or any other horizontal alignment swap
   - Body text that was left-aligned becomes centered, or right-aligned text becomes left-aligned
   - Any secondary/supporting text block whose alignment changed while the main heading is correct
   - A very slight vertical nudge in any text block that does not dramatically alter the overall appearance

## Verdicts

- **pass** - Both horizontal and vertical alignment match the source for all headings and body text blocks — no alignment differences detected.
- **borderline** - Minor alignment differences that do not dramatically alter the slide's appearance: a very slight vertical shift in any text block, or a secondary/supporting text block's alignment changed while the main heading's alignment is correct.
- **fail** - Clear alignment changes that noticeably alter the slide's visual structure: the main heading's vertical alignment swapped (e.g., top→center), the main heading's horizontal alignment swapped (e.g., left→center), or body text alignment changed in a way that visibly restructures the layout.
- **na** - The source slide contains no text elements to evaluate.

When multiple text elements are affected, grade by the most disruptive change: a main heading alignment swap → **fail**; only a secondary block shifted or a slight vertical nudge → **borderline**.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
