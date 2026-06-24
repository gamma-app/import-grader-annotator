# Card frames / borders

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether any slide-level border or frame treatment from the source is faithfully reproduced in the output (or, if none existed, that none was added).

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Examine `input_slide` for any slide-level border or frame treatment: a colored frame around the whole slide edge, a partial border (top/bottom/sides only), a decorative frame pattern around the content area, or a highlighted/tinted border region. Do NOT consider borders on individual elements such as tables or images — only the slide's own border/frame.
2. Check `output_slide` to see whether the same border/frame treatment is present, and whether its color, style, and coverage (which sides) match the source.
3. Note any of these failure patterns:
   - A source border/frame is completely absent in the output (dropped entirely).
   - A border/frame appears in the output that did not exist in the source (added where none existed).
   - A border/frame is present in the output but with a noticeably different color from the source.
   - A border/frame is present on some sides in the output but missing on other sides that had it in the source.

## Verdicts

- **pass** - All border/frame treatments present in the source are also present in the output with matching color and style on all applicable sides.
- **borderline** - A border/frame is partially reproduced — for example, it appears on some sides but not others, or it is present but with a different color or style from the source.
- **fail** - Source border/frame is completely absent in the output, OR a border/frame has been added in the output where the source had none. If the slide has multiple border regions and any one is fully dropped or spuriously added, grade Fail.
- **na** - The source slide has no border or frame treatment of any kind, and the output also adds none.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
