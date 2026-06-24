# Icons dropped / swapped

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether small symbolic icons, pictograms, and emoji present in the source slide are faithfully reproduced in the imported version.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify all icons, pictograms, and emoji in `input_slide` — these are small symbolic glyphs that sit alongside text (e.g., feature icons, list/step markers, inline UI glyphs). Exclude logos, photographs, and large illustrations. For each icon, note whether it is **meaning-bearing** (labels or encodes a feature, step, or list item) or **decorative** (purely ornamental). If none exist, verdict is **na**.
2. For each identified icon, check whether it appears in `output_slide` with the same meaning and visual identity — same glyph or a recognizably equivalent one, same general placement, same communicative role.
3. Note any of these failure patterns:
   - An icon is entirely absent (dropped) from the output
   - An icon is replaced by an unrelated or wrong glyph that changes its meaning
   - An icon is rendered as a placeholder box, broken image, or literal text (e.g., `:check:`, `:star:`, or a plain bullet substituted for an icon)
   - An entire row, set, or group of icons is missing
   - A meaning-bearing icon is restyled so severely (e.g., outline↔filled swap combined with a different icon shape) that it no longer reads as the same symbol

## Verdicts

- **pass** - Every source icon appears in the output conveying the same meaning. Minor rendering differences, color shifts, use of an equivalent glyph from a different icon set, or small repositioning are all acceptable.
- **borderline** - Icons are present and meaning is preserved overall, but one or more icons are noticeably altered: restyled (e.g., outline↔filled), recolored or resized while still recognizable as the same icon, or a single **decorative** icon is dropped while all meaning-bearing icons remain intact.
- **fail** - One or more **meaning-bearing** icons are dropped, replaced by a wrong/unrelated glyph that changes meaning, rendered as a placeholder/broken image, or converted to literal text or a plain bullet; OR an entire icon set or row is lost.
- **na** - The source slide contains no icons, pictograms, or emoji (only logos, photographs, or large illustrations, or no image elements at all).

When the slide contains a mix of meaning-bearing and decorative icons: any meaning-bearing icon dropped or wrong → **fail**; only minor restyles or a single stray decorative icon dropped → **borderline**; all icons clear the bar → **pass**.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
