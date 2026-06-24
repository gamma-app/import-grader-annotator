# Text Highlight Lost

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether **decorative text highlights** (colored background behind key phrases) are preserved in the output.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify text highlights in the source slide. These are colored background rectangles or bands behind specific words or phrases — used for visual emphasis, similar to a highlighter pen effect. They are distinct from:
   - Bold/italic (character formatting)
   - Colored text (different text color)
   - Background fills on entire containers
2. Check whether these highlights are preserved in the output.
3. A common failure pattern: highlights drop while other emphasis (like bold) survives, making previously highlighted text look the same as surrounding text.

## Verdicts

- **pass** — All text highlights from the source are present in the output with matching or very similar color.
- **borderline** — Highlights are present but with noticeable differences: wrong highlight color, highlights applied to more or fewer words than in the source, or a significantly different highlight style.
- **fail** — Text highlights are dropped entirely — highlighted phrases in the source appear as plain (unhighlighted) text in the output.

If the source slide contains no text highlights, verdict is **pass**.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
