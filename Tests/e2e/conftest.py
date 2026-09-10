"""Shared fixtures for browser E2E tests (live dashboard).

Starts the real Dash dashboard once per session on a scratch port
(``WATCHTOWER_DASHBOARD_PORT``, default 7791). Tests skip cleanly when either
``pytest-playwright`` or the chromium binaries are unavailable, so CI stays
green in environments that skip ``playwright install``.

The 2026-09-10 cleanup deleted the old e2e suite (it tested removed features:
customize-tabs drag&drop, filter presets, recommendations, shortcuts sidebar).
These specs target LIVE tabs only and assert structure (ids, nav, interactions)
so they pass with or without local ``data/``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

pytest.importorskip("pytest_playwright")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PORT = int(os.getenv("WATCHTOWER_E2E_PORT", "7791"))
BASE_URL = f"http://127.0.0.1:{PORT}"

SERVER_START_TIMEOUT_SECONDS = 120


def _current_changelog_version() -> str:
    """The deployed changelog version, so e2e pages look like returning visitors.

    The 🆕 Novedades modal auto-opens once per unseen version (T-089); without
    this seed its backdrop would nondeterministically cover the nav mid-test.
    """
    try:
        import json

        return str(json.loads((PROJECT_ROOT / "changelog.json").read_text(encoding="utf-8"))["version"])
    except Exception:
        return "e2e-no-changelog"


def _browser_available() -> bool:
    """Probe whether chromium can actually launch (binaries installed)."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def _require_chromium():
    """Skip the whole e2e session when the browser binary is missing."""
    if not _browser_available():
        pytest.skip("playwright chromium not installed (run: playwright install chromium)")


@pytest.fixture(scope="session")
def dashboard_url():
    """Launch the real dashboard once and yield its base URL."""
    env = {**os.environ, "WATCHTOWER_DASHBOARD_PORT": str(PORT)}
    proc = subprocess.Popen(
        [sys.executable, "run_watchtower_dashboard.py"],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.time() + SERVER_START_TIMEOUT_SECONDS
        while time.time() < deadline:
            if proc.poll() is not None:
                pytest.fail(f"dashboard process exited early with code {proc.returncode}")
            try:
                with urllib.request.urlopen(f"{BASE_URL}/", timeout=2) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(1)
        else:
            pytest.fail(f"dashboard did not answer within {SERVER_START_TIMEOUT_SECONDS}s")
        yield BASE_URL
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture()
def dashboard_page(page, dashboard_url):
    """A playwright page already loaded on the dashboard home."""
    # Returning-visitor baseline: pre-seen changelog version so the modal
    # never auto-opens over the tests (see _current_changelog_version).
    page.add_init_script(
        "try { localStorage.setItem('wt_changelog_version', %s); } catch (e) {}" % json.dumps(_current_changelog_version())
    )
    page.goto(dashboard_url, wait_until="domcontentloaded")
    # Give Dash's renderer a moment to mount the layout on first load.
    page.wait_for_selector(".nav-link", timeout=30_000)
    return page
