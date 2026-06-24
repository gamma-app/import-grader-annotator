# Headers & footers dropped

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether header and footer content present in the source slide is preserved in the imported output.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. Examine `input_slide` for any header or footer content: page/slide numbers; footer text such as company name, date, or document title; confidentiality, legal, or compliance lines (e.g., "CONFIDENTIAL", "ATTORNEY WORK PRODUCT", "DRAFT", copyright notices); and persistent header bars or section labels. These often appear as small, muted text at the edges of the slide. If none exist, verdict is **na**.
2. For each header/footer element identified, check whether it appears in `output_slide` — look at slide edges, top and bottom bars, and any small text regions. Note whether the content is present, partially present, or absent, and whether any formatting differences are significant.
3. Note any of these failure patterns:
   - Page numbers missing entirely from the output
   - Footer text (company name, date, document title) entirely absent
   - Any confidentiality, legal, or compliance text (e.g., "CONFIDENTIAL", "DRAFT", "ATTORNEY WORK PRODUCT", copyright) missing — even if other footer elements survive
   - A whole footer or header region dropped with no equivalent in the output
   - A minor individual element (e.g., date only) missing while other footer elements remain
   - Noticeably different formatting that changes the appearance of footer content

## Verdicts

- **pass** - All header/footer content from `input_slide` is present in `output_slide`. Minor positional shifts or small formatting changes are acceptable as long as the content itself is there.
- **borderline** - Most header/footer content is present but a minor non-legal element is missing (e.g., the date is dropped while the company name and page number remain), or formatting differences are noticeable but all content is technically present.
- **fail** - Significant content is dropped: page numbers are missing, footer text is entirely absent, or any confidentiality/compliance/legal text is gone — even if other footer elements survive. When multiple elements are affected, grade by the most severe loss: any legal/compliance text or a whole footer dropped is a Fail.
- **na** - The source slide contains no headers, footers, page numbers, or compliance/legal text of any kind.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```
