"""Render tests for the Knowledge Garden list ↔ cards view toggle (spec 03 F2, T-074).

Fixture-based — monkeypatches the tab's data loader, never reads data/ files
and never touches the network.
"""

import dash
import dash_bootstrap_components as dbc
import pytest

from src.web.dashboard.components import knowledge_garden_tab as tab
from src.web.dashboard.components.saved_items import SAVE_CANDIDATES

_ITEMS = [
    {"title": "Rust in production", "url": "http://example.com/rust", "source": "LessWrong", "summary": "Long-form piece about rust compilers", "published": "2026-08-20T10:00:00"},
    {"title": "Zig allocator notes", "url": "http://example.com/zig", "source": "LessWrong", "summary": "Notes on zig allocators and arenas", "published": "2026-08-21T09:00:00"},
    {"title": "No snippet here", "url": "http://example.com/bare", "source": "LessWrong", "published": "2026-08-22T09:00:00"},
]


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


def _texts(layout):
    return [n for n in _walk(layout) if isinstance(n, str)]


def _of_type(layout, component_type):
    return [n for n in _walk(layout) if isinstance(n, component_type)]


def _by_id_type(layout, id_type):
    return [n for n in _walk(layout) if isinstance(getattr(n, "id", None), dict) and n.id.get("type") == id_type]


def _hrefs(layout):
    return [href for href in (getattr(n, "href", None) for n in _walk(layout)) if href]


def test_list_view_renders_shared_table(patched_data):
    content, page = tab.build_knowledge_table("lesswrong", display_name="LessWrong")
    assert page == 1
    tables = _of_type(content, dbc.Table)
    assert len(tables) == 1
    texts = _texts(content)
    assert "Title" in texts  # canonical table header stays stable
    for item in _ITEMS:
        assert item["title"] in texts


def test_cards_view_renders_card_grid(patched_data):
    content, _page = tab.build_knowledge_table("lesswrong", display_name="LessWrong", view="cards")
    # No table in card view — one dbc.Card per item instead
    assert _of_type(content, dbc.Table) == []
    cards = _of_type(content, dbc.Card)
    assert len(cards) == len(_ITEMS)
    texts = _texts(content)
    hrefs = _hrefs(content)
    for item in _ITEMS:
        assert item["title"] in texts  # title
        assert item["url"] in hrefs  # link
        assert "lesswrong" in " ".join(texts).lower() or item["source"] in texts  # source badge
    assert "Long-form piece about rust compilers" in texts  # snippet text present


def test_card_snippet_degrades_when_missing(patched_data):
    content, _page = tab.build_knowledge_table("lesswrong", display_name="LessWrong", view="cards")
    cards = _of_type(content, dbc.Card)
    bare = next(c for c in cards if "No snippet here" in _texts(c))
    assert bare is not None  # item without summary still renders a card
    assert not any("…" in t for t in _texts(bare))


def test_cards_view_keeps_search_alert_and_star_buttons(patched_data):
    content, _page = tab.build_knowledge_table("lesswrong", search_term="zig", display_name="LessWrong", view="cards")
    texts = _texts(content)
    assert "🌱 Found 1 items matching 'zig'" in texts  # search summary carried over
    stars = _by_id_type(content, "kg-save-btn")
    assert len(stars) == 1  # the save star keeps working in card view


def test_subtab_layout_has_toggle_button_and_store(patched_data):
    layout = tab.create_knowledge_source_tab_content("lesswrong", combined_name="LessWrong")
    stores = [n for n in _walk(layout) if isinstance(getattr(n, "id", None), str) and n.id.endswith("-view")]
    assert any(s.id == "knowledge-search-lesswrong-view" and s.data == "list" for s in stores)  # default view store
    buttons = [n for n in _walk(layout) if isinstance(getattr(n, "id", None), str) and n.id == "knowledge-search-lesswrong-view-toggle"]
    assert len(buttons) == 1
    assert buttons[0].children == tab.KG_VIEW_TOGGLE_LABELS["list"]  # button offers the switch to cards


def test_toggle_callback_wired_in_controller(patched_data):
    app = dash.Dash("test-kg-toggle")
    tab.register_knowledge_garden_callbacks(app)
    # The controller owns the results, page AND view outputs (single callback pattern)
    controller = next(spec for spec in app.callback_map.values() if "knowledge-search-lesswrong-view.data" in str(spec.get("output", "")))
    output_str = str(controller["output"]).replace("'", "").replace(" ", "")
    assert "knowledge-search-lesswrong-results.children" in output_str
    assert "knowledge-search-lesswrong-page.data" in output_str
    assert "knowledge-search-lesswrong-view.data" in output_str
    assert "knowledge-search-lesswrong-view-toggle.children" in output_str
    assert "knowledge-search-lesswrong-view-toggle" in str(controller["inputs"])  # toggle is an input of the controller
