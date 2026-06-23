"""Run gamma's import-evals VLM graders against rendered slide pairs.

Flow: for a (deck, variant, pair) we read the matching grader's ``prompt.md`` +
``grader.yml`` from ``packages/import-evals/graders``, then POST the rubric, the
model, and the two rendered-PNG URLs to the local eval-server
(``yarn dev:eval-server``). The eval-server fetches the PNGs over localhost,
base64-encodes them, and runs the prompt against claude through gamma's model
gateway. We parse the ``pass | borderline | fail`` verdict + explanation from the
response and store it per (deck, variant, pair, mode) in the shared ``ai_grades/``
folder — in its own file so it never collides with the human autosave.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import config, storage
from .modes import MODE_BY_ID, MODE_GRADERS, PAIR_MODE_IDS


class AIGraderError(RuntimeError):
    """Configuration or transport error talking to the eval-server / graders dir."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------- grader defs
_grader_cache: Dict[str, Dict] = {}
_grader_cache_lock = threading.Lock()


def _graders_dir() -> Path:
    d = config.IMPORT_EVALS_GRADERS_DIR
    if not d:
        raise AIGraderError(
            "IMPORT_EVALS_GRADERS_DIR is not set — point .env at "
            "<your gamma checkout>/packages/import-evals/graders."
        )
    if not d.is_dir():
        raise AIGraderError(f"graders dir not found: {d}")
    return d


def _model_from_yaml(text: str) -> Optional[str]:
    """Minimal scan for a top-level ``model:`` key (avoids a YAML dependency)."""
    for line in text.splitlines():
        if line[:1] in (" ", "\t"):
            continue  # nested key
        stripped = line.strip()
        if stripped.lower().startswith("model:"):
            return stripped.split(":", 1)[1].strip().strip("'\"") or None
    return None


def load_grader(grader_name: str) -> Dict:
    """Load + cache a grader's prompt + model. Returns name/model/prompt/prompt_hash."""
    gdir = _graders_dir() / grader_name
    prompt_path = gdir / "prompt.md"
    yml_path = gdir / "grader.yml"
    if not prompt_path.exists() or not yml_path.exists():
        raise AIGraderError(f"grader '{grader_name}' is missing prompt.md/grader.yml in {gdir}")

    mtime = max(prompt_path.stat().st_mtime, yml_path.stat().st_mtime)
    with _grader_cache_lock:
        cached = _grader_cache.get(grader_name)
        if cached and cached["_mtime"] == mtime and not config.AI_GRADER_MODEL:
            return cached

    prompt = prompt_path.read_text(encoding="utf-8")
    model = (
        config.AI_GRADER_MODEL
        or _model_from_yaml(yml_path.read_text(encoding="utf-8"))
        or "claude-sonnet-4-6"
    )
    prompt_hash = hashlib.sha256(f"{model}\n{prompt}".encode("utf-8")).hexdigest()[:16]
    rec = {
        "name": grader_name,
        "model": model,
        "prompt": prompt,
        "prompt_hash": prompt_hash,
        "_mtime": mtime,
    }
    with _grader_cache_lock:
        _grader_cache[grader_name] = rec
    return rec


# --------------------------------------------------------------- eval-server
# The eval-server's /run-grader builds the prompt with hardcoded `input`/`output`
# image headers, so we send the two PNGs under those keys and add a short note
# mapping them onto the rubric's input_slide / output_slide naming.
_LABEL_NOTE = (
    "\n\n---\n\n"
    "Note on the two images in the Data section below: the image under **input** "
    "is `input_slide` (the original source slide); the image under **output** is "
    "`output_slide` (the imported version)."
)


