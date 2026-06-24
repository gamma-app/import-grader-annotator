# Color Zones / Fills Misassigned

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether **color zones, container fills, and background regions** are misassigned — fills dropped or added, split-background zones lost, or outline-vs-fill swapped.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify color zones in the source slide:
   - Colored panels or containers (boxes with background fills)
   - Split backgrounds (slide divided into colored regions — e.g., left half dark, right half light)
   - Section fills (content areas with distinct background colors)
   - Outlined-only shapes vs filled shapes
2. Compare source vs output:
   - **Fills dropped**: A colored container in the source has no fill in the output
   - **Fills added**: A transparent/unfilled area in the source gets a fill color in the output
   - **Outline↔fill swap**: A shape that was outlined-only becomes filled, or vice versa
   - **Split zones lost**: A multi-zone background becomes a single solid color
   - **Color mismatch**: The zone exists but with a wrong color

## Verdicts

- **pass** — All color zones and fills match the source. Containers, panels, split backgrounds, and outline/fill distinctions are preserved. Minor shade differences acceptable.
- **borderline** — Color zones are mostly preserved but with noticeable issues: one container has a wrong fill color, or a minor fill is dropped/added without significantly changing the slide's visual structure.
- **fail** — Significant color zone problems: fills dropped from key containers, fills added where none should be, outline↔fill swapped, or split-background zones collapsed into a single color.

If the source slide has no distinct color zones or container fills (plain/uniform background), verdict is **pass**.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
