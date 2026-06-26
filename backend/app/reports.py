"""Per-failure-mode agreement reports: human grades vs. AI-grader verdicts.

Read-only. For one (mode, variant) we join the human annotation store with the
AI-grades store across every deck, keeping only slide pairs that have BOTH a
human grade and an AI verdict in {pass, borderline, fail, na}. Everything else
(ungraded / missing / error / skip) is excluded but counted for context.
Never contacts the eval-server and never triggers a render.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from . import ai_grader, config, storage
from .modes import MODE_BY_ID, MODE_GRADERS

# The comparable scores on both sides (human + agent). "na" is a first-class
# verdict now, so na↔na counts as agreement and na↔other as a disagreement.
_GRADES = ("pass", "borderline", "fail", "na")


def _empty_dist() -> Dict[str, int]:
    return {g: 0 for g in _GRADES}


def _cohen_kappa(human_dist: Dict[str, int], ai_dist: Dict[str, int],
                 agreements: int, n: int) -> Optional[float]:
    """Chance-corrected agreement over the comparable classes. None when undefined."""
    if not n:
        return None
    po = agreements / n
    pe = sum((human_dist[c] / n) * (ai_dist[c] / n) for c in _GRADES)
    if abs(1.0 - pe) < 1e-12:
        return None  # expected agreement is 1 (one class only) -> kappa undefined
    return round((po - pe) / (1.0 - pe), 3)


# Pseudo-variant: pool every real variant into one combined dataset.
COMBINED_VARIANT = "both"
COMBINED_LABEL = "Both variants"


def mode_report(mode_id: int, variant: str) -> Dict:
    """Build the agreement report for one pair-level mode + variant.

    Assumes `mode_id` has a VLM grader and `variant` is valid (validated by the
    caller). Pairs are matched by index within each (deck, variant). When
    `variant` is ``"both"``, every pair from all real variants is pooled into a
    single dataset (one confusion matrix, distributions, agreement, and κ).
    """
    mode = MODE_BY_ID[mode_id]
    mkey = str(mode_id)

    if variant == COMBINED_VARIANT:
        variants = list(config.VARIANT_KEYS)
        variant_label = COMBINED_LABEL
    else:
        variants = [variant]
        variant_label = config.VARIANT_BY_KEY[variant]["label"]

    human_dist = _empty_dist()
    ai_dist = _empty_dist()
    confusion = {h: _empty_dist() for h in _GRADES}  # confusion[human][ai]
    agreements = 0
    both = human_only = ai_only = no_data = considered = 0
    disagreements: List[Dict] = []

    for vkey in variants:
        for slug in storage.list_slugs():
            hv = storage.annotation_variant(slug, vkey)
            if not hv or not hv.get("available"):
                continue  # no human data for this variant -> no "both" possible
            ai_pairs = ai_grader.load_ai_grades(slug, vkey).get("pairs", {})
            title = storage.prettify(slug)

            for p in hv.get("pairs", []):
                idx = p.get("index")
                considered += 1
                h_cell = (p.get("modes") or {}).get(mkey) or {}
                h_grade = h_cell.get("grade", "ungraded")
                ai_cell = (ai_pairs.get(str(idx)) or {}).get(mkey) or {}
                ai_verdict = ai_cell.get("verdict")

                h_ok = h_grade in _GRADES
                ai_ok = ai_verdict in _GRADES
                if h_ok and ai_ok:
                    both += 1
                    human_dist[h_grade] += 1
                    ai_dist[ai_verdict] += 1
                    confusion[h_grade][ai_verdict] += 1
                    if h_grade == ai_verdict:
                        agreements += 1
                    else:
                        disagreements.append({
                            "slug": slug,
                            "title": title,
                            "variant": vkey,
                            "pair_index": idx,
                            "input_image": p.get("input_image"),
                            "output_image": p.get("output_image"),
                            "human_grade": h_grade,
                            "human_note": h_cell.get("note", ""),
                            "ai_verdict": ai_verdict,
                            "ai_reason": ai_cell.get("reason", ""),
                            "ai_graded_at": ai_cell.get("graded_at"),
                        })
                elif h_ok:
                    human_only += 1
                elif ai_ok:
                    ai_only += 1
                else:
                    no_data += 1

    n = both
    disagreements.sort(key=lambda d: (d["slug"], d["pair_index"] or 0, d["variant"]))
    return {
        "mode": {
            "id": mode_id,
            "name": mode["name"],
            "severity": mode.get("severity"),
            "element": mode.get("element"),
            "grader": MODE_GRADERS.get(mode_id),
        },
        "variant": variant,
        "variant_label": variant_label,
        "grades": list(_GRADES),
        "counts": {
            "both": n,
            "human_only": human_only,
            "ai_only": ai_only,
            "no_data": no_data,
            "considered": considered,
        },
        "human_distribution": human_dist,
        "ai_distribution": ai_dist,
        "agreements": agreements,
        "disagreements_count": n - agreements,
        "agreement_pct": round(100 * agreements / n, 1) if n else None,
        "cohen_kappa": _cohen_kappa(human_dist, ai_dist, agreements, n),
        "confusion": confusion,
        "disagreements": disagreements,
    }
