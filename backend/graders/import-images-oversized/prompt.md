# Icons / emoji / images oversized

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether small inline icons, emoji, or small images that were modestly sized in the source have been blown up to disproportionately large graphics in the imported version.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify all small inline elements in `input_slide`: icons, emoji, small glyphs, or small images that are roughly text-height or modestly sized and appear inline with content. Exclude logos, background images, hero images, and full-width images — those are graded elsewhere.
2. For each such element found, compare its size relative to surrounding content and the overall slide in `output_slide` versus `input_slide`. Check whether the element has grown significantly beyond its original proportional size.
3. Note any of these failure patterns:
   - A text-height icon or small glyph now fills a quarter or more of the slide area
   - A small inline image is rendered at a scale that dominates the slide or breaks the surrounding layout
   - An emoji or small decorative element is enlarged to the point that it disrupts visual balance
   - Multiple small elements each enlarged noticeably beyond their original size

## Verdicts

- **pass** - Small inline elements keep roughly proportional sizing relative to surrounding content and the slide as a whole; minor size differences are acceptable.
- **borderline** - One or more small inline elements are noticeably larger than in the source but do not dominate the slide or break the layout.
- **fail** - One or more small inline elements are blown up to disproportionately large graphics (e.g. a text-height icon now fills a quarter or half the slide), significantly changing the visual balance or breaking the layout. If any element is dramatically oversized, verdict is fail; if enlargement is only mild across multiple elements, verdict is borderline.
- **na** - The source slide contains no small inline icons, emoji, or small images that could be oversized (nothing in this category exists on the slide).

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
