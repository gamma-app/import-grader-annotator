"""Ingest a PPTX and produce a gradable ``current`` slide-pair via gamma.app.

Pipeline (one uploaded ``.pptx`` -> a deck folder the grader can show):
  1. **PPTX -> input.pdf** with headless LibreOffice (``soffice --convert-to pdf``).
  2. **gamma "current import" -> current_output.pdf** by driving gamma.app in a
     headless browser (Playwright) with a saved login session, mirroring the
     manual flow: dashboard "Import" button -> "AI import" -> upload the PPTX into
     the hidden file input -> pick the faithful "Visual import" mode (gamma
     defaults to an AI "Transform content" redesign!) -> Continue -> wait for the
     generated deck to open in the editor -> export it to PDF.
  3. **Place + render**: write ``input.pdf`` + ``current_output.pdf`` (and the
     source ``input.pptx``) into ``<DATA_DIR>/decks/<slug>/`` and run the existing
     ``storage.ensure_rendered`` + ``sync_annotation`` so the pair appears.

All heavy work happens in a local scratch dir; the deck folder is only populated
once both PDFs exist, so a failed import never leaves a half-built deck.

Runs in a background thread, mirroring ``ai_grader``'s single-active-job model.
Playwright's SYNC api is used inside that worker thread (safe: a plain thread has
no asyncio loop). Auth is a Playwright ``storageState`` captured once via
``python -m app.gamma_login``; see GAMMA_* in ``config.py``.

The gamma.app UI selectors live in clearly-marked, env-overridable constants
below. They are a best effort from gamma's client code and almost certainly need
one calibration pass against a live account — on any failure we dump a
screenshot + DOM so the exact step can be fixed quickly.
"""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import config, storage

LogFn = Callable[[str], None]


