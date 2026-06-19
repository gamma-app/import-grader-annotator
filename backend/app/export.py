"""Consolidated JSON + tidy/long CSV exports of all annotations."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from . import config, storage
from .modes import MODE_BY_ID, MODES

TIDY_COLUMNS = [
    "deck_slug",
    "title",
    "variant",
    "variant_label",
    "annotator",
    "level",
    "pair_index",
    "input_image",
    "output_image",
    "mode_id",
    "mode_name",
    "element",
    "dimension",
    "severity",
    "grade",
    "note",
    "updated_at",
]


def _collect() -> List[Dict]:
    """Render (if needed), sync, and gather every deck's annotation."""
    decks: List[Dict] = []
    for slug in storage.list_slugs():
        storage.ensure_rendered(slug)
        decks.append(storage.sync_annotation(slug))
    return decks


VARIANT_LABEL = {v["key"]: v["label"] for v in config.VARIANTS}


def _tidy_rows(decks: List[Dict]) -> List[Dict]:
    rows: List[Dict] = []
    for ann in decks:
        slug = ann["deck_slug"]
        title = ann.get("title", slug)
        annotator = ann.get("annotator", "")

        for vkey, variant in ann.get("variants", {}).items():
            vlabel = VARIANT_LABEL.get(vkey, vkey)

            for mid_str, cell in variant.get("deck_level", {}).items():
                mode = MODE_BY_ID.get(int(mid_str), {})
                rows.append(
                    {
                        "deck_slug": slug,
                        "title": title,
                        "variant": vkey,
                        "variant_label": vlabel,
                        "annotator": annotator,
                        "level": "deck",
                        "pair_index": "",
                        "input_image": "",
                        "output_image": "",
                        "mode_id": mid_str,
                        "mode_name": mode.get("name", ""),
                        "element": mode.get("element", ""),
                        "dimension": mode.get("dimension", ""),
                        "severity": mode.get("severity", ""),
                        "grade": cell.get("grade", "ungraded"),
                        "note": cell.get("note", ""),
                        "updated_at": variant.get("updated_at", ann.get("updated_at", "")),
                    }
                )

            for pair in variant.get("pairs", []):
                for mid_str, cell in pair.get("modes", {}).items():
                    mode = MODE_BY_ID.get(int(mid_str), {})
                    rows.append(
                        {
                            "deck_slug": slug,
                            "title": title,
                            "variant": vkey,
                            "variant_label": vlabel,
                            "annotator": annotator,
                            "level": "slide",
                            "pair_index": pair["index"],
                            "input_image": pair.get("input_image", ""),
                            "output_image": pair.get("output_image", ""),
                            "mode_id": mid_str,
                            "mode_name": mode.get("name", ""),
                            "element": mode.get("element", ""),
                            "dimension": mode.get("dimension", ""),
                            "severity": mode.get("severity", ""),
                            "grade": cell.get("grade", "ungraded"),
                            "note": cell.get("note", ""),
                            "updated_at": pair.get("updated_at", ""),
                        }
                    )
    return rows


def run_export() -> Dict:
    config.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    decks = _collect()
    generated_at = datetime.now(timezone.utc).isoformat()

    json_path = config.EXPORTS_DIR / "consolidated.json"
    payload = {"generated_at": generated_at, "modes": MODES, "decks": decks}
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    rows = _tidy_rows(decks)
    csv_path = config.EXPORTS_DIR / "tidy.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TIDY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "generated_at": generated_at,
        "deck_count": len(decks),
        "row_count": len(rows),
        "json_path": str(json_path),
        "csv_path": str(csv_path),
    }
