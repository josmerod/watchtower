"""Unit tests for the Knowledge Garden NUEVO badge plumbing (T-085).

Locks the DOM contract that ``assets/js/kg_state.js`` depends on: list rows
and card wrappers carry ``data-kg-date`` (ISO string, empty when undated),
the layout exposes the ``kg-new-counter`` header chip, and the pure
``_kg_date_iso`` helper agrees with ``get_sortable_date``'s field order.
Fixture-based like ``test_kg_card_view_toggle.py`` — monkeypatches the tab's
data loader, never reads data/ files and never touches the network.
"""

from pathlib import Path

import dash_bootstrap_components as dbc
import pytest
from dash import html

from src.web.dashboard.components import knowledge_garden_tab as tab
from src.web.dashboard.components.saved_items import SAVE_CANDIDATES

_ITEMS = [
    {"title": "Dated post", "url": "http://example.com/dated", "source": "LessWrong", "published": "2026-08-20T10:00:00"},
    {"title": "Created issue", "url": "http://example.com/created", "source": "LessWrong", "created_at": "2026-08-21T09:00:00"},
    {"title": "Undated", "url": "http://example.com/bare", "source": "LessWrong"},
]

_JS_PATH = Path(__file__).resolve().parents[2] / "src" / "web" / "dashboard" / "assets" / "js" / "kg_state.js"


@pytest.fixture
def patched_data(monkeypatch):
    """Freeze the tab's data source so tests are hermetic."""
    SAVE_CANDIDATES.clear()
    data = {"lesswrong": [dict(item) for item in _ITEMS]}
    monkeypatch.setattr(tab, "get_all_knowledge_data", lambda force_refresh=False: data)
    yield
    SAVE_CANDIDATES.clear()


def _walk(node):
    """Yield every node of a Dash component tree."""
    yield node
    children = getattr(node, "children", None)
    if children is None:
        return
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        yield from _walk(child)


def _kg_date(node) -> str | None:
    return getattr(node, "data-kg-date", None)


# ---------------------------------------------------------------------------
# Pure helper: date extraction / threshold input
# ---------------------------------------------------------------------------


def test_kg_date_iso_prefers_first_matching_field():
    from src.services.data_loader import parse_date

    def norm(raw: str) -> str:
        return parse_date(raw).isoformat()

    # Compare against the same parser's output: tz-normalization stays out of
    # the test (naive local times shift when converted to UTC).
    assert tab._kg_date_iso({"published": "2026-08-20T10:00:00"}) == norm("2026-08-20T10:00:00")
    # published_at outranks created_at (same order get_sortable_date uses)
    assert tab._kg_date_iso({"published_at": "2026-08-01T12:00:00", "created_at": "2020-01-01T00:00:00"}) == norm("2026-08-01T12:00:00")
    assert tab._kg_date_iso({"created_at": "2026-08-21T09:00:00"}) == norm("2026-08-21T09:00:00")
    assert "T" in tab._kg_date_iso({"published": "2026-08-20T10:00:00"})  # ISO 8601 for Date.parse


def test_kg_date_iso_falls_back_to_raw_string_when_parser_rejects():
    # Values the parser rejects pass through untouched; kg_state.js skips
    # whatever Date.parse cannot read.
    assert tab._kg_date_iso({"date": "not-a-date"}) == "not-a-date"


def test_kg_date_iso_empty_when_undated():
    assert tab._kg_date_iso({}) == ""
    assert tab._kg_date_iso({"published": "", "date": None}) == ""


# ---------------------------------------------------------------------------
# Render contract: rows and cards carry data-kg-date
# ---------------------------------------------------------------------------


def test_list_rows_carry_kg_date_in_item_order(patched_data):
    content, _page = tab.build_knowledge_table("lesswrong", display_name="LessWrong")
    body_rows = [n for n in _walk(content) if isinstance(n, html.Tr) and _kg_date(n) is not None]
    assert len(body_rows) == len(_ITEMS)
    dates = [_kg_date(n) for n in body_rows]
    # Rows render newest-first (get_sortable_date desc): created 08-21, then
    # published 08-20, then the undated item with an empty attribute.
    assert dates[0].startswith("2026-08-21")
    assert dates[1].startswith("2026-08-20")
    assert dates[2] == ""  # undated → present but empty (never badged)


def test_list_row_attribute_survives_serialization(patched_data):
    """The post-construction wildcard must reach the browser props."""
    content, _page = tab.build_knowledge_table("lesswrong", display_name="LessWrong")
    row = next(n for n in _walk(content) if isinstance(n, html.Tr) and _kg_date(n))
    props = row.to_plotly_json()["props"]
    assert props.get("data-kg-date") == _kg_date(row)


def test_card_wrappers_carry_kg_date(patched_data):
    content, _page = tab.build_knowledge_table("lesswrong", display_name="LessWrong", view="cards")
    wrappers = [n for n in _walk(content) if isinstance(n, html.Div) and _kg_date(n) is not None]
    assert len(wrappers) == len(_ITEMS)
    # Date-only prefixes (render order is newest-first like the list view);
    # the universal parser normalizes to UTC based on the machine timezone,
    # so exact times would make the test tz-dependent.
    dates = [_kg_date(n) for n in wrappers]
    assert dates[0].startswith("2026-08-21") and dates[1].startswith("2026-08-20")
    assert dates[2] == ""  # undated → present but empty (never badged)
    # the dbc.Card still renders inside the wrapper (view toggle unaffected)
    assert len([n for n in _walk(content) if isinstance(n, dbc.Card)]) == len(_ITEMS)


def test_no_match_alert_renders_without_rows(patched_data):
    content, page = tab.build_knowledge_table("lesswrong", search_term="zzz-no-match", display_name="LessWrong")
    assert page == 1
    assert [n for n in _walk(content) if isinstance(n, html.Tr)] == []  # tolerant empty state, no crash


def test_layout_has_new_counter_chip():
    spans = [n for n in _walk(tab.render_knowledge_garden_tab()) if getattr(n, "id", None) == "kg-new-counter"]
    assert len(spans) == 1  # exactly one counter target for kg_state.js


# ---------------------------------------------------------------------------
# JS contract: hook points kg_state.js must keep
# ---------------------------------------------------------------------------


def test_js_contract_for_nuevo_badges():
    js = _JS_PATH.read_text(encoding="utf-8")
    assert "wt_kg_last_visit" in js, "localStorage last-visit key renamed"
    assert "data-kg-date" in js, "row date attribute no longer read"
    assert "wt-kg-new-badge" in js, "badge class renamed"
    assert "NUEVO" in js, "badge label changed"
    assert "kg-new-counter" in js, "toolbar counter target changed"
    assert "toISOString" in js, "last-visit stamp must stay ISO (Date.parse round-trip)"
    assert "sessionBaseline" in js, "per-session baseline (first-visit no-badges) removed"
    # House rules: observer debounced, last-visit bump debounced
    assert "MutationObserver" in js and "scheduleRefresh" in js
    assert js.count("setTimeout") >= 2, "debounces removed (observer + last-visit stamp)"