class ImporterError(RuntimeError):
    """Configuration, conversion, or browser-automation failure."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------- gamma UI flow
# These describe the gamma.app import/export click-path. They are intentionally
# fuzzy (case-insensitive name regexes) and overridable via env so the flow can
# be calibrated without code changes. Comma-separated for the *_LABELS lists.
def _csv_env(name: str, default: List[str]) -> List[str]:
    raw = os.environ.get(name)
    if not raw:
        return default
    return [s.strip() for s in raw.split(",") if s.strip()]


# The flow mirrors the manual one exactly:
#   dashboard "Import" button -> "AI import" menu item (navigates to
#   /create/import) -> upload the .pptx -> pick "Visual import" -> Continue.
# The dashboard Import control is a Chakra menu button with a stable test id.
IMPORT_BUTTON_TESTID = os.environ.get("GAMMA_IMPORT_BUTTON_TESTID") or "import-doc-button"
# Fallback accessible name for that button if the test id ever changes.
IMPORT_BUTTON_LABEL = os.environ.get("GAMMA_IMPORT_BUTTON_LABEL") or "Import"
# Dropdown item that opens the AI import surface (sparkles icon + "AI" badge).
AI_IMPORT_LABEL = os.environ.get("GAMMA_AI_IMPORT_LABEL") or "AI import"
# URL substring the "AI import" item navigates to; it hosts the upload <input>.
IMPORT_PATH = os.environ.get("GAMMA_IMPORT_PATH") or "/create/import"
# Accessible name of the *faithful* import mode on the post-upload screen. Gamma
# defaults the selector to "Transform content" (an AI redesign that does NOT
# preserve the slides); "Visual import" is the mode that reproduces the manual
# "current import". Selecting it is therefore REQUIRED for a correct pair. Set
# this env var to empty to skip mode selection and accept gamma's default.
IMPORT_MODE_LABEL = os.environ.get("GAMMA_IMPORT_MODE_LABEL", "Visual import")
# Accessible name of the "Continue" button. The import flow has THREE Continue
# steps, all sharing this label: (1) the upload screen (after the mode pick),
# (2) the "Pick a theme" step, then (3) the slide-preview step whose Continue
# actually starts generation. We disambiguate them by waiting for each step's
# text (THEME_STEP_HINT / PREVIEW_STEP_HINT) before clicking.
CONTINUE_LABEL = os.environ.get("GAMMA_IMPORT_CONTINUE_LABEL") or "Continue"
# Text shown on the second ("Pick a theme") step. We wait for it before clicking
# the second Continue, so we don't accidentally re-click the first. Non-fatal.
THEME_STEP_HINT = os.environ.get("GAMMA_THEME_STEP_HINT", "Pick a theme")
# Text shown on the third (slide-preview) step -- gamma renders "<n> cards total"
# next to its Continue button. We wait for it (and for that Continue to enable,
# since it's disabled while gamma imports the slides) before clicking the third
# Continue, which calls generate() and kicks off the deck generation. Non-fatal.
PREVIEW_STEP_HINT = os.environ.get("GAMMA_PREVIEW_STEP_HINT", "cards total")
# Accessible-name regexes clicked to open the share/export surface in the editor.
EXPORT_OPEN_LABELS = _csv_env("GAMMA_EXPORT_OPEN_LABELS", ["Share", "Export"])
# Accessible-name of the PDF export button inside the export panel.
EXPORT_PDF_LABEL = os.environ.get("GAMMA_EXPORT_PDF_LABEL") or "PDF"
# URL (regex) that marks "the finished deck is open in the editor". The import
# first lands on /create/import-ppt/<genId> (generation in progress); the
# finished deck editor is /docs/<docId>, so match that specifically.
DOC_URL_REGEX = os.environ.get("GAMMA_DOC_URL_REGEX") or r"/docs/[A-Za-z0-9]"


# --------------------------------------------------------------- readiness
def playwright_installed() -> bool:
    return importlib.util.find_spec("playwright") is not None


def find_soffice() -> Optional[str]:
    """Locate the LibreOffice binary used for PPTX->PDF, or None."""
    if config.SOFFICE_BIN:
        return config.SOFFICE_BIN if Path(config.SOFFICE_BIN).exists() else None
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    mac = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    return str(mac) if mac.exists() else None


def auth_state_present() -> bool:
    return config.GAMMA_AUTH_STATE_PATH.exists()


def status() -> Dict:
    """Config/health for the UI: can we run an import right now?"""
    pw = playwright_installed()
    soffice = find_soffice()
    auth = auth_state_present()
    ready = bool(pw and soffice and auth)
    missing: List[str] = []
    if not pw:
        missing.append("playwright not installed (pip install -r requirements.txt)")
    if not soffice:
        missing.append("LibreOffice 'soffice' not found (install LibreOffice or set SOFFICE_BIN)")
    if not auth:
        missing.append("no gamma session (run: python -m app.gamma_login)")
    return {
        "ready": ready,
        "playwright_installed": pw,
        "soffice_available": bool(soffice),
        "soffice_path": soffice,
        "auth_state_present": auth,
        "gamma_base_url": config.GAMMA_BASE_URL,
        "headless": config.GAMMA_IMPORT_HEADLESS,
        "missing": missing,
    }


# --------------------------------------------------------------- helpers
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Filesystem-safe deck slug from a filename/title (e.g. 'Q3 Sales!' -> 'q3-sales')."""
    base = Path(name).stem if name else ""
    slug = _SLUG_RE.sub("-", base.strip().lower()).strip("-")
    return slug or f"deck-{uuid.uuid4().hex[:8]}"


def convert_pptx_to_pdf(pptx_path: Path, out_pdf: Path, log: LogFn) -> None:
    """Render a PPTX to PDF with headless LibreOffice. Writes exactly ``out_pdf``."""
    soffice = find_soffice()
    if not soffice:
        raise ImporterError("LibreOffice 'soffice' not found for PPTX->PDF conversion")
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    # Per-call user profile avoids clashing with a running LibreOffice instance.
    with tempfile.TemporaryDirectory() as profile:
        profile_uri = Path(profile).as_uri()
        cmd = [
            soffice,
            "--headless",
            "--norestore",
            f"-env:UserInstallation={profile_uri}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_pdf.parent),
            str(pptx_path),
        ]
        log(f"convert: {' '.join(cmd)}")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        except subprocess.TimeoutExpired as exc:
            raise ImporterError("PPTX->PDF conversion timed out after 240s") from exc
    if proc.returncode != 0:
        raise ImporterError(f"soffice failed (exit {proc.returncode}): {proc.stderr.strip()[:500]}")
    produced = out_pdf.parent / f"{pptx_path.stem}.pdf"
    if not produced.exists():
        raise ImporterError(f"soffice did not produce a PDF (expected {produced.name})")
    if produced != out_pdf:
        produced.replace(out_pdf)
    log(f"convert: wrote {out_pdf.name} ({out_pdf.stat().st_size} bytes)")


