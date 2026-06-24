# Labels / Pills

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether label/pill elements (small badge-like components with colored backgrounds and short text) retain their visual container and styling after import.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify all label/pill elements in `input_slide`: look for small badge-like elements — colored rounded-rectangle or pill shapes containing short text such as tags, categories, status indicators, or feature labels.
2. For each pill found, check in `output_slide` whether it still renders as a pill (container present, rounded shape) and whether its styling is preserved — including background color, text color, border radius, border, and text casing. Also check for nested-pill layouts if present.
3. Note any of these failure patterns:
   - A pill is flattened to plain text with no visible container or background
   - A pill is missing entirely from the output
   - A pill has a completely wrong background color or text color (not a minor shade difference)
   - A pill has wrong text casing (e.g., ALL CAPS changed to Title Case)
   - A pill has a noticeably different shape (e.g., sharp corners instead of rounded)
   - A nested-pill layout is broken or collapsed

## Verdicts

- **pass** - Every pill in the source retains its pill appearance (rounded container with background) and correct styling in the output. Minor color-shade differences or slight size variation are still a pass.
- **borderline** - All pills still render as pills (container/pill form factor preserved) but one or more have noticeable issues: wrong background color, wrong text casing, or a slightly different shape.
- **fail** - One or more pills are flattened to plain text (container lost), given completely wrong styling, or missing entirely. When multiple pills are present, grade by the most severe: any pill flattened or missing results in Fail.
- **na** - The source slide contains no label or pill elements.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
