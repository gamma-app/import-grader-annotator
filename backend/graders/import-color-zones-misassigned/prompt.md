# Color zones / fills misassigned

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether color zones, container fills, and background regions are correctly reproduced — including filled panels, split backgrounds, section fills, and outline-vs-fill distinctions.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify all distinct color zones and fills in `input_slide`: colored panels or containers (boxes with background fills), split backgrounds (e.g., left half dark / right half light), section fills (content areas with distinct background colors), and any shapes that are outline-only vs. filled.
2. Check each identified zone/fill in `output_slide` to confirm it is present, correctly colored, and correctly rendered as filled or outline-only.
3. Note any of these failure patterns:
   - A fill is dropped from a container or panel that had one in the source
   - A fill is added to a container or region that was plain/transparent in the source
   - An outline-only shape is rendered as filled, or a filled shape is rendered as outline-only (outline↔fill swap)
   - A split background (two or more distinct color regions) is collapsed into a single color
   - A color zone is present but uses the wrong color (not just a minor shade difference)

## Verdicts

- **pass** - All color zones and fills match the source: containers, panels, split backgrounds, and outline/fill distinctions are all preserved. Minor shade differences are acceptable.
- **borderline** - Color zones are mostly preserved but with a noticeable issue: one container has a wrong fill color, or a minor fill is dropped or added without significantly changing the slide's overall visual structure.
- **fail** - Significant problems are present: fills dropped from key containers, fills added where none should be, an outline↔fill swap, or a split background collapsed into a single color. When multiple zones are affected, grade by the most severe: any key fill dropped/added, an outline↔fill swap, or a split background collapsed counts as Fail.
- **na** - The source slide has no distinct color zones or container fills (plain/uniform background) and the output adds none. If the output adds a fill where the source was plain/transparent, do not use N/A — grade Borderline or Fail as appropriate.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
