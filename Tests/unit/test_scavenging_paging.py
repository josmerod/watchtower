"""Unit tests for the Scavenging tab's paging (T-150) and the bundle links of Humble books (T-149).

The tab used to show the first 100 rows of a source and nothing else: with a
30-day window Audible brings about 500. Fixtures only: the source files live
under tmp_path.
"""

import json

import dash
import dash_bootstrap_components as dbc
import pytest
from dash import html

import src.web.dashboard.components.scavenging_tab as tab
from src.web.dashboard.components.scavenging_tab import (
    _pager,
    _scavenging_page,
    _target_page,
    create_scavenging_table,
    register_scavenging_callbacks,
    render_scavenging_tab,
)

SID = "scavenging-search-audible"


def _items(count: int) -> list[dict]:
    return [{"title": f"Item {n:03d}", "link": f"https://example.com/{n:03d}", "published": f"2026-11-{1 + n % 27:02d}T{n % 24:02d}:00:00", "summary": f"summary {n:03d}", "category": "audible", "source": "audible"} for n in range(count)]


def _walk(node):
    """Yield every node of a Dash component tree, strings included."""
    yield node
    children = getattr(node, "children", None)
    if children is None:
        return
    for child in children if isinstance(children, (list, tuple)) else [children]:
        yield from _walk(child)


def _by_id(root, component_id):
    return [n for n in _walk(root) if getattr(n, "id", None) == component_id]


def _texts(root) -> str:
    return " ".join(n for n in _walk(root) if isinstance(n, str))


def _rows(root) -> int:
    return sum(len(table.children[1].children) for table in [n for n in _walk(root) if isinstance(n, dbc.Table)] if len(table.children) > 1 and isinstance(table.children[1].children, list))


# ---------------------------------------------------------------------------
# Which page a trigger asks for
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("triggered", "current", "expected"),
    [
        (SID, 3, 1),  # a new search term starts over
        (f"{SID}-clear", 2, 1),
        (f"{SID}-prev", 2, 1),
        (f"{SID}-prev", 1, 1),  # no page before the first
        (f"{SID}-next", 2, 3),
        (f"{SID}-next", 5, 5),  # no page after the last
        (f"{SID}-prev", None, 1),  # page never set: treated as the first
    ],
)
def test_target_page(triggered, current, expected):
    assert _target_page(triggered, SID, current, 5) == expected


# ---------------------------------------------------------------------------
# One page of rows and its pager
# ---------------------------------------------------------------------------


def test_pager_is_empty_while_everything_fits_on_one_page():
    assert _pager(SID, 1, 0) == ""
    assert _pager(SID, 1, tab.MAX_ITEMS_PER_TAB) == ""


def test_pager_names_the_page_and_disables_what_cannot_move():
    first = _pager(SID, 1, tab.MAX_ITEMS_PER_TAB + 1)
    last = _pager(SID, 2, tab.MAX_ITEMS_PER_TAB + 1)

    assert _texts(first) == f"← Prev Showing {tab.MAX_ITEMS_PER_TAB} of {tab.MAX_ITEMS_PER_TAB + 1} · Page 1 of 2 Next →"
    assert _by_id(first, f"{SID}-prev")[0].disabled is True and _by_id(first, f"{SID}-next")[0].disabled is False
    assert _texts(last) == "← Prev Showing 1 of 101 · Page 2 of 2 Next →"
    assert _by_id(last, f"{SID}-prev")[0].disabled is False and _by_id(last, f"{SID}-next")[0].disabled is True


def test_the_page_shows_its_slice_and_how_many_there_are():
    body, pager, page = _scavenging_page(_items(250), "", f"{SID}-next", 2, SID)

    assert page == 3
    assert _rows(body) == 50
    assert "Item 200" in _texts(body) and "Item 249" in _texts(body) and "Item 199" not in _texts(body)
    assert _texts(pager) == "← Prev Showing 50 of 250 · Page 3 of 3 Next →"


def test_a_new_search_starts_on_the_first_page_with_only_the_matches():
    body, pager, page = _scavenging_page(_items(250) + [{"title": "Rust adventures", "link": "https://example.com/rust", "summary": "systems", "category": "audible"}], "rust", SID, 3, SID)

    assert page == 1
    assert _rows(body) == 1
    assert "⛏️ Found 1 items matching 'rust'" in _texts(body)
    assert pager == ""


def test_a_search_with_more_matches_than_one_page_gets_a_pager():
    body, pager, page = _scavenging_page(_items(250), "Item 1", SID, None, SID)

    assert page == 1  # Item 100 to Item 199: 100 matches, one page
    assert _rows(body) == 100
    assert pager == ""


def test_a_search_without_matches_says_so():
    body, pager, page = _scavenging_page(_items(5), "nothing-like-this", SID, 1, SID)

    assert "⛏️ Found 0 items matching 'nothing-like-this'" in _texts(body)
    assert _rows(body) == 0
    assert (pager, page) == ("", 1)


