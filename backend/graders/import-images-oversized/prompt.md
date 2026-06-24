# Icons / emoji / images oversized

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether small inline icons, emoji, or images that were modestly sized in the source have been blown up to disproportionately large graphics in the imported version.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify all small inline elements in `input_slide` — icons, emoji, small glyphs, or small images that are roughly text-height or modestly sized relative to the slide (not large hero images or full-width graphics).
2. For each such element found, compare its size relative to the slide in `output_slide` versus `input_slide` — check whether it has grown significantly larger, now dominates the slide, or breaks the layout.
3. Note any of these failure patterns:
   - A text-height icon or small emoji rendered as a large graphic (e.g., now filling a quarter or half the slide)
   - A small inline image expanded so much it disrupts surrounding text or layout
   - Visual balance of the slide significantly altered because a formerly modest element is now oversized
   - Multiple elements: if any single element is dramatically oversized, that alone constitutes a fail; if enlargement is mild across elements, that is borderline

## Verdicts

- **pass** - All small inline elements in the output retain roughly proportional sizing compared to the source; minor size differences are acceptable
- **borderline** - One or more elements are noticeably larger than in the source but do not dominate the slide or break the overall layout
- **fail** - One or more small elements are blown up to disproportionately large graphics (e.g., a text-height icon now fills a quarter or half the slide), significantly changing the visual balance or breaking the layout
- **na** - The source slide contains no small inline icons, emoji, or small images that could be oversized (nothing in this category exists to evaluate)

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