def _post_run_grader(prompt: str, model: str, input_url: str, output_url: str,
                     timeout: float = 180.0) -> Dict:
    body = json.dumps({
        "prompt": prompt + _LABEL_NOTE,
        "model": model,
        "input": input_url,
        "output": output_url,
        "imageVariables": ["input", "output"],
        "temperature": 0,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{config.EVAL_SERVER_URL}/run-grader",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise AIGraderError(f"eval-server {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise AIGraderError(
            f"eval-server unreachable at {config.EVAL_SERVER_URL} "
            f"(is `yarn dev:eval-server` running?): {exc.reason}"
        ) from exc


# --------------------------------------------------------------- response parse
_VERDICTS = ("pass", "borderline", "fail", "skip")
_VERDICT_RE = re.compile(r'"verdict"\s*:\s*"(pass|borderline|fail|skip)"', re.IGNORECASE)
_REASON_RE = re.compile(r'"reason"\s*:\s*"((?:[^"\\]|\\.)*)"', re.IGNORECASE)


def _extract_json_obj(raw: str) -> Optional[dict]:
    start = raw.find("{")
    if start == -1:
        return None
    end = raw.rfind("}")
    while end > start:
        try:
            obj = json.loads(raw[start:end + 1])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        end = raw.rfind("}", start, end)
    return None


def parse_verdict(raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Pull (verdict, reason) out of the model's JSON response (fenced or inline)."""
    raw = raw or ""
    obj = _extract_json_obj(raw)
    if obj is not None:
        v = obj.get("verdict")
        verdict = v.lower() if isinstance(v, str) and v.lower() in _VERDICTS else None
        reason = obj.get("reason") if isinstance(obj.get("reason"), str) else None
        if verdict:
            return verdict, reason
    vm = _VERDICT_RE.search(raw)
    if vm:
        rm = _REASON_RE.search(raw)
        reason = None
        if rm:
            try:
                reason = json.loads('"' + rm.group(1) + '"')
            except json.JSONDecodeError:
                reason = rm.group(1)
        return vm.group(1).lower(), reason

    # Legacy line format: "VERDICT: PASS\nREASON: ..."
    lm = re.search(r"VERDICT:\s*(PASS|BORDERLINE|FAIL|SKIP)", raw, re.IGNORECASE)
    if lm:
        rl = re.search(r"REASON:\s*(.+)", raw, re.IGNORECASE)
        return lm.group(1).lower(), (rl.group(1).strip() if rl else None)
    return None, None


# --------------------------------------------------------------- storage (ai_grades/)
_store_locks: Dict[str, threading.RLock] = {}
_store_locks_guard = threading.Lock()


def _store_lock(key: str) -> threading.RLock:
    with _store_locks_guard:
        lock = _store_locks.get(key)
        if lock is None:
            lock = threading.RLock()
            _store_locks[key] = lock
        return lock


def _store_path(slug: str, variant: str) -> Path:
    return config.AI_GRADES_DIR / f"{slug}__{variant}.json"


def _empty_store(slug: str, variant: str) -> Dict:
    return {"deck_slug": slug, "variant": variant, "updated_at": _now(), "pairs": {}}


def load_ai_grades(slug: str, variant: str) -> Dict:
    path = _store_path(slug, variant)
    if not path.exists():
        return _empty_store(slug, variant)
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _empty_store(slug, variant)
    data.setdefault("pairs", {})
    return data


def _save_ai_grades(slug: str, variant: str, data: Dict) -> None:
    config.AI_GRADES_DIR.mkdir(parents=True, exist_ok=True)
    path = _store_path(slug, variant)
    fd, tmp = tempfile.mkstemp(dir=str(config.AI_GRADES_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def get_ai_grades(slug: str, variant: str) -> Dict:
    """Public read for the UI overlay (no eval-server contact)."""
    return load_ai_grades(slug, variant)


# --------------------------------------------------------------- grading
def _abs_image_url(rel_url: str) -> str:
    return f"{config.SELF_BASE_URL}{rel_url}"


def _find_pair(detail: Dict, index: int) -> Optional[Dict]:
    for p in detail.get("pairs", []):
        if p.get("index") == index:
            return p
    return None


def gradeable_pair_modes(modes: Optional[List[int]] = None) -> List[int]:
    """Pair-level mode ids that have a grader, optionally filtered to `modes`."""
    ids = [m for m in PAIR_MODE_IDS if m in MODE_GRADERS]
    if modes is not None:
        wanted = set(modes)
        ids = [m for m in ids if m in wanted]
    return ids


def grade_pair_mode(
    slug: str,
    variant: str,
    index: int,
    mode_id: int,
    *,
    force: bool = False,
    input_url: Optional[str] = None,
    output_url: Optional[str] = None,
    persist: bool = True,
) -> Dict:
    """Grade a single (pair, mode). Skips the model call if a fresh cached result
    exists (same prompt_hash) unless `force`. Returns the stored cell."""
    grader_name = MODE_GRADERS.get(mode_id)
    if not grader_name:
        raise AIGraderError(f"mode #{mode_id} has no VLM grader")

    grader = load_grader(grader_name)
    key = f"{slug}__{variant}"

    with _store_lock(key):
        store = load_ai_grades(slug, variant)
        pair_cells = store["pairs"].setdefault(str(index), {})
        existing = pair_cells.get(str(mode_id))
        if (
            not force
            and existing
            and existing.get("prompt_hash") == grader["prompt_hash"]
            and existing.get("verdict") in ("pass", "borderline", "fail")
        ):
            return existing

    # Resolve the two image URLs if the caller didn't pre-supply them.
    if input_url is None or output_url is None:
        detail = storage.get_deck_detail(slug, variant)
        pair = _find_pair(detail, index)
        if pair is None:
            raise AIGraderError(f"pair {index} not found in {slug}/{variant}")
        input_url = _abs_image_url(pair["input_image"])
        output_url = _abs_image_url(pair["output_image"])

    result = _post_run_grader(grader["prompt"], grader["model"], input_url, output_url)
    raw = result.get("rawResponse")
    server_error = result.get("error")
    verdict, reason = parse_verdict(raw)

    cell: Dict = {
        "verdict": verdict or "error",
        "reason": reason or (server_error or "Could not parse a verdict from the model response."),
        "grader": grader_name,
        "model": grader["model"],
        "prompt_hash": grader["prompt_hash"],
        "graded_at": _now(),
        "latency_ms": result.get("latencyMs"),
    }
    if server_error:
        cell["error"] = server_error
    if verdict is None:
        # keep the raw text only when parsing failed, to aid debugging
        cell["raw"] = (raw or "")[:1000]

    if persist:
        with _store_lock(key):
            store = load_ai_grades(slug, variant)
            store["pairs"].setdefault(str(index), {})[str(mode_id)] = cell
            store["updated_at"] = _now()
            _save_ai_grades(slug, variant, store)
    return cell


def grade_pair(
    slug: str,
    variant: str,
    index: int,
    *,
    modes: Optional[List[int]] = None,
    force: bool = False,
) -> Dict:
    """Grade the mapped modes for one pair, in parallel (AI_GRADER_CONCURRENCY).

    Resolves the two image URLs once, then fans out one model call per mode.
    """
    detail = storage.get_deck_detail(slug, variant)
    pair = _find_pair(detail, index)
    if pair is None:
        raise AIGraderError(f"pair {index} not found in {slug}/{variant}")
    input_url = _abs_image_url(pair["input_image"])
    output_url = _abs_image_url(pair["output_image"])

    mode_ids = gradeable_pair_modes(modes)
    results: Dict[str, Dict] = {}
    if not mode_ids:
        return {"slug": slug, "variant": variant, "index": index, "modes": results}

    def _task(mode_id: int) -> Tuple[int, Dict]:
        return mode_id, grade_pair_mode(
            slug, variant, index, mode_id,
            force=force, input_url=input_url, output_url=output_url,
        )

    workers = max(1, min(config.AI_GRADER_CONCURRENCY, len(mode_ids)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for mode_id, cell in pool.map(_task, mode_ids):
            results[str(mode_id)] = cell
    return {"slug": slug, "variant": variant, "index": index, "modes": results}


# --------------------------------------------------------------- status
def status() -> Dict:
    """Config/health for the UI: graders dir present + eval-server reachable."""
    graders_dir = config.IMPORT_EVALS_GRADERS_DIR
    dir_ok = bool(graders_dir and graders_dir.is_dir())
    missing: List[str] = []
    if dir_ok:
        for gname in MODE_GRADERS.values():
            if not (graders_dir / gname / "prompt.md").exists():
                missing.append(gname)

    server_ok = False
    server_error: Optional[str] = None
    try:
        req = urllib.request.Request(f"{config.EVAL_SERVER_URL}/graders", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            server_ok = 200 <= resp.status < 300
    except Exception as exc:  # noqa: BLE001 - report any reachability failure
        server_error = str(exc)

    return {
        "eval_server_url": config.EVAL_SERVER_URL,
        "eval_server_reachable": server_ok,
        "eval_server_error": server_error,
        "self_base_url": config.SELF_BASE_URL,
        "graders_dir": str(graders_dir) if graders_dir else None,
        "graders_dir_ok": dir_ok,
        "graders_expected": len(MODE_GRADERS),
        "graders_present": len(MODE_GRADERS) - len(missing) if dir_ok else 0,
        "graders_missing": missing,
    }


# --------------------------------------------------------------- coverage
def store_counts(slug: str, variant: str) -> Dict:
    """Cheap read of how many AI cells are stored for (deck, variant)."""
    store = load_ai_grades(slug, variant)
    graded = errors = 0
    for cells in store.get("pairs", {}).values():
        for cell in cells.values():
            v = cell.get("verdict")
            if v in ("pass", "borderline", "fail"):
                graded += 1
            elif v == "error":
                errors += 1
    return {"graded": graded, "errors": errors}


# --------------------------------------------------------------- bulk jobs
# In-memory only: a single background run at a time, polled by the dashboard.
# Each pair is graded by grade_pair (which fans out its modes at
# AI_GRADER_CONCURRENCY), and pairs are walked sequentially so total in-flight
# model calls stay bounded by AI_GRADER_CONCURRENCY.
_jobs: Dict[str, Dict] = {}
_jobs_lock = threading.Lock()
_active_job_id: Optional[str] = None
_ABORT_AFTER_CONSECUTIVE_FAILURES = 3


def _public_job(job: Optional[Dict]) -> Optional[Dict]:
    if not job:
        return None
    return {k: v for k, v in job.items() if not k.startswith("_")}


def get_job(job_id: str) -> Optional[Dict]:
    with _jobs_lock:
        return _public_job(_jobs.get(job_id))


def list_jobs() -> Dict:
    with _jobs_lock:
        jobs = [_public_job(j) for j in _jobs.values()]
        active = _public_job(_jobs.get(_active_job_id)) if _active_job_id else None
    jobs.sort(key=lambda j: j["started_at"], reverse=True)
    return {"jobs": jobs[:20], "active": active}


def cancel_job(job_id: str) -> Optional[Dict]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        if job["status"] == "running":
            job["_cancel"].set()
            job["status"] = "cancelling"
        return _public_job(job)


def _enumerate_units(scope: str, variant: str, slug: Optional[str]) -> List[Tuple[str, int]]:
    """[(slug, pair_index), ...] for the run scope, from lightweight summaries."""
    if scope == "deck":
        if not slug:
            raise ValueError("scope 'deck' requires a slug")
        slugs = [slug]
    elif scope == "all":
        slugs = storage.list_slugs()
    else:
        raise ValueError(f"unknown scope '{scope}'")

    units: List[Tuple[str, int]] = []
    for s in slugs:
        summ = storage.deck_summary(s)["variants"].get(variant, {})
        if not summ.get("available"):
            continue
        for idx in range(1, int(summ.get("pair_count", 0)) + 1):
            units.append((s, idx))
    return units


def start_run(scope: str, variant: str, *, slug: Optional[str] = None, force: bool = False) -> Dict:
    """Start a background bulk run. If one is already active, returns it unchanged."""
    if variant not in config.VARIANT_BY_KEY:
        raise ValueError(f"unknown variant '{variant}'")
    st = status()
    if not st["eval_server_reachable"]:
        raise AIGraderError(st.get("eval_server_error") or f"eval-server unreachable at {config.EVAL_SERVER_URL}")
    if not st["graders_dir_ok"]:
        raise AIGraderError("graders dir not found — set IMPORT_EVALS_GRADERS_DIR in .env")

    units = _enumerate_units(scope, variant, slug)

    global _active_job_id
    with _jobs_lock:
        active = _jobs.get(_active_job_id) if _active_job_id else None
        if active and active["status"] in ("running", "cancelling"):
            return _public_job(active)
        job_id = uuid.uuid4().hex[:12]
        job = {
            "id": job_id,
            "scope": scope,
            "variant": variant,
            "slug": slug,
            "status": "running",
            "total": len(units),
            "done": 0,
            "cells": 0,
            "errors": 0,
            "current": None,
            "current_slug": None,
            "started_at": _now(),
            "finished_at": None,
            "error": None,
            "force": bool(force),
            "_cancel": threading.Event(),
            "_units": units,
        }
        _jobs[job_id] = job
        _active_job_id = job_id

    threading.Thread(target=_run_job, args=(job_id,), daemon=True).start()
    return _public_job(job)


def _run_job(job_id: str) -> None:
    global _active_job_id
    job = _jobs[job_id]
    units = job["_units"]
    cancel = job["_cancel"]
    variant = job["variant"]
    force = job["force"]
    consecutive = 0
    try:
        for slug, idx in units:
            if cancel.is_set():
                break
            with _jobs_lock:
                job["current"] = f"{slug} \u00b7 pair {idx}"
                job["current_slug"] = slug
            try:
                res = grade_pair(slug, variant, idx, force=force)
                cells = res.get("modes", {})
                errs = sum(1 for c in cells.values() if c.get("verdict") == "error")
                with _jobs_lock:
                    job["cells"] += len(cells)
                    job["errors"] += errs
                consecutive = 0
            except AIGraderError as exc:
                consecutive += 1
                with _jobs_lock:
                    job["errors"] += 1
                    job["error"] = str(exc)
                if consecutive >= _ABORT_AFTER_CONSECUTIVE_FAILURES:
                    with _jobs_lock:
                        job["status"] = "error"
                    break
            finally:
                with _jobs_lock:
                    job["done"] += 1
        with _jobs_lock:
            if cancel.is_set():
                job["status"] = "cancelled"
            elif job["status"] == "running":
                job["status"] = "done"
    except Exception as exc:  # noqa: BLE001 - never let the worker die silently
        with _jobs_lock:
            job["status"] = "error"
            job["error"] = str(exc)
    finally:
        with _jobs_lock:
            job["current"] = None
            job["current_slug"] = None
            job["finished_at"] = _now()
            if _active_job_id == job_id:
                _active_job_id = None
