# Text Sizing and Spacing

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether **text sizing and spacing** are preserved — checking for heading over/undersizing, spacing inflation, text rendered too small, or headings demoted to body text.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Compare text sizing between source and output:
   - **Headings**: Are heading sizes roughly proportional to the source? A large heading should stay large, a small subheading should stay small.
   - **Body text**: Is body text at a readable, proportional size?
   - **Size hierarchy**: Is the relative sizing between heading, subheading, and body text preserved? (H1 > H2 > body)
2. Compare spacing:
   - **Line spacing**: Is the space between lines similar?
   - **Section spacing**: Is the space between content blocks (headings, paragraphs, lists) similar?
   - **Spacing inflation**: Has spacing been dramatically increased, making the card taller or content more spread out than the source?
3. Check for type-level demotion:
   - Headings rendered as body text (same size as paragraphs)
   - Display text shrunk to regular heading size
   - Labels or captions rendered at body text size

## Verdicts

- **pass** — Text sizing and spacing closely match the source. The heading hierarchy and spacing rhythm are preserved. Minor differences in exact point sizes are acceptable.
- **borderline** — Text is readable and the hierarchy is recognizable, but there are noticeable sizing or spacing differences — e.g., headings are somewhat larger or smaller, spacing is noticeably tighter or looser than the source.
- **fail** — Significant text sizing or spacing issues: headings dramatically over/undersized, spacing inflation that makes the slide much taller, text too small to read, or headings demoted to body text size.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
