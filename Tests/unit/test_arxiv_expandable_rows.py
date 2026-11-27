"""Render tests for expandable paper rows: abstract + cluster (spec 10 M2, T-074).

Fixture-based — monkeypatches the tab's data loader, never reads data/ files
and never touches the network.
"""

import dash
import pytest

from src.web.dashboard.components import arxiv_research_tab as tab

_ABSTRACT = "We propose a novel method for folding variant channel directories into canonical channels using pure-Dash collapse components."


def _paper(title, **extra):
    record = {
        "source": "arxiv",
        "id": f"https://arxiv.org/abs/2608.{1000 + len(title)}",
        "link": f"https://arxiv.org/abs/2608.{1000 + len(title)}",
        "title": title,
        "authors": ["Ana", "Bob"],
        "published": "2026-08-25T00:00:00.000Z",
        "summary": _ABSTRACT,
    }
    record.update(extra)
    return record


@pytest.fixture
def patched_data(monkeypatch):
    """Freeze the tab's data sources so tests are hermetic."""
    monkeypatch.setattr(tab, "get_trending_items_map", lambda: {})
    holder = {}

    def _set(papers, source_key="all_arxiv"):
        holder["data"] = {source_key: papers}
        monkeypatch.setattr(tab, "get_all_arxiv_data", lambda: holder["data"])

    return _set


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


def _by_id_type(layout, id_type):
    return [n for n in _walk(layout) if isinstance(getattr(n, "id", None), dict) and n.id.get("type") == id_type]


def test_rows_expandable_with_abstract_collapsed_by_default(patched_data):
    papers = [_paper("Paper One"), _paper("Paper Two", cluster_label="clustering", cluster_keywords=["kmeans", "embeddings"])]
    patched_data(papers)
    layout = tab.create_arxiv_category_tab_content("all_arxiv")

    # One expander button and one collapse per paper
    buttons = _by_id_type(layout, tab.ARXIV_EXPAND_BTN_TYPE)
    collapses = _by_id_type(layout, tab.ARXIV_DETAIL_COLLAPSE_TYPE)
    assert len(buttons) == 2 and len(collapses) == 2
    # Collapsed by default
    assert all(c.is_open is False for c in collapses)
    # Button and collapse for the same paper share the pattern index
    btn_indexes = {b.id["index"] for b in buttons}
    assert btn_indexes == {c.id["index"] for c in collapses}

    # The abstract text is present in the (hidden) detail rows
    texts = _texts(layout)
    assert _ABSTRACT in texts
    assert "Abstract" in texts
    # Cluster metadata renders when the ETL provided it
    assert "🧩 clustering" in texts
    assert "kmeans" in texts and "embeddings" in texts


def test_detail_degrades_without_cluster_fields(patched_data):
    patched_data([_paper("Bare Paper")])
    layout = tab.create_arxiv_category_tab_content("all_arxiv")
    texts = _texts(layout)
    assert _ABSTRACT in texts  # abstract still shown
    assert "🧩" not in " ".join(texts)  # no bogus cluster badge


def test_detail_placeholder_when_no_abstract(patched_data):
    patched_data([_paper("Empty Paper", summary="")])
    layout = tab.create_arxiv_category_tab_content("all_arxiv")
    assert "Sin abstract ni cluster para este paper." in _texts(layout)


def test_table_header_keeps_canonical_columns(patched_data):
    patched_data([_paper("Header Paper")])
    layout = tab.create_arxiv_category_tab_content("all_arxiv")
    texts = _texts(layout)
    assert "Title" in texts and "Authors" in texts and "Published Date" in texts


def test_expand_toggle_callback_registered():
    app = dash.Dash("test-arxiv-expand")
    tab.register_arxiv_callbacks(app)
    toggle_spec = next(spec for spec in app.callback_map.values() if tab.ARXIV_DETAIL_COLLAPSE_TYPE in str(spec.get("output", "")))
    assert "is_open" in str(toggle_spec["output"])
    assert tab.ARXIV_EXPAND_BTN_TYPE in str(toggle_spec["inputs"])  # pattern-matching input wired


# --- One category in the page at a time (T-172) ---
#
# With every category rendered at once the tab held more than two thousand
# pattern-matching ids and froze the browser: the renderer reindexes the ids
# of the whole layout on every update, comparing each one against the previous list.


def _sources(monkeypatch, **papers_by_key):
    """Serve the given papers under their category keys."""
    monkeypatch.setattr(tab, "get_all_arxiv_data", lambda: papers_by_key)


def _search_box(layout):
    return next((n for n in _walk(layout) if getattr(n, "id", None) == tab.ARXIV_SEARCH_ID), None)


