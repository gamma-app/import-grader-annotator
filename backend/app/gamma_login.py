"""One-time interactive capture of a gamma.app login session for the importer.

Launches a HEADED Chromium, opens gamma.app, and waits for you to log in by hand
(Google SSO, email, whatever your account uses). Once you're signed in, press
Enter in the terminal and it saves a Playwright ``storageState`` (the
``gamma_session`` cookies) to ``GAMMA_AUTH_STATE_PATH``. The importer then reuses
that session headlessly.

    backend/.venv/bin/python -m app.gamma_login

Re-run this whenever the importer reports the session is expired/invalid. The
saved file contains live session cookies — it is machine-local and gitignored;
never commit it or put it in the shared data dir.
"""
from __future__ import annotations

import sys
from pathlib import Path

from . import config


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Playwright is not installed. Run:\n"
            "  backend/.venv/bin/pip install -r backend/requirements.txt\n"
            "  backend/.venv/bin/playwright install chromium",
            file=sys.stderr,
        )
        return 1

    out_path: Path = config.GAMMA_AUTH_STATE_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Opening {config.GAMMA_BASE_URL} in a browser window...")
    print("Log in to gamma.app, then come back here and press Enter.")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=config.GAMMA_USER_AGENT,
            ignore_https_errors=True,
        )
        page = context.new_page()
        try:
            page.goto(config.GAMMA_BASE_URL, wait_until="domcontentloaded", timeout=120_000)
        except Exception as exc:  # noqa: BLE001 - navigation hiccups shouldn't abort login
            print(f"(warning) initial navigation issue: {exc}")

        try:
            input("\nPress Enter once you are fully logged in (dashboard visible)... ")
        except (EOFError, KeyboardInterrupt):
            print("\nAborted; no session saved.", file=sys.stderr)
            context.close()
            browser.close()
            return 1

        context.storage_state(path=str(out_path))
        context.close()
        browser.close()

    print(f"\nSaved gamma session to: {out_path}")
    print("The importer can now run headlessly. Re-run this if it ever expires.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