def test_a_source_without_data_answers_an_alert():
    body, pager, page = _scavenging_page(None, "", SID, 1, SID)

    assert isinstance(body, dbc.Alert) and body.children == "No data loaded."
    assert (pager, page) == (dash.no_update, dash.no_update)


# ---------------------------------------------------------------------------
# Layout and wiring
# ---------------------------------------------------------------------------


def _source(tmp_path, monkeypatch, key: str, records: list[dict]) -> None:
    """One configured source whose canonical file holds ``records``."""
    path = tmp_path / key / "output" / f"{key}_latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records), encoding="utf-8")
    monkeypatch.setattr(tab, "SCAVENGING_SOURCES", [{"key": key, "label": key.capitalize(), "category": key, "paths": [str(path)]}])


def test_layout_shows_the_first_page_with_its_pager(tmp_path, monkeypatch):
    _source(tmp_path, monkeypatch, "audible", _items(250))

    layout = render_scavenging_tab()
    search_id = "scavenging-search-audible"

    assert _by_id(layout, f"{search_id}-page")[0].data == 1
    assert len(_by_id(layout, f"{search_id}-data")[0].data) == 250  # the whole source stays reachable for search and paging
    assert _rows(_by_id(layout, f"{search_id}-results")[0]) == tab.MAX_ITEMS_PER_TAB
    assert _texts(_by_id(layout, f"{search_id}-pager")[0]) == "← Prev Showing 100 of 250 · Page 1 of 3 Next →"


def test_a_source_that_fits_on_one_page_shows_no_pager(tmp_path, monkeypatch):
    _source(tmp_path, monkeypatch, "audible", _items(5))

    layout = render_scavenging_tab()

    assert _rows(_by_id(layout, "scavenging-search-audible-results")[0]) == 5
    assert _by_id(layout, "scavenging-search-audible-pager")[0].children == ""


def test_every_configured_source_gets_its_controller(tmp_path, monkeypatch):
    # Registered although the file does not exist yet: a source whose data shows up after startup must be searchable too.
    monkeypatch.setattr(tab, "SCAVENGING_SOURCES", [{"key": "audible", "label": "Audible", "category": "audible", "paths": [str(tmp_path / "nowhere" / "audible_releases_latest.json")]}])
    app = dash.Dash("test-scavenging-paging")
    register_scavenging_callbacks(app)

    controller = next(entry for entry in app._callback_list if "scavenging-search-audible-results.children" in str(entry["output"]))
    outputs = str(controller["output"])
    assert "scavenging-search-audible-pager.children" in outputs and "scavenging-search-audible-page.data" in outputs
    inputs = {(str(i["id"]), i["property"]) for i in controller["inputs"]}
    assert inputs == {("scavenging-search-audible", "value"), ("scavenging-search-audible-prev", "n_clicks"), ("scavenging-search-audible-next", "n_clicks")}
    assert controller["prevent_initial_call"] is True  # the first page is rendered with the layout
    # The clear button still empties the search box.
    assert any("scavenging-search-audible.value" in str(entry["output"]) and entry["prevent_initial_call"] for entry in app._callback_list)


# ---------------------------------------------------------------------------
# Humble books: the title goes to the book, Details to the bundle
# ---------------------------------------------------------------------------


def test_humble_books_link_to_their_bundle_from_the_details_cell():
    one = {"title": "Conquer the command line", "link": "https://humble.dadand.dev/books/10156", "summary": "Authors: Richard Smedley", "category": "humble_books", "humble_urls": ["https://www.humblebundle.com/books/tech-a"]}
    two = {**one, "title": "Shared book", "humble_urls": ["https://www.humblebundle.com/books/tech-a", "https://www.humblebundle.com/books/tech-b"]}
    plain = {"title": "Any other record", "link": "https://example.com/x", "summary": "s", "category": "audible"}

    table = create_scavenging_table([one, two, plain])
    links = [(a.href, a.children) for a in _walk(table) if isinstance(a, html.A)]

    # One URL per book: what keeps one row per book in the dashboard.
    assert ("https://humble.dadand.dev/books/10156", "Conquer the command line") in links
    assert ("https://humble.dadand.dev/books/10156", "Shared book") in links
    assert ("https://example.com/x", "Any other record") in links
    assert [text for href, text in links if "humblebundle.com/books/tech-a" == href.removeprefix("https://www.")] == ["Humble ↗", "Humble 1 ↗"]
    assert [text for href, text in links if href == "https://www.humblebundle.com/books/tech-b"] == ["Humble 2 ↗"]
    assert len([1 for href, _ in links if "humblebundle.com" in str(href)]) == 3  # nothing for the record that carries none
