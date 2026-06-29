"""Author a VLM grader rubric from a failure-mode description.

Regeneration is LLM-written but constrained to the import-evals house-style
scaffold (Title / intro / input_slide + output_slide / Task / Verdicts /
Response format). The failure-mode description is the SOLE source of criteria +
verdict bands - the previous rubric is intentionally not used (fixed scaffold).
"""
from __future__ import annotations

from typing import Dict

from . import ai_grader, config, llm, storage
from . import modes as registry


class GraderAuthorError(RuntimeError):
    """Bad input or model failure while authoring a grader prompt."""


_SYSTEM = (
    "You are an expert at authoring VLM grader rubrics that evaluate how faithfully "
    "PowerPoint slides are imported into Gamma. You write precise, unambiguous rubrics "
    "a vision model can apply consistently."
)

_SCAFFOLD = """# <Failure mode name>

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether <one sentence stating exactly what this failure mode checks>.

You receive two images:

- `input_slide` - a screenshot of the original PPTX slide
- `output_slide` - a screenshot of the Gamma-imported version of the same slide

## Task

1. <what to identify in the source slide>
2. <what to check in the output slide>
3. Note any of these failure patterns:
   - <concrete failure patterns drawn from the description>

## Verdicts

- **pass** - <pass criteria from the description>
- **borderline** - <borderline criteria from the description>
- **fail** - <fail criteria from the description>
- **na** - <when the mode does not apply, from the description's N/A condition>

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail" | "na", "reason": "..." }
```"""


def _author_model() -> str:
    return config.AI_GRADER_MODEL or "claude-sonnet-4-6"


def _build_user_prompt(mode: Dict, description: str) -> str:
    triple = '"' * 3
    return (
        "Write a VLM grader rubric for the following slide-import failure mode.\n\n"
        "Failure mode:\n"
        f"- id: #{mode['id']}\n"
        f"- name: {mode['name']}\n"
        f"- element group: {mode['element']}\n"
        f"- dimension: {mode['dimension']}\n"
        f"- severity: {mode['severity']}\n\n"
        "Authoritative description of the failure mode and its grading bands. This is "
        "your ONLY source of grading criteria - do not invent criteria beyond it:\n"
        f"{triple}\n{description.strip()}\n{triple}\n\n"
        "Produce the rubric in Markdown, following this EXACT section structure and "
        "headings. Fill in every angle-bracket placeholder, keep the "
        "`input_slide`/`output_slide` naming, and keep the final JSON response-format "
        "block verbatim:\n\n"
        f"{_SCAFFOLD}\n\n"
        "Rules:\n"
        "- Output ONLY the rubric Markdown - no preamble, no commentary, and do NOT "
        "wrap the whole thing in a code fence.\n"
        "- The four verdict bullets (pass, borderline, fail, na) must reflect the "
        "description's bands exactly.\n"
        "- The `na` verdict must capture the description's N/A condition. If the "
        "description gives a tie-breaker for slides with multiple elements, fold it "
        "into the Task or Verdicts.\n"
        "- Be concise and concrete so a vision model applies it consistently."
    )


def _strip_outer_fence(text: str) -> str:
    """Drop a stray ``` fence wrapping the whole rubric. The rubric itself ends
    with a ```json block, so only strip when the FIRST line opens a fence."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if len(lines) >= 2 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
    return t


def generate_prompt(mode_id: int) -> Dict:
    """Generate a grader rubric from the mode's saved description.

    Works for both an existing grader (reinitialize in place) and a grader-less
    pair-level mode (mint a new grader name). The caller writes the prompt and,
    when ``created`` is True, attaches the grader to the mode in the registry.

    Returns {grader_name, model, prompt, description, latency_ms, created}. Raises
    GraderAuthorError on unknown mode / deck-level mode / missing description /
    model failure."""
    mode = registry.mode_by_id(mode_id)
    if not mode:
        raise GraderAuthorError(f"unknown mode #{mode_id}")
    grader_name = registry.grader_name(mode_id)
    created = False
    if not grader_name:
        if mode.get("level") != "pair":
            raise GraderAuthorError(
                "only pair-level modes can have a per-slide VLM grader "
                "(deck-level modes are graded once per deck, not per slide pair)"
            )
        grader_name = ai_grader.derive_grader_name(mode["name"], mode_id)
        created = True

    descs = storage.load_mode_descriptions().get("descriptions", {})
    description = ((descs.get(str(mode_id)) or {}).get("text") or "").strip()
    if not description:
        raise GraderAuthorError(
            "write a description for this mode first - it is the source the grader is generated from"
        )

    model = _author_model()
    res = llm.generate_text(_build_user_prompt(mode, description), model, system=_SYSTEM)
    if res.get("error") or not res.get("text"):
        raise GraderAuthorError(res.get("error") or "model returned an empty prompt")

    return {
        "grader_name": grader_name,
        "model": model,
        "prompt": _strip_outer_fence(res["text"]),
        "description": description,
        "latency_ms": res.get("latencyMs"),
        "created": created,
    }