# --------------------------------------------------------------- browser flow
def _save_debug(page, debug_dir: Path, name: str, log: LogFn) -> None:
    try:
        debug_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(debug_dir / f"{name}.png"), full_page=True)
        (debug_dir / f"{name}.html").write_text(page.content(), encoding="utf-8")
        log(f"debug: saved {name}.png + {name}.html to {debug_dir}")
    except Exception as exc:  # noqa: BLE001 - debugging must never mask the real error
        log(f"debug: failed to capture artifacts: {exc}")


def _try_click_labels(page, labels: List[str], log: LogFn) -> None:
    """Best-effort: click each accessible-name regex if visible (missing = skip)."""
    for label in labels:
        try:
            loc = page.get_by_role("button", name=re.compile(label, re.I)).first
            if loc.count() and loc.is_visible():
                loc.click()
                log(f"clicked: {label!r}")
                page.wait_for_timeout(600)
        except Exception:  # noqa: BLE001 - optional step; continue the path
            continue


def _click_label(page, label: str, log: LogFn, timeout: int) -> bool:
    """Click the first VISIBLE, clickable control matching ``label``.

    Tries EXACT-name matches first (button/tab/text) so e.g. "Export" doesn't
    match gamma's "Export 0 cards"/"Export..." decoys, then falls back to loose
    case-insensitive regex matches (button/menuitem/tab/text). Crucially it
    iterates over ALL matches of each strategy and clicks the first one that is
    visible AND actionable -- gamma frequently renders hidden or
    pointer-events:none duplicates, so only ever trying ``.first`` (as before)
    could get permanently stuck on a decoy. Uses a short per-click timeout so a
    non-actionable match is skipped quickly; the outer loop re-polls until
    ``timeout`` so controls that are briefly disabled still get clicked once
    they settle. Returns True iff something was clicked.
    """
    rx = re.compile(label, re.I)
    strategies = (
        lambda: page.get_by_role("button", name=label, exact=True),
        lambda: page.get_by_role("tab", name=label, exact=True),
        lambda: page.get_by_text(label, exact=True),
        lambda: page.get_by_role("button", name=rx),
        lambda: page.get_by_role("menuitem", name=rx),
        lambda: page.get_by_role("tab", name=rx),
        lambda: page.get_by_text(rx),
    )
    deadline = time.time() + timeout / 1000.0
    while True:
        for getter in strategies:
            try:
                loc = getter()
                count = min(loc.count(), 10)  # cap pathological match counts
            except Exception:  # noqa: BLE001 - bad/transient locator; try next strategy
                continue
            for i in range(count):
                try:
                    item = loc.nth(i)
                    if item.is_visible():
                        item.click(timeout=3000)
                        log(f"clicked: {label!r}")
                        return True
                except Exception:  # noqa: BLE001 - not actionable (hidden/covered); try next
                    continue
        if time.time() >= deadline:
            return False
        page.wait_for_timeout(250)


