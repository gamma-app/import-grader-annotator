# Text sizing & spacing

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether text sizing and spacing (heading sizes, body-text readability, size hierarchy, line spacing, and section spacing) are faithfully preserved after import.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. In `input_slide`, identify all text elements and note: heading sizes (H1, H2, etc.), body text size, the size hierarchy between levels, line spacing within blocks, and spacing between sections/blocks.
2. In `output_slide`, compare each of those properties against the source: check whether headings remain proportionally large, body text remains readable, the H1 > H2 > body hierarchy is preserved, and spacing rhythm (line spacing and section gaps) matches the source.
3. Note any of these failure patterns:
   - Headings dramatically oversized or undersized relative to the source
   - Size hierarchy broken (e.g., H1 and H2 appear the same size, or headings shrink to body-text size)
   - Headings demoted to body-text size (type-level demotion)
   - Display text or large decorative text shrunk significantly
   - Body text too small to read comfortably
   - Spacing inflation: line spacing or section gaps are so much larger that the slide appears much taller or more spread out than the source
   - Spacing compression: text blocks are unnaturally cramped compared to the source

## Verdicts

- **pass** - Heading sizes, body text size, size hierarchy, line spacing, and section spacing all closely match the source. Minor point-size differences are acceptable as long as hierarchy and rhythm are preserved.
- **borderline** - Text is readable and the hierarchy is still recognizable, but there are noticeable differences — headings are somewhat larger or smaller than in the source, or spacing is noticeably tighter or looser, without being severe enough to break readability or hierarchy.
- **fail** - One or more significant issues: headings are dramatically over- or undersized, any heading is demoted to body-text size, body text is too small to read, or spacing inflation makes the slide substantially taller/more spread out than the source.
- **na** - The source slide contains no text (e.g., a pure image or cover slide with no readable text elements).

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
