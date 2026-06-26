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


def write_pdf_without_pages(src: Path, dst: Path, drop_pages_1based: List[int]) -> int:
    """Write `src` to `dst` keeping every page except those in `drop_pages_1based`.

    Pages are 1-based to match the rendered PNG numbering. Returns the new page
    count. Raises ValueError if any page is out of range or all pages are dropped.
    """
    with fitz.open(src) as doc:
        total = doc.page_count
        drop = {int(p) for p in drop_pages_1based}
        for p in drop:
            if p < 1 or p > total:
                raise ValueError(f"page {p} is out of range 1..{total}")
        keep = [i for i in range(total) if (i + 1) not in drop]  # 0-based
        if not keep:
            raise ValueError("refusing to write a PDF with zero pages")
        doc.select(keep)
        doc.save(str(dst))
        return len(keep)
