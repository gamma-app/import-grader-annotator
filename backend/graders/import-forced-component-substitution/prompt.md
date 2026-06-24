# Forced component substitution

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether the import has imposed Gamma-specific UI components onto content that had a different (often simpler or custom) visual treatment in the source.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Examine the `input_slide` and identify how each content element is visually treated: plain text blocks, free-form or custom image arrangements, static text sections, freely-placed content, and any custom styling that does not use standard UI component wrappers.
2. Compare each element in the `output_slide` to its source counterpart and check whether Gamma has replaced the original treatment with one of its own component primitives.
3. Note any of these failure patterns:
   - Blockquote accent bars (vertical side bars) applied to text that was plain, unquoted body text in the source
   - Info/callout/alert containers wrapped around content that was plain and unboxed in the source
   - A photo gallery grid or uniform image grid replacing a custom mosaic, collage, or free-form image arrangement
   - Toggle or accordion sections introduced where the source had static, always-visible content
   - Card wrappers or bordered/shaded containers placed around content that was freely positioned without such framing in the source

## Verdicts

- **pass** - The output preserves the source's visual treatment for all elements; no Gamma-specific components have been substituted for the source-native layouts or styling.
- **borderline** - A minor substitution is present that does not significantly alter the slide's overall visual character (e.g., a subtle container-style difference on one element, or a mild callout styling added to a single item).
- **fail** - One or more clear substitutions are visible: blockquote bars on un-quoted text, callout/info boxes around plain content, gallery grids replacing custom image arrangements, toggles/accordions replacing static content, or card wrappers imposed on freely-placed content. When multiple elements are affected, grade by the most severe case — any single clear forced substitution warrants a fail.
- **na** - The source slide contains no content that could be subject to component substitution (e.g., the slide is blank, contains only a title, or every element is already a standard Gamma-compatible component in the source).

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
