"""The search controllers of the News subtabs only run when the user types (T-163).

The layout renders the table of every subtab. The fifteen generic controllers
used to run once more when the tab was inserted and rebuild the same tables:
sixteen requests to open News, sixteen tables replaced a moment after landing.
The search boxes also wait for a pause in typing.
Fixtures only: the tab's data loader is replaced, no file is read.
"""

import json

import dash
import pytest
from dash import html

from src.web.dashboard.components import news_tab as tab

_STORY = {"title": "Rust rewrite shipped", "url": "https://example.com/rust", "published": "2026-11-26T10:00:00Z"}


def _stories(count):
    return [{"title": f"Story number {i}", "url": f"https://example.com/{i}", "published": f"2026-11-{26 - i:02d}T10:00:00Z"} for i in range(count)]


def _plain_subtabs():
    """The subtabs served by the generic controller (Top Tech has its own)."""
    return [tab_def for tab_def in tab.NEWS_TAB_DEFINITIONS if not tab_def.get("paginated")]


def _as_json(node):
    return json.dumps(node.to_plotly_json(), sort_keys=True, default=str)


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if children is None:
        return
    for child in children if isinstance(children, (list, tuple)) else [children]:
        yield from _walk(child)


@pytest.fixture
def one_source(monkeypatch):
    """Serve stories under one source key; every other source is empty."""
    key = _plain_subtabs()[1]["keys"]  # a single-source subtab
    holder = {"data": {}}

    def serve(stories):
        holder["data"] = {key: stories}
        monkeypatch.setattr(tab, "get_all_news_data", lambda: {source: [] for source in tab._ALL_NEWS_SOURCES} | holder["data"])

    serve([])
    return key, serve


def _controller(app, search_id):
    return app.callback_map[f"{search_id}-results.children"]["callback"].__wrapped__


def _subtab(key):
    return next(tab_def for tab_def in _plain_subtabs() if tab_def["keys"] == key)


def test_search_controllers_are_idle_on_load():
    """The layout already carries each table: nothing is left for a callback to do on insertion."""
    app = dash.Dash("test-news-idle")
    tab.register_news_search_callbacks(app)

    for tab_def in _plain_subtabs():
        search_id = tab._search_id_for_tab(tab_def)
        (entry,) = [e for e in app._callback_list if f"{search_id}-results.children" in e["output"]]
        assert entry["prevent_initial_call"] is True, search_id
        assert {"id": search_id, "property": "value"} in entry["inputs"]


def test_layout_shows_what_the_controller_shows_for_an_empty_term(one_source):
    key, serve = one_source
    serve([_STORY, *_stories(tab.MAX_ARTICLES_PER_SOURCE + 5)])
    tab_def = _subtab(key)
    search_id = tab._search_id_for_tab(tab_def)
    app = dash.Dash("test-news-same")
    tab.register_news_search_callbacks(app)

    layout = tab.create_news_source_tab_content(tab_def["keys"], combined_name=tab_def["label"])
    (container,) = [n for n in _walk(layout) if getattr(n, "id", None) == f"{search_id}-results"]

    assert _as_json(container.children) == _as_json(_controller(app, search_id)(""))
    assert _as_json(container.children) == _as_json(_controller(app, search_id)(None))


def test_search_waits_for_a_pause_in_typing():
    """Every subtab's search box, Top Tech's included, asks once per pause and not once per keystroke."""
    for tab_def in tab.NEWS_TAB_DEFINITIONS:
        layout = tab.create_news_source_tab_content(tab_def["keys"], combined_name=tab_def["label"], with_pagination=bool(tab_def.get("paginated")))
        (box,) = [n for n in _walk(layout) if getattr(n, "id", None) == tab._search_id_for_tab(tab_def)]

        assert box.debounce == tab.NEWS_SEARCH_DEBOUNCE_MS, tab_def["label"]


def test_table_lists_the_newest_articles_up_to_the_limit(one_source):
    key, serve = one_source
    serve(_stories(60))
    tab_def = _subtab(key)
    app = dash.Dash("test-news-limit")
    tab.register_news_search_callbacks(app)

    results = _controller(app, tab._search_id_for_tab(tab_def))("")

    titles = [text for text in _texts(results) if text.startswith("Story number")]
    assert len(titles) == tab.MAX_ARTICLES_PER_SOURCE
    assert titles[0] == "Story number 0"  # the newest comes first
    assert "Found" not in " ".join(_texts(results))  # no count alert while nothing is searched


def test_search_lists_the_matches_with_a_count(one_source):
    key, serve = one_source
    serve([_STORY, *_stories(5)])
    tab_def = _subtab(key)
    app = dash.Dash("test-news-search")
    tab.register_news_search_callbacks(app)

    results = _controller(app, tab._search_id_for_tab(tab_def))("rust")

    texts = _texts(results)
    assert "📰 Found 1 articles matching 'rust'" in texts
    assert "Rust" in texts and " rewrite shipped" in texts  # the match, with its highlight
    assert not any(text.startswith("Story number") for text in texts)


def test_rows_carry_the_source_name_and_the_read_state_key(one_source):
    key, serve = one_source
    serve([_STORY])
    tab_def = _subtab(key)
    app = dash.Dash("test-news-rows")
    tab.register_news_search_callbacks(app)

    (row,) = [n for n in _walk(_controller(app, tab._search_id_for_tab(tab_def))("")) if getattr(n, "data-item-hash", None)]
    cells = row.children

    assert tab._ALL_NEWS_SOURCES[key]["name"] in _texts(cells[1])  # the Source column
    assert getattr(row, "data-item-hash") == tab._news_item_hash(_STORY["url"], _STORY["title"])


def test_source_without_articles_says_so(one_source):
    key, _ = one_source
    tab_def = _subtab(key)
    app = dash.Dash("test-news-empty")
    tab.register_news_search_callbacks(app)

    assert "No data available (fetch returned empty)" in _texts(_controller(app, tab._search_id_for_tab(tab_def))(""))


def _texts(node):
    return [text for text in _walk(node) if isinstance(text, str)]
