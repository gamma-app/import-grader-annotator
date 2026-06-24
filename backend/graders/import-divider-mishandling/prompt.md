# Divider Mishandling

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether **dividers and horizontal/vertical rules** are mishandled — dropped, recolored, added where none existed, or resized/moved.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify all dividers/rules in the source slide: horizontal lines, vertical separators, decorative rules between sections, thin bars used to separate content areas.
2. Compare source vs output for each divider:
   - **Presence**: Is the divider still there? Or is it dropped?
   - **Color**: Does it match the source color, or has it been recolored?
   - **Size/thickness**: Is the line thickness roughly similar?
   - **Position**: Is it in roughly the same place on the slide?
   - **Style**: Solid, dashed, dotted — does the line style match?
3. Also check for **phantom dividers**: dividers added in the output that don't exist in the source.

## Verdicts

- **pass** — All dividers from the source are present in the output with matching color, thickness, and position. No phantom dividers added. Minor positional shifts acceptable.
- **borderline** — Dividers are mostly preserved but with noticeable differences: a color change, thickness change, or slight repositioning that alters the visual separation of content. Or a minor phantom divider added.
- **fail** — Dividers are dropped entirely, dramatically recolored (changing visual meaning), added where none existed (phantom dividers), or significantly resized/moved in a way that breaks the content separation.

If the source slide contains no dividers or rules, verdict is **pass** (unless phantom dividers were added in the output — that would be a fail).

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
