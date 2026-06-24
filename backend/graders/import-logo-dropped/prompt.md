# Logo dropped

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether every logo present in the source slide is faithfully reproduced in the imported output.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Examine `input_slide` for any logos — defined as company/brand wordmarks, partner or client logos, and product logos (recognizable brand marks). Exclude decorative photos, generic UI icons, app screenshots, and illustrative imagery. For each logo found, classify it as **primary** (the slide's main brand mark — largest/most prominent, or in a header/title/corner-brand position) or **secondary** (partner/client logos, small footer or watermark marks, logos in a "trusted by" grid).
2. For each logo identified in `input_slide`, check whether it appears in `output_slide` and assess: presence, recognizability, brand-correct color and proportion, and approximate scale. Note whether it is a primary or secondary logo.
3. Note any of these failure patterns:
   - A primary logo is missing, replaced by text/initials/a pill/a placeholder/a generic icon, or rendered unrecognizable (e.g. white logo on white fill, extreme distortion, severe cropping)
   - All logos on the slide are dropped or replaced
   - An entire partner-logo row or grid is dropped
   - A secondary logo is dropped, replaced, or distorted while all primary logos remain intact
   - Any logo is clearly mis-scaled (noticeably too big or too small) but still recognizable
   - Any logo is recolored, forced to monochrome, mildly stretched, partially cropped, or rendered blurry/low-res yet still identifiable
   - A few logos are missing from a larger partner grid while most remain
   - A logo is duplicated, or a spurious logo not in the source is added

## Verdicts

- **pass** - Every source logo is present in the output, recognizable, in brand-correct color and proportion, at roughly appropriate scale. Acceptable differences include repositioning, modest size changes, minor padding/cropping that doesn't hurt recognizability, and reordering of logos within a row/grid.
- **borderline** - The failure mode applies and fidelity is degraded, but core brand identity survives: a secondary logo is dropped, replaced, or distorted while all primary logos remain intact; a logo is clearly mis-scaled but still recognizable; a logo is recolored, forced to monochrome, mildly stretched, partially cropped, or blurry/low-res yet still identifiable; a few logos are missing from a larger partner grid (most remain); or a logo is duplicated or a spurious logo is added. If any primary logo hits the Fail bar, do not use Borderline.
- **fail** - Any primary logo is missing or replaced by text/initials/a pill/a placeholder/a generic icon; any logo is so mis-scaled, distorted, recolored, cropped, or low-res that it is unrecognizable (effectively dropped); all logos on the slide are dropped or replaced; or an entire partner-logo row/grid is dropped. When multiple logos are present, grade by the most severe case weighted by importance — a single primary logo failure makes the whole slide Fail.
- **na** - The `input_slide` contains no logos by the definition above (no company/brand wordmarks, partner or client logos, or product logos). If a logo exists in the source, this verdict is never applicable regardless of what the output shows.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
