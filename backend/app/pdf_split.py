"""Render a PDF into one PNG per page using PyMuPDF (no system deps)."""
from __future__ import annotations

from pathlib import Path
from typing import List

import fitz  # PyMuPDF


def render_pdf_to_pngs(pdf_path: Path, out_dir: Path, width: int = 1600) -> List[Path]:
    """Render each page of `pdf_path` to `out_dir/NNN.png` (1-indexed, zero-padded).

    Returns the sorted list of written PNG paths. Clears any stale PNGs first so
    re-rendering a changed PDF never leaves orphan pages behind.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.png"):
        stale.unlink()

    written: List[Path] = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            page_width = page.rect.width or width
            zoom = width / page_width
            matrix = fitz.Matrix(zoom, zoom)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            target = out_dir / f"{i:03d}.png"
            pixmap.save(target)
            written.append(target)
    return written


def pdf_page_count(pdf_path: Path) -> int:
    with fitz.open(pdf_path) as doc:
        return doc.page_count
