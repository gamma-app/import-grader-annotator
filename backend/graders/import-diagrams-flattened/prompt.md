# Diagrams Flattened to Primitives

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether any **structured diagrams** (SmartArt, Venn diagrams, chevrons, timelines, flowcharts, organizational charts, quadrant diagrams, puzzle pieces) are **rebuilt as generic primitives**, losing their characteristic shape and color relationships.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify any structured diagrams in the source slide. These are visually distinct from plain text or simple images — they have connected shapes, arrows, overlapping regions, or structured layouts that convey relationships.
2. In the output, check whether each diagram retains its characteristic structure:
   - Does a Venn diagram still show overlapping circles?
   - Does a timeline still show sequential progression?
   - Does a flowchart still show connected steps with arrows?
   - Does a chevron/process diagram still show directional stages?
   - Does a hierarchy chart still show parent-child relationships?
3. Note if the diagram has been "flattened" — rebuilt as disconnected boxes, bullet lists, plain text, or generic shapes that lose the structural meaning of the original.

## Verdicts

- **pass** — All diagrams in the source are faithfully reproduced in the output with their characteristic structure intact. Minor styling differences (slightly different colors, rounded vs square corners) are acceptable if the structural meaning is preserved.
- **borderline** — Diagrams are partially preserved — the overall shape/structure is recognizable but some elements are lost or simplified (e.g., a 5-step process shows only 4 steps, or arrows/connectors are missing but shapes remain).
- **fail** — One or more diagrams are flattened to generic primitives: rebuilt as plain text lists, disconnected boxes, or generic shapes that lose the structural relationships of the original.

If the source slide contains no structured diagrams, verdict is **pass**.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