def _listening(app, component_id, prop, output_part=None):
    """The callback registrations (Dash's own record, flags included) that listen to a component."""
    return [e for e in app._callback_list if (output_part is None or output_part in e["output"]) and any(r.get("id") == component_id and r.get("property") == prop for r in e["inputs"])]


def test_tab_holds_the_table_of_the_first_category_only(patched_data, monkeypatch):
    _sources(monkeypatch, hf_trending=[_paper(f"Trend {i}") for i in range(3)], all_arxiv=[_paper(f"All {i}") for i in range(5)], machine_learning=[_paper("ML 0")])
    layout = tab.render_arxiv_research_tab()
    # Three papers of the first category, not the nine of the three: one button and one detail each
    assert len(_by_id_type(layout, tab.ARXIV_EXPAND_BTN_TYPE)) == 3
    assert len(_by_id_type(layout, tab.ARXIV_DETAIL_COLLAPSE_TYPE)) == 3


def test_tab_bar_lists_every_category_and_no_table(patched_data, monkeypatch):
    _sources(monkeypatch, hf_trending=[_paper("Only One")], all_arxiv=[_paper("Hidden One")])
    layout = tab.render_arxiv_research_tab()
    bar = next(n for n in _walk(layout) if getattr(n, "id", None) == tab.ARXIV_TABS_ID)
    # Every configured source gets its place in the bar, in the order of the configuration: a new one cannot be missed
    tab_ids = [t.tab_id for t in bar.children]
    assert tab_ids == [f"{tab.ARXIV_TAB_ID_PREFIX}{key}" for key in tab.ARXIV_SOURCES_CONFIG]
    assert tab_ids[:2] == [f"{tab.ARXIV_TAB_ID_PREFIX}hf_trending", f"{tab.ARXIV_TAB_ID_PREFIX}all_arxiv"]
    assert bar.active_tab == tab_ids[0]  # given: the bar would otherwise set it on mount and run the controller once more
    assert all(t.children is None for t in bar.children)  # the content is rendered by the controller, never by the bar
    assert [t.label for t in bar.children] == [tab.ARXIV_SOURCES_CONFIG[key]["name"] for key in tab._arxiv_source_keys()]


def test_search_box_stays_outside_the_table_container(patched_data, monkeypatch):
    _sources(monkeypatch, hf_trending=[_paper("Trend")])
    layout = tab.render_arxiv_research_tab()
    container = next(n for n in _walk(layout) if getattr(n, "id", None) == tab.ARXIV_CONTENT_ID)
    box = _search_box(layout)
    # The controller replaces the container's children: a search box inside would be inserted on
    # every category switch and fire the controller again.
    assert box is not None and _search_box(container) is None
    assert _by_id_type(container, tab.ARXIV_EXPAND_BTN_TYPE)  # the open category's table is rendered here
    assert box.debounce == tab.ARXIV_SEARCH_DEBOUNCE_MS
    assert box.placeholder == tab._arxiv_placeholder("hf_trending")


def test_controller_shows_the_category_that_was_opened(patched_data, monkeypatch):
    _sources(monkeypatch, hf_trending=[_paper("Trend")], all_arxiv=[_paper(f"All {i}") for i in range(4)])
    content, search_value, placeholder = tab._arxiv_category_update(tab.ARXIV_TABS_ID, f"{tab.ARXIV_TAB_ID_PREFIX}all_arxiv", None)
    assert len(_by_id_type(content, tab.ARXIV_EXPAND_BTN_TYPE)) == 4
    assert search_value is dash.no_update  # nothing to clear
    assert placeholder == tab._arxiv_placeholder("all_arxiv")
    assert "All Papers" in placeholder


def test_controller_empties_the_search_box_when_switching_with_a_term(patched_data, monkeypatch):
    _sources(monkeypatch, all_arxiv=[_paper("Alpha One"), _paper("Beta Two")])
    content, search_value, _ = tab._arxiv_category_update(tab.ARXIV_TABS_ID, f"{tab.ARXIV_TAB_ID_PREFIX}all_arxiv", "Alpha")
    assert search_value == ""
    assert len(_by_id_type(content, tab.ARXIV_EXPAND_BTN_TYPE)) == 2  # the new category opens unfiltered


def test_controller_filters_on_typing_and_leaves_the_box_alone(patched_data, monkeypatch):
    _sources(monkeypatch, all_arxiv=[_paper("Alpha One"), _paper("Beta Two"), _paper("Gamma Three")])
    content, search_value, placeholder = tab._arxiv_category_update(tab.ARXIV_SEARCH_ID, f"{tab.ARXIV_TAB_ID_PREFIX}all_arxiv", "two")
    assert len(_by_id_type(content, tab.ARXIV_EXPAND_BTN_TYPE)) == 1
    assert "📰 Found 1 papers matching 'two'" in _texts(content)
    assert search_value is dash.no_update and placeholder is dash.no_update


