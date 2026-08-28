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
