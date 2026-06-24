# Diagrams flattened to primitives

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether structured diagrams (SmartArt, Venn, chevron/process, timelines, flowcharts, org/hierarchy charts, quadrants, puzzle pieces) retain their characteristic shape and relationships after import.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify every structured diagram in `input_slide`: look for SmartArt, Venn diagrams, chevron/process flows, timelines, flowcharts, org/hierarchy charts, quadrants, or puzzle-piece graphics — any graphic that conveys relationships via connected shapes, arrows, overlaps, or ordered stages. Ignore plain text, simple images, tables, and data charts.
2. For each diagram found, check whether `output_slide` preserves its characteristic structure: overlapping regions (Venn), sequential connected stages (process/timeline), parent–child links (hierarchy/org), connected decision paths (flowchart), etc.
3. Note any of these failure patterns:
   - Diagram replaced by a plain text or bullet list
   - Diagram rebuilt as disconnected, unrelated boxes or generic shapes with no connectors or spatial relationships
   - Arrows, connectors, or overlaps removed so structural meaning is lost
   - Steps, nodes, or stages missing (e.g., 5-step process becomes 4 steps)
   - Hierarchy or parent–child relationships no longer visually represented

## Verdicts

- **pass** - Every diagram in `input_slide` retains its characteristic structure in `output_slide` (Venn still overlaps, timeline still sequential, flowchart still connected, hierarchy still shows parent–child). Minor styling differences (slightly different colors, rounded vs. square corners) are acceptable as long as structural meaning survives.
- **borderline** - The overall shape/structure of a diagram is still recognizable but partially degraded: some elements are lost or simplified (e.g., a 5-step process shows only 4 steps, or arrows/connectors are missing but the shapes/stages themselves remain).
- **fail** - One or more diagrams are flattened to generic primitives: rebuilt as a plain text/bullet list, disconnected boxes, or generic shapes that lose the structural relationships conveyed by the original diagram. When multiple diagrams are present, any single flattened diagram yields a Fail verdict.
- **na** - The source slide contains no structured diagram (no SmartArt, Venn, chevron/process flow, timeline, flowchart, org/hierarchy chart, quadrant, or puzzle-piece graphic).

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
