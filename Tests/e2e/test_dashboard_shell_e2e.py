"""E2E specs for the dashboard shell: home load, nav, tab switching.

Structural assertions only (ids and nav labels render regardless of local
``data/``), so these pass both on dev machines and in CI without data.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

# Tabs registered in app.py's nav (subset with stable labels).
EXPECTED_TAB_LABELS = ("News", "📈 Markets", "🛡️ Security", "🛰️ Tech Radar", "📊 Metrics")
# Hidden on purpose (T-060, reversible): must NOT appear in the nav.
HIDDEN_TAB_LABEL = "Shortcuts"


def test_home_loads_with_nav_tabs(dashboard_page):
    """The dashboard serves HTML and mounts the tab nav."""
    # Dash serves "Updating..." until the renderer sets the real title.
    dashboard_page.wait_for_function("() => document.title && document.title !== 'Updating...'", timeout=15_000)
    assert "Watchtower" in dashboard_page.title()
    tabs = dashboard_page.locator(".nav-link")
    assert tabs.count() >= 10, f"expected >=10 nav tabs, got {tabs.count()}"


def test_expected_tabs_present(dashboard_page):
    """The core tabs are in the nav."""
    # .first: lazily-mounted tab content can add its own subtab nav (a second
    # ul.nav-tabs) before this runs; the main nav is always first in the DOM.
    nav_text = dashboard_page.locator("ul.nav-tabs").first.inner_text()
    for label in EXPECTED_TAB_LABELS:
        assert label in nav_text, f"tab {label!r} missing from nav"


def test_shortcuts_tab_stays_hidden(dashboard_page):
    """Shortcuts was hidden from the nav (T-060) — keep it that way."""
    nav_text = dashboard_page.locator("ul.nav-tabs").first.inner_text()
    assert HIDDEN_TAB_LABEL not in nav_text


def test_switching_to_news_renders_global_search(dashboard_page):
    """News tab → 🔎 Global subtab (last, T-061) exposes the global search."""
    dashboard_page.get_by_role("tab", name="News").first.click()
    # News content (and its subtabs) render lazily; the input only becomes
    # visible once the 🔎 Global subtab — the LAST one (T-061) — is active.
    global_tab = dashboard_page.get_by_role("tab", name="🔎 Global")
    global_tab.wait_for(state="visible", timeout=15_000)
    global_tab.click()
    dashboard_page.wait_for_selector("#news-global-search-input", state="visible", timeout=15_000)


def test_switching_to_markets_renders_container(dashboard_page):
    """Clicking the Markets tab mounts its content container."""
    dashboard_page.get_by_role("tab", name="📈 Markets").click()
    # The Markets layout is lazy-rendered on first activation; wait for any of
    # its landmark ids (table or its summary/header area).
    dashboard_page.wait_for_selector("#markets-main-container, #markets-container, .card", timeout=15_000)


def test_switching_to_metrics_renders_summary(dashboard_page):
    """Clicking Metrics mounts the collapsible system-state area (T-063)."""
    dashboard_page.get_by_role("tab", name="📊 Metrics").click()
    dashboard_page.wait_for_selector("#metrics-table-container", timeout=15_000)
