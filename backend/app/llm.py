"""Direct Anthropic vision client for running VLM grader rubrics in-process.

Replaces the gamma eval-server's ``/run-grader``: we read the two rendered slide
PNGs straight from the local render cache, base64-encode them, and call
Anthropic's Messages API with the rubric + both images. We return the model's
raw text under the same ``{rawResponse, error, latencyMs}`` shape the old
eval-server used, so the existing verdict parser is unchanged.
"""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

from . import config

# Mirrors the system message gamma's grader playground uses.
_SYSTEM = "You are an expert evaluator. Follow the grading rubric precisely."

# A neutral safety-net footer: it guarantees a parseable JSON shape without
# enumerating a verdict set (the rubric above defines the allowed verdicts, so
# we never contradict it).
_RESPONSE_FOOTER = (
    "\n\n---\n\n"
    "Respond with a JSON object of the form "
    '`{ "verdict": "...", "reason": "<brief explanation>" }` '
    "using one of the verdicts defined in the rubric above."
)

_MEDIA_TYPE = "image/png"


class LLMError(RuntimeError):
    """Transport/configuration error talking to the Anthropic API."""


def configured() -> bool:
    """True when an API key is present (used by the UI status check)."""
    return bool(config.ANTHROPIC_API_KEY)


def _image_block(path: Path) -> Dict:
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": _MEDIA_TYPE, "data": data},
    }


def _build_user_content(rubric: str, input_path: Path, output_path: Path) -> List[Dict]:
    """Rubric + a Data section with the two labeled images + a JSON footer."""
    return [
        {"type": "text", "text": rubric},
        {"type": "text", "text": "\n\n---\n\n## Data\n\n### input_slide\nThe original source slide:"},
        _image_block(input_path),
        {"type": "text", "text": "\n### output_slide\nThe Gamma-imported version of the same slide:"},
        _image_block(output_path),
        {"type": "text", "text": _RESPONSE_FOOTER},
    ]


def _text_from_response(payload: Dict) -> Optional[str]:
    """Concatenate the text blocks from an Anthropic Messages API response."""
    blocks = payload.get("content")
    if not isinstance(blocks, list):
        return None
    parts = [b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"]
    text = "".join(parts).strip()
    return text or None


def run_grader(
    rubric: str,
    model: str,
    input_path: Path,
    output_path: Path,
    *,
    temperature: float = 0.0,
    timeout: float = 180.0,
) -> Dict:
    """Grade one slide pair against a rubric. Returns
    ``{rawResponse, error, latencyMs}`` (matches the old eval-server contract)."""
    start = time.time()

    def _elapsed() -> int:
        return int((time.time() - start) * 1000)

    if not config.ANTHROPIC_API_KEY:
        return {"rawResponse": None, "error": "ANTHROPIC_API_KEY is not set in .env", "latencyMs": 0}
    for p, label in ((input_path, "input"), (output_path, "output")):
        if not p.exists():
            return {"rawResponse": None, "error": f"{label} image not found: {p}", "latencyMs": 0}

    body = json.dumps({
        "model": model,
        "max_tokens": config.AI_GRADER_MAX_TOKENS,
        "temperature": temperature,
        "system": _SYSTEM,
        "messages": [
            {"role": "user", "content": _build_user_content(rubric, input_path, output_path)},
        ],
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{config.ANTHROPIC_BASE_URL}/v1/messages",
        data=body,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": config.ANTHROPIC_API_KEY,
            "anthropic-version": config.ANTHROPIC_VERSION,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        return {"rawResponse": None, "error": f"anthropic {exc.code}: {detail}", "latencyMs": _elapsed()}
    except urllib.error.URLError as exc:
        return {"rawResponse": None, "error": f"anthropic unreachable: {exc.reason}", "latencyMs": _elapsed()}

    text = _text_from_response(payload)
    return {
        "rawResponse": text,
        "error": None if text else "empty response from model",
        "latencyMs": _elapsed(),
    }


def generate_text(
    prompt: str,
    model: str,
    *,
    system: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.2,
    timeout: float = 180.0,
) -> Dict:
    """Text-only completion (no images). Returns {text, error, latencyMs}."""
    start = time.time()

    def _elapsed() -> int:
        return int((time.time() - start) * 1000)

    if not config.ANTHROPIC_API_KEY:
        return {"text": None, "error": "ANTHROPIC_API_KEY is not set in .env", "latencyMs": 0}

    payload_obj: Dict = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
    }
    if system:
        payload_obj["system"] = system
    body = json.dumps(payload_obj).encode("utf-8")

    req = urllib.request.Request(
        f"{config.ANTHROPIC_BASE_URL}/v1/messages",
        data=body,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": config.ANTHROPIC_API_KEY,
            "anthropic-version": config.ANTHROPIC_VERSION,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        return {"text": None, "error": f"anthropic {exc.code}: {detail}", "latencyMs": _elapsed()}
    except urllib.error.URLError as exc:
        return {"text": None, "error": f"anthropic unreachable: {exc.reason}", "latencyMs": _elapsed()}

    text = _text_from_response(payload)
    return {"text": text, "error": None if text else "empty response from model", "latencyMs": _elapsed()}


def list_models(timeout: float = 30.0) -> Dict:
    """GET /v1/models — used during setup to confirm a valid model id."""
    if not config.ANTHROPIC_API_KEY:
        raise LLMError("ANTHROPIC_API_KEY is not set in .env")
    req = urllib.request.Request(
        f"{config.ANTHROPIC_BASE_URL}/v1/models",
        method="GET",
        headers={
            "x-api-key": config.ANTHROPIC_API_KEY,
            "anthropic-version": config.ANTHROPIC_VERSION,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise LLMError(f"anthropic {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"anthropic unreachable: {exc.reason}") from exc