def _gamma_import_to_pdf(pptx_path: Path, out_pdf: Path, debug_dir: Path, log: LogFn) -> str:
    """Drive gamma.app: upload the PPTX, wait for the deck, export to PDF.

    Returns the imported deck URL. Raises ImporterError (with debug artifacts) on
    any step failure. Selectors are best-effort and may need calibration.
    """
    from playwright.sync_api import TimeoutError as PWTimeout  # noqa: PLC0415
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    auth = config.GAMMA_AUTH_STATE_PATH
    if not auth.exists():
        raise ImporterError(f"no gamma session at {auth} — run: python -m app.gamma_login")

    action_ms = config.GAMMA_ACTION_TIMEOUT_MS
    overall_ms = config.GAMMA_IMPORT_TIMEOUT_MS

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=config.GAMMA_IMPORT_HEADLESS,
            # Look like a real browser (no navigator.webdriver) so gamma/Cloudflare
            # don't treat us as automation now that we use a normal User-Agent.
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            storage_state=str(auth),
            user_agent=config.GAMMA_USER_AGENT,
            # A real desktop viewport so gamma renders the full dashboard toolbar
            # (Import button etc.) rather than a compact/mobile layout.
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True,
            accept_downloads=True,
        )
        context.set_default_timeout(action_ms)
        page = context.new_page()
        try:
            # Start on the dashboard, exactly like the manual flow.
            log(f"goto {config.GAMMA_BASE_URL}")
            page.goto(config.GAMMA_BASE_URL, wait_until="domcontentloaded", timeout=action_ms * 3)

            # Session sanity check: a login/redirect means the saved session expired.
            if re.search(r"/signin|/login|/auth", page.url, re.I):
                _save_debug(page, debug_dir, "01-not-logged-in", log)
                raise ImporterError(
                    "gamma session looks expired/invalid (landed on a sign-in page). "
                    "Re-capture it with: python -m app.gamma_login"
                )

            # --- Dashboard "Import" button -> "AI import" -----------------------
            # Mirror the manual flow: open the "Import" menu (stable test id) and
            # click its "AI import" item, which navigates to /create/import?ref=home.
            # The Chakra menu can need a moment to open, so retry the toggle; if the
            # menu interaction still races, navigate to that exact URL directly
            # (functionally identical to clicking "AI import").
            ai_import_url = f"{config.GAMMA_BASE_URL}{IMPORT_PATH}?ref=home"
            reached = False
            try:
                btn = page.get_by_test_id(IMPORT_BUTTON_TESTID).first
                if not (btn.count() and btn.is_visible()):
                    raise ImporterError("import-doc-button not visible")
                for attempt in range(3):
                    btn.click()
                    log(f"clicked Import button (test id {IMPORT_BUTTON_TESTID!r}, attempt {attempt + 1})")
                    if _click_label(page, AI_IMPORT_LABEL, log, timeout=5000):
                        reached = True
                        break
            except Exception as exc:  # noqa: BLE001 - fall back to direct navigation
                log(f"Import menu interaction failed ({exc}); using direct navigation")

            if not reached:
                log(f"navigating directly to the AI import page -> {ai_import_url}")
                page.goto(ai_import_url, wait_until="domcontentloaded", timeout=action_ms * 3)

            # Confirm we landed on the import page (the "AI import" destination).
            try:
                page.wait_for_url(re.compile(re.escape(IMPORT_PATH)), timeout=action_ms * 2)
            except PWTimeout:
                log(f"note: URL didn't match {IMPORT_PATH!r}; looking for the upload input anyway")
            log(f"on AI import page: {page.url}")

            # --- Upload the PPTX via the (hidden) file input ---------------------
            # set_input_files works on hidden inputs, so no need to click "Browse".
            try:
                file_input = page.locator('input[type="file"]').first
                file_input.wait_for(state="attached", timeout=action_ms)
                file_input.set_input_files(str(pptx_path))
                log(f"uploaded {pptx_path.name}; waiting for gamma to parse it...")
            except PWTimeout as exc:
                _save_debug(page, debug_dir, "02-no-file-input", log)
                raise ImporterError(
                    "reached the AI import page but found no file <input>. Calibrate "
                    "GAMMA_AI_IMPORT_LABEL / GAMMA_IMPORT_PATH (see the saved screenshot)."
                ) from exc

            # --- Pick the faithful import mode, then start generation ------------
            # The post-upload screen (file summary + mode selector + Continue)
            # appears once parsing finishes; allow plenty of time for big decks.
            try:
                continue_btn = page.get_by_role(
                    "button", name=re.compile(CONTINUE_LABEL, re.I)
                ).first
                continue_btn.wait_for(state="visible", timeout=overall_ms)
            except PWTimeout as exc:
                _save_debug(page, debug_dir, "03-no-continue", log)
                raise ImporterError(
                    "PPTX uploaded but the import screen never appeared. Calibrate "
                    "GAMMA_IMPORT_CONTINUE_LABEL or raise GAMMA_IMPORT_TIMEOUT_MS."
                ) from exc

            # Gamma defaults to "Transform content" (AI redesign). Selecting
            # "Visual import" is what reproduces the faithful current-import.
            if IMPORT_MODE_LABEL:
                if not _click_label(page, IMPORT_MODE_LABEL, log, timeout=action_ms):
                    _save_debug(page, debug_dir, "03b-no-import-mode", log)
                    raise ImporterError(
                        f"could not select the {IMPORT_MODE_LABEL!r} import mode. Gamma "
                        "defaults to AI 'Transform content', which is NOT a faithful "
                        "import. Calibrate GAMMA_IMPORT_MODE_LABEL, or set it empty to "
                        "accept gamma's default mode."
                    )
                page.wait_for_timeout(400)  # let the selection settle

            continue_btn.click()
            log("clicked Continue (1/3: import settings); waiting for the theme step...")

            # --- Theme step -> second "Continue" ---------------------------------
            # The first Continue navigates to /create/import-ppt/<id> and shows a
            # "Pick a theme" step (a default theme is preselected) with ITS OWN
            # Continue button. Wait for that step before clicking, so we advance it
            # rather than re-clicking the first Continue.
            try:
                page.get_by_text(re.compile(THEME_STEP_HINT, re.I)).first.wait_for(
                    state="visible", timeout=overall_ms
                )
                log(f"theme step visible ({THEME_STEP_HINT!r})")
            except PWTimeout:
                log(f"note: didn't see {THEME_STEP_HINT!r}; trying the theme Continue anyway")

            if not _click_label(page, CONTINUE_LABEL, log, timeout=overall_ms):
                _save_debug(page, debug_dir, "03c-no-theme-continue", log)
                raise ImporterError(
                    "stuck on gamma's theme step: its 'Continue' button never became "
                    "clickable. Calibrate GAMMA_IMPORT_CONTINUE_LABEL / GAMMA_THEME_STEP_HINT, "
                    "or raise GAMMA_IMPORT_TIMEOUT_MS."
                )
            log("clicked Continue (2/3: theme step); waiting for the slide preview...")

            # --- Slide-preview step -> third "Continue" (this starts generation) -
            # The theme Continue swaps the SAME /create/import-ppt page to a slide
            # preview ("<n> cards total" + a Continue that calls generate()). That
            # Continue is disabled while gamma imports the slides, so: wait for the
            # preview to render, then wait (with progress logs) for the button to
            # enable -- otherwise a slow slide import just looks hung here.
            try:
                page.get_by_text(re.compile(PREVIEW_STEP_HINT, re.I)).first.wait_for(
                    state="visible", timeout=overall_ms
                )
                log(f"slide preview visible ({PREVIEW_STEP_HINT!r})")
            except PWTimeout:
                log(f"note: didn't see {PREVIEW_STEP_HINT!r}; trying the preview Continue anyway")

            preview_continue = page.get_by_role(
                "button", name=re.compile(CONTINUE_LABEL, re.I)
            ).last
            deadline = time.time() + overall_ms / 1000.0
            poll = 0
            while time.time() < deadline:
                try:
                    if preview_continue.count() and preview_continue.is_enabled():
                        break
                except Exception:  # noqa: BLE001 - keep polling until enabled/deadline
                    pass
                poll += 1
                if poll % 6 == 0:  # ~every 30s
                    log("still importing slides... (preview Continue not yet enabled)")
                page.wait_for_timeout(5000)

            if not _click_label(page, CONTINUE_LABEL, log, timeout=action_ms):
                _save_debug(page, debug_dir, "03d-no-preview-continue", log)
                raise ImporterError(
                    "stuck on gamma's slide-preview step: its 'Continue' button never "
                    "became clickable. Gamma may still be importing slides -- raise "
                    "GAMMA_IMPORT_TIMEOUT_MS, or calibrate GAMMA_IMPORT_CONTINUE_LABEL / "
                    "GAMMA_PREVIEW_STEP_HINT."
                )
            log("clicked Continue (3/3: slide preview); gamma is generating (can take minutes)...")

            # --- Wait for the finished deck to open in the editor ----------------
            # Generation (gamma's generateDoc) can take several minutes for a big
            # deck; when it resolves, gamma navigates to /docs/<id>. Poll the URL
            # (logging progress) instead of one opaque wait, so slow generations
            # are visible rather than looking hung.
            deadline = time.time() + overall_ms / 1000.0
            doc_url = None
            poll = 0
            while time.time() < deadline:
                if re.search(DOC_URL_REGEX, page.url):
                    doc_url = page.url
                    break
                poll += 1
                if poll % 4 == 0:  # ~every 20s
                    log(f"still generating... (at {page.url})")
                page.wait_for_timeout(5000)
            if not doc_url:
                _save_debug(page, debug_dir, "04-generation-timeout", log)
                raise ImporterError(
                    "timed out waiting for the generated deck to open in the editor. "
                    "Calibrate GAMMA_DOC_URL_REGEX or raise GAMMA_IMPORT_TIMEOUT_MS."
                )
            log(f"generated deck: {doc_url}")
            # Let the editor settle. Gamma keeps live connections open, so DON'T
            # require networkidle (it may never fire); a short load wait suffices.
            try:
                page.wait_for_load_state("load", timeout=action_ms)
            except PWTimeout:
                pass
            page.wait_for_timeout(2000)

            # --- Export the deck to PDF ------------------------------------------
            # Open the share modal, switch to its "Export" sub-view, then click
            # "Export to PDF". On success gamma POSTs to /export/docs/<id>/pdf and
            # programmatically clicks an <a download> -- which Playwright captures
            # as a download event. IMPORTANT: the "Export" sidebar item is an
            # icon+text tab, NOT a <button>, so we click it with _click_label
            # (which falls back to matching text) rather than _try_click_labels
            # (button-only) -- the latter silently skipped it and left us stuck on
            # the "Share" view with no PDF button.
            for label in EXPORT_OPEN_LABELS:
                if not _click_label(page, label, log, timeout=action_ms):
                    safe = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
                    _save_debug(page, debug_dir, f"05a-no-{safe}", log)
                    raise ImporterError(
                        f"could not open the export panel: {label!r} was not "
                        "clickable. Calibrate GAMMA_EXPORT_OPEN_LABELS."
                    )
                page.wait_for_timeout(500)  # let the modal / sub-view render

            # Wait for the PDF button so a missing Export sub-view fails clearly
            # here instead of as an opaque download timeout later.
            pdf_btn = page.get_by_role("button", name=re.compile(EXPORT_PDF_LABEL, re.I)).first
            try:
                pdf_btn.wait_for(state="visible", timeout=action_ms)
            except PWTimeout as exc:
                _save_debug(page, debug_dir, "05b-no-pdf-button", log)
                raise ImporterError(
                    "opened the share modal but never found the PDF export button. "
                    "Calibrate GAMMA_EXPORT_OPEN_LABELS / GAMMA_EXPORT_PDF_LABEL."
                ) from exc

            # Gamma aborts the export request server-side at 60s (EXPORT_MAX_DELAY),
            # so cap the download wait near that rather than the full import budget.
            export_dl_ms = max(action_ms, 90_000)
            try:
                with page.expect_download(timeout=export_dl_ms) as dl_info:
                    pdf_btn.click()
                    log("clicked 'Export to PDF'; waiting for the download...")
                download = dl_info.value
                out_pdf.parent.mkdir(parents=True, exist_ok=True)
                download.save_as(str(out_pdf))
                log(f"exported PDF -> {out_pdf.name} ({out_pdf.stat().st_size} bytes)")
            except PWTimeout as exc:
                _save_debug(page, debug_dir, "05c-export-failed", log)
                raise ImporterError(
                    "could not export the deck to PDF (no download captured). The "
                    "export may have exceeded gamma's ~60s server limit (it then "
                    "emails a link instead), or the PDF button label changed. "
                    "Calibrate GAMMA_EXPORT_PDF_LABEL or retry."
                ) from exc

            return doc_url
        finally:
            try:
                context.close()
                browser.close()
            except Exception:  # noqa: BLE001
                pass