def test_search_never_lists_more_than_the_default_view(patched_data, monkeypatch):
    _sources(monkeypatch, all_arxiv=[_paper(f"Shared Word {i}") for i in range(tab.MAX_PAPERS_PER_TAB + 10)])
    content, _, _ = tab._arxiv_category_update(tab.ARXIV_SEARCH_ID, f"{tab.ARXIV_TAB_ID_PREFIX}all_arxiv", "shared")
    assert len(_by_id_type(content, tab.ARXIV_EXPAND_BTN_TYPE)) == tab.MAX_PAPERS_PER_TAB
    assert f"Found {tab.MAX_PAPERS_PER_TAB + 10} papers matching 'shared' — showing the first {tab.MAX_PAPERS_PER_TAB}" in " ".join(_texts(content))


def test_search_without_matches_says_so(patched_data, monkeypatch):
    _sources(monkeypatch, all_arxiv=[_paper("Alpha One")])
    content, _, _ = tab._arxiv_category_update(tab.ARXIV_SEARCH_ID, f"{tab.ARXIV_TAB_ID_PREFIX}all_arxiv", "zzz")
    assert f"No papers matching 'zzz' in {tab.ARXIV_SOURCES_CONFIG['all_arxiv']['name']}." in _texts(content)
    assert not _by_id_type(content, tab.ARXIV_EXPAND_BTN_TYPE)


def test_empty_category_shows_an_alert(patched_data, monkeypatch):
    _sources(monkeypatch, hf_trending=[_paper("Trend")], all_arxiv=[])
    content, _, _ = tab._arxiv_category_update(tab.ARXIV_TABS_ID, f"{tab.ARXIV_TAB_ID_PREFIX}all_arxiv", None)
    assert f"No papers available for {tab.ARXIV_SOURCES_CONFIG['all_arxiv']['name']}." in _texts(content)


def test_unknown_tab_id_falls_back_to_the_first_category(patched_data, monkeypatch):
    _sources(monkeypatch, hf_trending=[_paper("Trend")], all_arxiv=[_paper("All 0"), _paper("All 1")])
    assert tab._arxiv_source_key("arxiv-tab-nope") == "hf_trending"
    assert tab._arxiv_source_key(None) == "hf_trending"
    assert tab._arxiv_source_key(f"{tab.ARXIV_TAB_ID_PREFIX}all_arxiv") == "all_arxiv"
    content, _, placeholder = tab._arxiv_category_update(tab.ARXIV_SEARCH_ID, "arxiv-tab-nope", "")
    assert len(_by_id_type(content, tab.ARXIV_EXPAND_BTN_TYPE)) == 1
    assert placeholder is dash.no_update


def test_category_controller_is_idle_on_insertion(patched_data):
    app = dash.Dash("test-arxiv-category")
    tab.register_arxiv_callbacks(app)

    (entry,) = _listening(app, tab.ARXIV_TABS_ID, "active_tab", f"{tab.ARXIV_CONTENT_ID}.children")
    assert entry["prevent_initial_call"] is True  # the layout already carries the open category's table
    assert any(r.get("id") == tab.ARXIV_SEARCH_ID and r.get("property") == "value" for r in entry["inputs"])
    # The controller also answers for the search box: its value is cleared and its placeholder renamed on a switch
    assert f"{tab.ARXIV_SEARCH_ID}.value" in entry["output"] and f"{tab.ARXIV_SEARCH_ID}.placeholder" in entry["output"]
    # One controller for all the categories: nothing else listens to the bar or to the box's value
    assert len(_listening(app, tab.ARXIV_TABS_ID, "active_tab")) == 1
    assert len(_listening(app, tab.ARXIV_SEARCH_ID, "value")) == 1


def test_clear_button_empties_the_search_box(patched_data):
    app = dash.Dash("test-arxiv-clear")
    tab.register_arxiv_callbacks(app)

    (entry,) = _listening(app, f"{tab.ARXIV_SEARCH_ID}-clear", "n_clicks", f"{tab.ARXIV_SEARCH_ID}.value")
    assert entry["prevent_initial_call"] is True
    assert entry["output"].startswith(f"{tab.ARXIV_SEARCH_ID}.value@")  # allow_duplicate: the controller owns the plain output
    clear = app.callback_map[next(k for k in app.callback_map if k.startswith(f"{tab.ARXIV_SEARCH_ID}.value@"))]["callback"].__wrapped__
    assert clear(1) == ""
    assert clear(0) is dash.no_update
