# Text Highlight Lost

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether decorative text highlights (colored background bands behind specific words or phrases) are preserved correctly in the imported output.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Examine `input_slide` for any text highlights: colored background rectangles or bands placed directly behind specific words or phrases to create a highlighter-pen emphasis effect. Do not confuse these with bold/italic formatting, colored text (where the text characters themselves are colored), or a container/shape background fill behind a whole text block.
2. For each highlighted phrase found, check whether the same phrase in `output_slide` also carries a colored background highlight, and whether the highlight color and extent (which words are covered) match the source.
3. Note any of these failure patterns:
   - A highlighted phrase in `input_slide` appears as completely plain (unhighlighted) text in `output_slide` — highlight dropped entirely.
   - A highlight is present in `output_slide` but uses a noticeably different color from the source.
   - A highlight is present but covers more or fewer words than in the source.
   - A highlight is present but rendered in a significantly different style (e.g., underline instead of background band).

## Verdicts

- **pass** - All highlights identified in `input_slide` are present in `output_slide` with matching or very similar colors and coverage.
- **borderline** - All highlights are still present in `output_slide` but with noticeable differences: wrong highlight color, applied to more or fewer words than the source, or a significantly different highlight style.
- **fail** - One or more highlighted phrases from `input_slide` appear as plain (unhighlighted) text in `output_slide` — the highlight has been dropped entirely. If multiple highlights exist and at least one is dropped, grade as **fail**.
- **na** - `input_slide` contains no text highlights (no colored background bands behind specific words or phrases).

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
