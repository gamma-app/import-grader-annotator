# Logo dropped

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether every logo present in the source slide is faithfully reproduced in the imported output.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Examine `input_slide` for any logos — defined as company/brand wordmarks, partner or client logos, and product logos (recognizable brand marks). This **includes** company or brand name text placed in a consistent footer, corner, or header branding position (e.g. "Amour Urbane", "MOMENTUM", "LUMIO" in the bottom-left footer), even if rendered in plain text without a graphic mark, because these function as the deck's brand identifier. Exclude: decorative photos, generic UI icons, app screenshots, illustrative imagery, brand names printed on product packaging within a product photo (the name on a can label is part of the photo, not a standalone logo), and generic section/category labels (e.g. "LEGACY INFRASTRUCTURE", "VENDOR COMPARISON", "CHAPTER 3").

2. For each logo identified in `input_slide`, classify it as **primary** (the slide's main brand mark — largest/most prominent, or in a header/title/corner-brand/footer position as the deck's sole brand identifier) or **secondary** (partner/client logos, small supplementary marks, logos in a "trusted by" grid, or additional logos when a primary logo also exists on the same slide).

3. For each logo identified in `input_slide`, check whether it appears in `output_slide` and assess: presence, recognizability, brand-correct color and proportion, and approximate scale.

4. **Special classification rules:**
   - A footer/corner company name wordmark (even plain text) is the **primary** logo when it is the sole brand identifier on the slide. Its complete absence is a **Fail**.
   - A small brand-associated icon embedded *inside* a content/category badge (e.g. a paperclip icon inside an "ENGAGEMENT TOOL" pill badge) is a **decorative UI element**, not a standalone logo. Its substitution with a generic icon does not affect the logo verdict if the standalone brand wordmark is otherwise intact.
   - Brand names or marks that appear only as part of product packaging artwork within a photo (printed on the product itself, not placed separately on the slide) are **not** standalone logos.
   - A logo added to the output that does not exist as a standalone logo in the source slide is a spurious addition — this is only a failure mode if the source slide already contained at least one qualifying logo.

5. Note any of these failure patterns:
   - A primary logo is missing, replaced by text/initials/a pill/a placeholder/a generic icon, or rendered unrecognizable (e.g. white logo on white fill, extreme distortion, severe cropping)
   - All logos on the slide are dropped or replaced
   - An entire partner-logo row or grid is dropped
   - A secondary logo is dropped, replaced, or distorted while all primary logos remain intact
   - Any logo is clearly mis-scaled (noticeably too big or too small) but still recognizable
   - Any logo is recolored, forced to monochrome, mildly stretched, partially cropped, or rendered blurry/low-res yet still identifiable
   - A few logos are missing from a larger partner grid while most remain
   - A logo is duplicated, or a spurious logo not in the source is added (only applicable when source has at least one logo)

## Verdicts

- **pass** - Every source logo is present in the output, recognizable, in brand-correct color and proportion, at roughly appropriate scale. Acceptable differences include repositioning, modest size changes, minor padding/cropping that doesn't hurt recognizability, reordering of logos within a row/grid, and substitution of a small brand-associated icon *inside a content badge* (not a standalone logo placement) when the standalone wordmark is intact.

- **borderline** - The failure mode applies and fidelity is degraded, but core brand identity survives: a secondary logo is dropped, replaced, or distorted while all primary logos remain intact; a logo is clearly mis-scaled but still recognizable; a logo is recolored, forced to monochrome, mildly stretched, partially cropped, or blurry/low-res yet still identifiable; a few logos are missing from a larger partner grid (most remain); or a spurious logo is added to an output slide that already had at least one source logo. If any primary logo hits the Fail bar, do not use Borderline.

- **fail** - Any primary logo is missing, completely absent, or replaced by text/initials/a pill/a placeholder/a generic icon; any logo is so mis-scaled, distorted, recolored, cropped, or low-res that it is unrecognizable (effectively dropped); all logos on the slide are dropped or replaced; or an entire partner-logo row/grid is dropped. **Specifically: if the footer/corner company wordmark is the sole brand identifier on the slide and it is completely absent from the output, that is Fail** — the entire brand presence is lost. When multiple logos are present, grade by the most severe case weighted by importance — a single primary logo failure makes the whole slide Fail.

- **na** - The `input_slide` contains no logos by the definition above (no company/brand wordmarks, partner or client logos, product logos, or footer/corner brand name identifiers). Plain text that functions only as a generic section label, category tag, or third-party attribution line (e.g. "Prepared by: Mosaic Health Advisors") does not qualify as a logo. If a logo exists in the source, this verdict is never applicable regardless of what the output shows. If the output adds a spurious logo but the source had none, the verdict remains **na**.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
