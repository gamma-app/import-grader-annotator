#!/usr/bin/env python3
"""CLI helper: render a PDF into per-page PNGs.

Run with the backend venv so PyMuPDF is available, e.g.:
    backend/.venv/bin/python scripts/split_pdf.py input.pdf out_dir --width 1600
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.pdf_split import render_pdf_to_pngs  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Render a PDF to one PNG per page.")
    ap.add_argument("pdf", help="path to the source PDF")
    ap.add_argument("out_dir", help="directory to write NNN.png files into")
    ap.add_argument("--width", type=int, default=1600, help="output width in px (default 1600)")
    args = ap.parse_args()

    paths = render_pdf_to_pngs(Path(args.pdf), Path(args.out_dir), width=args.width)
    print(f"Wrote {len(paths)} pages to {args.out_dir}")


if __name__ == "__main__":
    main()