# --------------------------------------------------------------- jobs
# In-memory, single active import at a time (browser automation is heavy), polled
# by the dashboard. Mirrors ai_grader's job model.
_jobs: Dict[str, Dict] = {}
_jobs_lock = threading.Lock()
_active_job_id: Optional[str] = None


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


def _append_log(job: Dict, line: str) -> None:
    with _jobs_lock:
        job["_log"].append(f"{_now()} {line}")
        job["message"] = line


def start_import(
    *, pptx_bytes: bytes, filename: str, title: Optional[str] = None, slug: Optional[str] = None
) -> Dict:
    """Validate readiness + slug, stage the upload, and start a background import.

    Raises ValueError (bad request / slug exists) or ImporterError (not ready).
    If an import is already running, returns it unchanged.
    """
    if not filename.lower().endswith((".pptx", ".ppt")):
        raise ValueError("only .pptx/.ppt files are supported")
    if not pptx_bytes:
        raise ValueError("empty upload")

    st = status()
    if not st["ready"]:
        raise ImporterError("importer not ready: " + "; ".join(st["missing"]))

    deck_slug = (slug or slugify(title or filename)).strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", deck_slug):
        raise ValueError(f"invalid slug '{deck_slug}' (use lowercase letters, digits, hyphens)")
    if storage.deck_dir(deck_slug).exists():
        raise ValueError(f"deck '{deck_slug}' already exists — pick a different title/slug")

    global _active_job_id
    with _jobs_lock:
        active = _jobs.get(_active_job_id) if _active_job_id else None
        if active and active["status"] in ("running", "cancelling"):
            return _public_job(active)

        job_id = uuid.uuid4().hex[:12]
        # Stage the uploaded PPTX into local scratch (never the shared data dir).
        uploads = config.IMPORTS_DIR / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        pptx_path = uploads / f"{job_id}.pptx"
        pptx_path.write_bytes(pptx_bytes)

        job = {
            "id": job_id,
            "status": "running",
            "stage": "queued",
            "slug": deck_slug,
            "title": title or storage.prettify(deck_slug),
            "filename": filename,
            "variant": "current",
            "message": "queued",
            "doc_url": None,
            "error": None,
            "started_at": _now(),
            "finished_at": None,
            "_cancel": threading.Event(),
            "_pptx_path": pptx_path,
            "_log": [],
        }
        _jobs[job_id] = job
        _active_job_id = job_id

    threading.Thread(target=_run_import_job, args=(job_id,), daemon=True).start()
    return _public_job(job)


