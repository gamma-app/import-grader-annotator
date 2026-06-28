#!/usr/bin/env python3
"""CLI helper: pack per-page PNGs into a single PDF (one image per page).

The inverse of split_pdf.py. Useful for ingesting pre-rendered slide images
(e.g. an exported analysis bundle) into the grader, which is PDF-in.

Run with the backend venv so PyMuPDF is available, e.g.:
    backend/.venv/bin/python scripts/images_to_pdf.py img_dir out.pdf --pattern "imp-*.png"
"""
import argparse
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF


def _num_key(p: Path):
    """Sort by the last run of digits in the filename so imp-2 < imp-10."""
    nums = re.findall(r"\d+", p.name)
    return (int(nums[-1]) if nums else 0, p.name)


def main() -> None:
    ap = argparse.ArgumentParser(description="Pack PNGs into a one-image-per-page PDF.")
    ap.add_argument("img_dir", help="directory containing the page images")
    ap.add_argument("out_pdf", help="path to write the combined PDF")
    ap.add_argument("--pattern", default="*.png", help="glob for page images (default: *.png)")
    args = ap.parse_args()

    img_dir = Path(args.img_dir)
    images = sorted(img_dir.glob(args.pattern), key=_num_key)
    if not images:
        print(f"No images matching {args.pattern!r} in {img_dir}", file=sys.stderr)
        sys.exit(1)

    doc = fitz.open()
    for img_path in images:
        with fitz.open(img_path) as img:
            pdf_bytes = img.convert_to_pdf()
        with fitz.open("pdf", pdf_bytes) as img_pdf:
            doc.insert_pdf(img_pdf)

    out_pdf = Path(args.out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_pdf))
    doc.close()
    print(f"Wrote {len(images)} pages to {out_pdf}")


if __name__ == "__main__":
    main()
