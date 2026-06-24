# Headers and Footers Dropped

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether **headers, footers, page numbers, confidentiality lines, or compliance text** from the source are dropped in the output.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify header and footer content in the source slide. This includes:
   - **Page/slide numbers** (typically bottom-right or bottom-center)
   - **Footer text** (company name, date, document title — typically at the bottom)
   - **Confidentiality/legal lines** ("CONFIDENTIAL", "ATTORNEY WORK PRODUCT", "DRAFT", copyright notices)
   - **Header bars or text** (persistent branding or section labels at the top)
2. Check whether each of these elements is preserved in the output.
3. Note: headers/footers often have specific formatting (smaller text, different color, positioned at slide edges). They may appear in different footer layouts per deck.

## Verdicts

- **pass** — All header/footer content from the source is present in the output. Minor positional shifts are acceptable as long as the content is there.
- **borderline** — Most header/footer content is present, but minor elements are missing (e.g., a date is dropped but the company name and page number remain) or formatting is noticeably different.
- **fail** — Significant header/footer content is dropped: page numbers missing, confidentiality/compliance text gone, or footer text entirely absent. This is especially critical for legal/compliance text (P0 severity).

If the source slide has no headers, footers, page numbers, or compliance text, verdict is **pass**.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```