def _set_stage(job: Dict, stage: str, message: str) -> None:
    with _jobs_lock:
        job["stage"] = stage
        job["message"] = message


def _run_import_job(job_id: str) -> None:
    global _active_job_id
    job = _jobs[job_id]
    cancel: threading.Event = job["_cancel"]
    slug = job["slug"]
    pptx_path: Path = job["_pptx_path"]
    log: LogFn = lambda line: _append_log(job, line)  # noqa: E731

    scratch = config.IMPORTS_DIR / "work" / job_id
    debug_dir = config.IMPORTS_DIR / "debug" / job_id
    scratch.mkdir(parents=True, exist_ok=True)
    input_pdf = scratch / config.INPUT_PDF
    output_pdf = scratch / config.VARIANT_BY_KEY["current"]["pdf"]

    try:
        # 1. PPTX -> input.pdf (fast, local)
        _set_stage(job, "converting", "Converting PPTX to input.pdf (LibreOffice)...")
        convert_pptx_to_pdf(pptx_path, input_pdf, log)
        if cancel.is_set():
            raise ImporterError("cancelled")

        # 2. gamma current-import -> current_output.pdf (slow, browser)
        _set_stage(job, "importing", "Running gamma current import + PDF export...")
        doc_url = _gamma_import_to_pdf(pptx_path, output_pdf, debug_dir, log)
        with _jobs_lock:
            job["doc_url"] = doc_url
        if cancel.is_set():
            raise ImporterError("cancelled")

        # 3. Place into the deck folder + render/sync (only now that both exist)
        _set_stage(job, "finalizing", "Saving the pair into Drive and rendering...")
        deck = storage.deck_dir(slug)
        if deck.exists():
            raise ImporterError(f"deck '{slug}' was created by someone else during import")
        deck.mkdir(parents=True, exist_ok=True)
        shutil.copy2(input_pdf, deck / config.INPUT_PDF)
        shutil.copy2(output_pdf, deck / config.VARIANT_BY_KEY["current"]["pdf"])
        try:
            shutil.copy2(pptx_path, deck / config.INPUT_PPTX)  # provenance (ignored by grader)
        except OSError:
            pass
        storage.ensure_rendered(slug, force=True)
        storage.sync_annotation(slug)
        log(f"deck '{slug}' is ready")

        with _jobs_lock:
            if cancel.is_set():
                job["status"] = "cancelled"
            else:
                job["status"] = "done"
                job["stage"] = "done"
                job["message"] = f"Imported '{slug}' (current variant) — ready to grade."
    except ImporterError as exc:
        with _jobs_lock:
            job["status"] = "cancelled" if cancel.is_set() else "error"
            job["stage"] = "error"
            job["error"] = str(exc)
            job["message"] = str(exc)
        log(f"ERROR: {exc}")
    except Exception as exc:  # noqa: BLE001 - never let the worker die silently
        with _jobs_lock:
            job["status"] = "error"
            job["stage"] = "error"
            job["error"] = str(exc)
            job["message"] = str(exc)
        log(f"ERROR (unexpected): {exc}")
    finally:
        with _jobs_lock:
            job["finished_at"] = _now()
            if _active_job_id == job_id:
                _active_job_id = None
        # Best-effort scratch cleanup; keep debug artifacts on failure.
        try:
            if job["status"] == "done":
                shutil.rmtree(scratch, ignore_errors=True)
                pptx_path.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
