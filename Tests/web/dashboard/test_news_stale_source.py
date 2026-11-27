"""A News source that stopped publishing is named above its table (T-176).

Three sources went unnoticed for months: their ETLs rewrote the file every
cycle (or failed quietly) and the tab showed them like any other. Fixtures
only: the tab's data loader is replaced, no file is read.
"""

from datetime import datetime, timedelta, timezone

import dash_bootstrap_components as dbc
import pytest

from src.web.dashboard.components import news_tab as tab

SUBTAB = next(tab_def for tab_def in tab.NEWS_TAB_DEFINITIONS if tab_def["id"] == "ft-bb")
FUTURETOOLS, BENSBITES = SUBTAB["keys"]


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if children is None:
        return
    for child in children if isinstance(children, (list, tuple)) else [children]:
        yield from _walk(child)


def _texts(node):
    return [text for text in _walk(node) if isinstance(text, str)]


def _alerts(node, color):
    return [n for n in _walk(node) if isinstance(n, dbc.Alert) and getattr(n, "color", None) == color]


def _issue(source, days_ago):
    moment = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {"title": f"An issue of {source}", "url": f"https://example.test/{source}/{days_ago}", "published_at": moment.isoformat()}


@pytest.fixture()
def serve(monkeypatch):
    """Serve the given items under their source keys; every other source is empty."""

    def load(**sources):
        data = {source: [] for source in tab._ALL_NEWS_SOURCES} | sources
        monkeypatch.setattr(tab, "get_all_news_data", lambda: data)

    return load


def test_a_source_whose_newest_item_is_old_is_named(serve):
    serve(**{FUTURETOOLS: [_issue(FUTURETOOLS, 500), _issue(FUTURETOOLS, 940)], BENSBITES: [_issue(BENSBITES, 3)]})

    results = tab._render_news_results(SUBTAB["keys"])

    (warning,) = _alerts(results, "warning")
    newest = datetime.now(timezone.utc) - timedelta(days=500)
    assert _texts(warning) == [f"⚠️ FutureTools lleva sin publicar nada nuevo desde el {newest:%d/%m/%Y}."]
    assert results.children[0] is warning  # above the table, which is still there with both sources
    assert "An issue of futuretools" in _texts(results) and "An issue of bensbites" in _texts(results)


def test_a_source_that_published_within_the_week_is_not_named(serve):
    serve(**{FUTURETOOLS: [_issue(FUTURETOOLS, tab.STALE_SOURCE_DAYS - 1)], BENSBITES: [_issue(BENSBITES, 0)]})

    assert _alerts(tab._render_news_results(SUBTAB["keys"]), "warning") == []


def test_a_source_without_items_or_dates_is_not_named(serve):
    serve(**{FUTURETOOLS: [{"title": "Undated", "url": "https://example.test/undated"}], BENSBITES: [_issue(BENSBITES, 1)]})

    results = tab._render_news_results(SUBTAB["keys"])

    assert _alerts(results, "warning") == []  # an item without a date says nothing about the source
    serve(**{FUTURETOOLS: [], BENSBITES: []})
    (only,) = _alerts(tab._render_news_results(SUBTAB["keys"]), "warning")
    assert _texts(only) == ["No data available (fetch returned empty)"]


def test_the_note_survives_a_search(serve):
    serve(**{FUTURETOOLS: [_issue(FUTURETOOLS, 940)], BENSBITES: [_issue(BENSBITES, 2)]})

    results = tab._render_news_results(SUBTAB["keys"], "issue of bensbites")

    (warning,) = _alerts(results, "warning")
    assert "FutureTools" in _texts(warning)[0]
    assert _texts(results.children[1])[0].startswith("📰 Found 1 articles")
