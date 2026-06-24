# Decorations dropped

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether decorative shapes and visual embellishments present in the source slide are preserved in the imported output.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify all decorative elements in `input_slide`: decorative shapes (clouds, blobs, abstract curves, swooshes), geometric accents (quarter-circles, triangles, angular corner/edge shapes), gradient bars or colored bands, background grids or dot patterns, and decorative lines/borders that are not functional dividers. If none exist, return **na**.
2. Check `output_slide` for the presence, appearance, and placement of each identified decorative element — noting whether each is present, missing, or noticeably altered in shape, color, or size.
3. Note any of these failure patterns:
   - A decorative element present in `input_slide` is entirely absent from `output_slide`
   - A decorative element is present but its shape, color, or size is noticeably different (e.g., a quarter-circle replaced by a rectangle, a gradient bar recolored)
   - Multiple decorative elements are missing or altered, leaving the slide looking generic or off-brand compared to the source
   - When multiple decorative elements exist, assess overall brand-feel loss: most/all gone → Fail; a subset altered/missing while the overall look largely survives → Borderline

## Verdicts

- **pass** - All decorative elements from `input_slide` are present in `output_slide`. Minor differences in exact shape rendering or position are acceptable.
- **borderline** - Some decorations are preserved while others are missing, or decorations are present but noticeably altered in shape, color, or size; the overall brand feel is only partially maintained.
- **fail** - Decorative shapes are dropped entirely or multiple decorative elements are missing, leaving the slide looking generic or off-brand compared to the source.
- **na** - The source slide has no decorative elements (plain or minimal design with no shapes, accents, bands, patterns, or ornamental borders).

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
