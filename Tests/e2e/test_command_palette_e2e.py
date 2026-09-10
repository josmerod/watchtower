"""E2E specs for the Ctrl+K command palette.

The palette works in shortcuts-only mode without the API (silent fallback,
T-057), so these specs are data-independent: the shortcut list is rendered
server-side into #palette-data.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


def test_palette_opens_with_ctrl_k(dashboard_page):
    """Ctrl+K opens the palette overlay with its input focused."""
    dashboard_page.keyboard.press("Control+k")
    dashboard_page.wait_for_selector("#wt-palette-input", timeout=10_000)
    assert dashboard_page.locator("#wt-palette-input").is_visible()


def test_palette_lists_shortcuts_without_query(dashboard_page):
    """The empty-query palette shows shortcut entries (server-rendered data)."""
    dashboard_page.keyboard.press("Control+k")
    dashboard_page.wait_for_selector("#wt-palette-list", timeout=10_000)
    dashboard_page.wait_for_function(
        "() => document.querySelectorAll('#wt-palette-list div').length > 0",
        timeout=10_000,
    )


def test_palette_escape_closes(dashboard_page):
    """Esc closes the overlay (hidden via display:none — stays in DOM)."""
    dashboard_page.keyboard.press("Control+k")
    dashboard_page.wait_for_selector("#wt-palette-input", timeout=10_000)
    # show() focuses the input on a 30ms timer — wait for the real focus so
    # the Escape keydown reaches the input's handler.
    dashboard_page.wait_for_function(
        "() => document.activeElement && document.activeElement.id === 'wt-palette-input'",
        timeout=10_000,
    )
    dashboard_page.keyboard.press("Escape")
    dashboard_page.wait_for_selector("#wt-palette-overlay", state="hidden", timeout=10_000)
