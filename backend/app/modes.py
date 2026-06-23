"""The failure-mode registry, derived from the Import Evals Taxonomy (PSSL).

24 distinct modes (#16 is merged into #7). Mode #18 is graded once per deck;
all others are graded per slide pair. Severity/dimension are carried for context
only and are not editable by annotators.
"""
from __future__ import annotations

from typing import Dict, List

# Display order for grouping in the UI.
ELEMENT_ORDER = [
    "Images",
    "Components",
    "Headers/Footers/Ornaments",
    "Backgrounds & fills",
    "Typography & Colors",
    "Card & composition",
]

GRADES = ["ungraded", "pass", "borderline", "fail"]

MODES: List[Dict] = [
    {"id": 1, "name": "Logo dropped", "element": "Images", "dimension": "Presence", "severity": "P1", "level": "pair"},
    {"id": 2, "name": "Headers & footers dropped", "element": "Headers/Footers/Ornaments", "dimension": "Presence", "severity": "P0", "level": "pair"},
    {"id": 3, "name": "Text sizing & spacing", "element": "Typography & Colors", "dimension": "Scale", "severity": "P1", "level": "pair"},
    {"id": 4, "name": "Divider mishandling", "element": "Headers/Footers/Ornaments", "dimension": "Presence", "severity": "P2", "level": "pair"},
    {"id": 5, "name": "Decorations dropped", "element": "Headers/Footers/Ornaments", "dimension": "Presence", "severity": "P2", "level": "pair"},
    {"id": 6, "name": "Diagrams flattened to primitives", "element": "Components", "dimension": "Presence", "severity": "P1", "level": "pair"},
    {"id": 7, "name": "Color zones / fills misassigned", "element": "Backgrounds & fills", "dimension": "Styling", "severity": "P1", "level": "pair", "aka": "merged with #16"},
    {"id": 8, "name": "Layout direction changed", "element": "Card & composition", "dimension": "Layout", "severity": "P1", "level": "pair"},
    {"id": 9, "name": "Icons dropped / swapped", "element": "Images", "dimension": "Presence", "severity": "P2", "level": "pair"},
    {"id": 10, "name": "Background / hero images dropped", "element": "Images", "dimension": "Presence", "severity": "P1", "level": "pair"},
    {"id": 11, "name": "Heading alignment", "element": "Card & composition", "dimension": "Layout", "severity": "P2", "level": "pair"},
    {"id": 12, "name": "Slides too tall / 16:9 broken", "element": "Card & composition", "dimension": "Layout", "severity": "P1", "level": "pair"},
    {"id": 13, "name": "Forced into accent treatment", "element": "Images", "dimension": "Layout", "severity": "P1", "level": "pair"},
    {"id": 14, "name": "Table styling / size", "element": "Components", "dimension": "Styling", "severity": "P1", "level": "pair"},
    {"id": 15, "name": "Labels / pills", "element": "Components", "dimension": "Styling", "severity": "P2", "level": "pair"},
    {"id": 17, "name": "Chart conversion + data loss", "element": "Components", "dimension": "Presence", "severity": "P0", "level": "pair"},
    {"id": 18, "name": "Brand color remapping", "element": "Typography & Colors", "dimension": "Styling", "severity": "P1", "level": "deck"},
    {"id": 19, "name": "Text color / emphasis drift", "element": "Typography & Colors", "dimension": "Styling", "severity": "P2", "level": "pair"},
    {"id": 20, "name": "Forced component substitution", "element": "Components", "dimension": "Presence", "severity": "P2", "level": "pair"},
    {"id": 21, "name": "Flaky / inconsistent handling", "element": "Images", "dimension": "Presence", "severity": "P2", "level": "pair"},
    {"id": 22, "name": "Bullet size / shape / color", "element": "Typography & Colors", "dimension": "Scale", "severity": "P2", "level": "pair"},
    {"id": 23, "name": "Icons / emoji / images oversized", "element": "Images", "dimension": "Scale", "severity": "P2", "level": "pair"},
    {"id": 24, "name": "Card frames / borders", "element": "Headers/Footers/Ornaments", "dimension": "Presence", "severity": "P2", "level": "pair"},
    {"id": 25, "name": "Text highlight lost", "element": "Typography & Colors", "dimension": "Styling", "severity": "P2", "level": "pair"},
]

PAIR_MODE_IDS = [m["id"] for m in MODES if m["level"] == "pair"]
DECK_MODE_IDS = [m["id"] for m in MODES if m["level"] == "deck"]
MODE_BY_ID = {m["id"]: m for m in MODES}

# Maps each failure mode to its VLM grader in gamma's packages/import-evals/graders.
# 22 of 24 modes have a 1:1 slide-level grader. The two Nones are intentional:
#   #18 Brand color remapping  -> deck-level; the import suite is slide-level only.
#   #21 Flaky / inconsistent   -> cross-slide judgment a single pair grader can't make.
MODE_GRADERS: Dict[int, str] = {
    1: "import-logo-dropped",
    2: "import-headers-footers-dropped",
    3: "import-text-sizing-spacing",
    4: "import-divider-mishandling",
    5: "import-decorations-dropped",
    6: "import-diagrams-flattened",
    7: "import-color-zones-misassigned",
    8: "import-layout-direction-changed",
    9: "import-icons-dropped-swapped",
    10: "import-background-images-dropped",
    11: "import-heading-alignment",
    12: "import-slides-too-tall",
    13: "import-forced-accent-treatment",
    14: "import-table-styling",
    15: "import-labels-pills",
    17: "import-chart-data-loss",
    19: "import-text-color-emphasis-drift",
    20: "import-forced-component-substitution",
    22: "import-bullet-styling",
    23: "import-images-oversized",
    24: "import-card-borders",
    25: "import-text-highlight-lost",
}

# Modes shown in the grading rail that have no VLM grader (UI shows "no AI grader").
UNGRADEABLE_MODE_IDS = [m["id"] for m in MODES if m["id"] not in MODE_GRADERS]
