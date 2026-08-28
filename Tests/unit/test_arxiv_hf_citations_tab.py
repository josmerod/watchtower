"""Render tests for the 📝 Citas column in the 🔥 HF Trending subtab (T-058).

Fixture-based — monkeypatches the tab's data loader, never reads data/ files
and never touches the network.
"""

import pytest

from src.web.dashboard.components import arxiv_research_tab as tab


def _paper(title, upvotes=10, **extra):
    record = {
        "source": "hf_daily_papers",
        "id": f"https://arxiv.org/abs/2608.{1000 + upvotes}",
        "link": f"https://huggingface.co/papers/2608.{1000 + upvotes}",
        "title": title,
        "authors": ["Ana", "Bob"],
        "published": "2026-08-25T00:00:00.000Z",
        "summary": "abstract",
        "upvotes": upvotes,
    }
    record.update(extra)
    return record


def _walk(node):
    """Yield every node of a Dash component tree (components and raw strings)."""
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


def _hrefs(layout):
    return [href for href in (getattr(n, "href", None) for n in _walk(layout)) if href]


@pytest.fixture
def patched_data(monkeypatch):
    """Freeze the tab's data sources so tests are hermetic."""
    monkeypatch.setattr(tab, "get_trending_items_map", lambda: {})
    holder = {}

    def _set(papers, source_key="hf_trending"):
        holder["data"] = {source_key: papers}
        monkeypatch.setattr(tab, "get_all_arxiv_data", lambda: holder["data"])

    return _set


def test_citas_column_renders_with_citation_data(patched_data):
    papers = [
        _paper("Paper With Counts", upvotes=30, citation_count=1284, citation_source="title", citation_doi="10.1145/3292500.3330701"),
        _paper("Paper Without Counts", upvotes=20),
    ]
    patched_data(papers)
    layout = tab.create_arxiv_category_tab_content("hf_trending")

    texts = _texts(layout)
    assert "📝 Citas" in texts
    assert "📝 1,284" in texts  # count rendered with a thousands separator
    assert "—" in texts  # absent data degrades to an em dash, not an error
    assert "https://doi.org/10.1145/3292500.3330701" in _hrefs(layout)  # badge links to the matched DOI


def test_citas_column_renders_fine_without_field(patched_data):
    patched_data([_paper("Fresh Preprint", upvotes=5), _paper("Another One", upvotes=4)])
    layout = tab.create_arxiv_category_tab_content("hf_trending")

    texts = _texts(layout)
    assert "📝 Citas" in texts  # header stays stable
    assert "—" in texts
    assert not any("📝" in t and t != "📝 Citas" for t in texts)  # no bogus badges


def test_other_subtabs_do_not_get_citas_column(patched_data):
    papers = [_paper("Regular Paper", upvotes=9, citation_count=50, citation_source="title", citation_doi="10.1/x")]
    patched_data(papers, source_key="all_arxiv")
    layout = tab.create_arxiv_category_tab_content("all_arxiv")

    texts = _texts(layout)
    assert "📝 Citas" not in texts
    assert "Published Date" in texts


def test_render_citation_cell_guards_bad_values():
    assert tab.citation_count_display({"citation_count": -3}) is None
    assert tab.citation_count_display({"citation_count": True}) is None  # bools are not counts
    assert tab.citation_count_display({"citation_count": "12"}) is None
    assert tab.citation_count_display({}) is None
    assert tab.citation_count_display({"citation_count": 0}) == 0  # a real zero from a matched record

    cell = tab.render_citation_cell({"citation_count": 0, "citation_source": "title"})
    assert "📝 0" in _texts(cell)


def test_citation_cell_without_doi_has_no_link():
    cell = tab.render_citation_cell({"citation_count": 12, "citation_source": "title"})
    assert "📝 12" in _texts(cell)
    assert _hrefs(cell) == []
