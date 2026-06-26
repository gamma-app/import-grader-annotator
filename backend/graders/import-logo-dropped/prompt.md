# Logo dropped

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether every logo present in the source slide is faithfully reproduced in the imported output.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

### Step 1 — Identify logos in `input_slide`

A **logo** is any of the following:
- A company or brand wordmark — including a brand name that appears in a dedicated footer, corner, or watermark position on the slide (e.g. "Amour Urbane" in the bottom-left, "MOMENTUM" in the bottom-left, "LUMIO" in the bottom-left). Such footer/corner brand names count as wordmark logos **even if they use no custom typeface, icon, or graphic emblem** — their consistent placement as the deck's brand identifier is what matters.
- A partner or client logo (standalone, not embedded in body text).
- A product logo presented as a standalone graphic element on the slide.

**Do NOT count as logos:**
- Decorative photos, generic UI icons, app screenshots, or illustrative imagery.
- Brand names or wordmarks that appear **only as part of product packaging or photography** (e.g. a brand name printed on a can in a product photo). These are part of the illustrative image, not standalone slide logos.
- Section-label badges or content-category pills (e.g. "ACTIVITY IDEA", "FILE INTEGRATION", "BEFORE") — these are slide UI elements, not brand logos, unless they are the only brand identifier on the slide and are clearly the deck's primary brand mark.
- Client or subject names mentioned in slide body text or titles (e.g. "MERIDIAN BANK" as part of a headline).

### Step 2 — Classify each logo

Classify each logo found as **primary** or **secondary**:

- **Primary**: the slide's main brand mark — the logo of the company/organization that produced the deck. This is typically the largest or most prominent logo, OR the logo in a header/title/corner-brand position, OR the logo in a consistent footer/watermark position across the deck. If a footer/corner brand name is the **only** brand mark on the slide, it is primary.
- **Secondary**: partner/client logos, small supplemental marks, logos in a "trusted by" grid, or additional logos that appear alongside an already-identified primary logo.

**Tie-breaking rule for footer names**: When a brand name (e.g. "LUMIO", "MOMENTUM", "Amour Urbane") appears in the footer/corner and is the only brand mark on the slide, treat it as the **primary** logo.

### Step 3 — Check each logo in `output_slide`

For each logo found in `input_slide`, determine whether it appears in `output_slide` — present, recognizable, in brand-correct color and proportion, at roughly appropriate scale.

### Step 4 — Identify failure patterns

Note any of these:
- A primary logo is missing, replaced by text/initials/a pill/a placeholder/a generic icon, or rendered unrecognizable
- All logos on the slide are dropped or replaced
- An entire partner-logo row or grid is dropped
- A secondary logo is dropped, replaced, or distorted while all primary logos remain intact
- Any logo is clearly mis-scaled (noticeably too big or too small) but still recognizable
- Any logo loses a distinctive visual element (e.g. a decorative arc, icon, or emblem) while the wordmark text remains intact and readable
- Any logo is recolored, forced to monochrome, mildly stretched, partially cropped, or rendered blurry/low-res yet still identifiable
- A few logos are missing from a larger partner grid (most remain)
- A logo is duplicated, or a spurious logo not in the source is added

## Verdicts

- **pass** — Every source logo is present in the output, recognizable, in brand-correct color and proportion, at roughly appropriate scale. Repositioning, modest size changes, minor padding/cropping that doesn't hurt recognizability, and reordering within a row/grid are all acceptable.

- **borderline** — The failure mode applies and fidelity is degraded, but core brand identity survives: a secondary logo is dropped, replaced, or distorted while all primary logos remain intact; or any logo loses a decorative element (e.g. an arc, icon, or emblem) while its wordmark text remains fully readable and recognizable; or a logo is clearly mis-scaled but still recognizable; or a logo is recolored, forced to monochrome, mildly stretched, partially cropped, or blurry/low-res yet still identifiable; or a few logos are missing from a larger partner grid (most remain); or a logo is duplicated or a spurious logo is added.

- **fail** — Brand identity is lost: any primary logo is missing, dropped, or replaced by text/initials/a pill/a placeholder/a generic icon; or any logo is so mis-scaled, distorted, recolored, cropped, or low-res that it is unrecognizable (effectively dropped); or all logos on the slide are dropped or replaced; or an entire partner-logo row/grid is dropped. **Tie-breaker:** if any primary logo hits the fail bar, the slide is Fail; if only secondary logos are affected while every primary is intact, it is Borderline.

- **na** — The source slide contains no logos by the definition above. Specifically: there is no company/brand wordmark in a footer/corner/header position, no standalone partner or client logo, and no standalone product logo. Brand names visible only on product packaging within photos do not count. If any qualifying logo exists in the source, this verdict is never applicable regardless of what the output shows.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
