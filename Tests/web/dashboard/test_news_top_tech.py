"""Tests for the News "Top Tech" subtab M4/M5 features (spec 01).

Covers the three T-064 deliverables with fixtures only (no network, no real
data/ files):
- M5 dedup grouping: the same story from 2 sources collapses to 1 row with a
  "N ocultos en M grupos" summary line.
- M4 pagination math: e.g. 73 items at 25/page = 3 pages, 23 on the last one.
- Render smoke: the Top Tech controls (selector, toggle, page store) exist in
  the layout and every previously load-bearing id is preserved.
"""

import pytest

from src.web.dashboard.components import news_tab
from src.web.dashboard.components.duplicate_filter import create_duplicate_toggle
from src.web.dashboard.deduplication_utils import (
    annotate_duplicate_groups,
    filter_duplicates,
    format_duplicate_summary,
    get_duplicate_summary,
    get_story_group_key,
    normalize_story_key,
)

# --- Fixtures -----------------------------------------------------------------


@pytest.fixture
def two_source_fixture():
    """The same story published by TechCrunch and VentureBeat plus one unique story."""
    return [
        {"title": "OpenAI launches new model", "url": "https://techcrunch.com/1", "source": "TechCrunch", "published": "2026-08-27T10:00:00+00:00"},
        {"title": "OpenAI Launches New Model!", "url": "https://venturebeat.com/1", "source": "VentureBeat", "published": "2026-08-27T09:00:00+00:00"},
        {"title": "Unrelated Apple story", "url": "https://techcrunch.com/2", "source": "TechCrunch", "published": "2026-08-26T10:00:00+00:00"},
    ]


@pytest.fixture
def stub_news_data():
    """Minimal data for the 4 Top Tech sources (fixtures only, never real files)."""
    return {
        "techcrunch": [{"title": f"TechCrunch story {i}", "url": f"https://techcrunch.com/{i}", "source": "TechCrunch", "published": f"2026-08-2{7 - i // 10}T10:00:00+00:00"} for i in range(30)],
        "venturebeat": [
            {"title": "TechCrunch story 0", "url": "https://venturebeat.com/0", "source": "VentureBeat", "published": "2026-08-27T09:00:00+00:00"},
            {"title": "VentureBeat exclusive", "url": "https://venturebeat.com/x", "source": "VentureBeat", "published": "2026-08-25T09:00:00+00:00"},
        ],
        "arstechnica": [{"title": f"Ars story {i}", "url": f"https://arstechnica.com/{i}", "source": "Ars Technica", "published": "2026-08-24T09:00:00+00:00"} for i in range(20)],
        "kagi_ai": [],
    }


def _walk(component):
    """Yield every Dash component in a layout tree (children may be str/None/component/list)."""
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        if hasattr(child, "to_plotly_json"):
            yield from _walk(child)


def _collect_ids(component):
    """Recursively collect every component id in a Dash layout tree."""
    ids = []
    for item in _walk(component):
        component_id = getattr(item, "id", None)
        if isinstance(component_id, str):
            ids.append(component_id)
    return ids


# --- M5: dedup grouping -------------------------------------------------------


class TestDuplicateGrouping:
    """Cross-source duplicate detection via annotate_duplicate_groups."""

    def test_same_story_two_sources_one_shown(self, two_source_fixture):
        """Same story from 2 sources -> 1 row shown + '1 oculto en 1 grupo'."""
        annotated = annotate_duplicate_groups(two_source_fixture)
        summary = get_duplicate_summary(annotated)

        assert summary["duplicate_items"] == 1
        assert summary["duplicate_groups"] == 1
        assert summary["unique_items"] == 2

        visible = filter_duplicates(annotated, show_duplicates=False)
        assert len(visible) == 2  # 1 shown for the dup story + 1 unique story
        assert format_duplicate_summary(summary) == "1 oculto en 1 grupo"

    def test_show_duplicates_returns_everything(self, two_source_fixture):
        """Toggle ON keeps both copies of the story."""
        annotated = annotate_duplicate_groups(two_source_fixture)
        visible = filter_duplicates(annotated, show_duplicates=True)
        assert len(visible) == 3

    def test_first_in_list_order_stays_original(self, two_source_fixture):
        """The newest item (list is date-desc) is the original, later ones are duplicates."""
        annotated = annotate_duplicate_groups(two_source_fixture)
        original, duplicate = annotated[0], annotated[1]

        assert original["is_duplicate"] is False
        assert duplicate["is_duplicate"] is True
        assert original["duplicate_group_id"] == duplicate["duplicate_group_id"]

    def test_input_list_not_mutated(self, two_source_fixture):
        """Annotate works on copies: cached datasets never gain dedup flags."""
        annotated = annotate_duplicate_groups(two_source_fixture)
        assert annotated[0] is not two_source_fixture[0]
        assert "is_duplicate" not in two_source_fixture[0]
        assert "duplicate_group_id" not in two_source_fixture[1]

    def test_group_of_three_hides_two(self):
        """3 copies of one story -> '2 ocultos en 1 grupo'."""
        data = [{"title": "Big launch", "url": f"https://src{i}.com/1", "source": f"src{i}"} for i in range(3)] + [{"title": "Other story", "url": "https://src0.com/2", "source": "src0"}]
        annotated = annotate_duplicate_groups(data)
        summary = get_duplicate_summary(annotated)

        assert summary["duplicate_items"] == 2
        assert summary["duplicate_groups"] == 1
        assert format_duplicate_summary(summary) == "2 ocultos en 1 grupo"

    def test_two_groups_plural_summary(self):
        """2 separate dup pairs -> '2 ocultos en 2 grupos'."""
        data = [
            {"title": "Story A", "url": "https://a/1"},
            {"title": "story a", "url": "https://b/1"},
            {"title": "Story B", "url": "https://a/2"},
            {"title": "STORY B!!", "url": "https://b/2"},
        ]
        annotated = annotate_duplicate_groups(data)
        summary = get_duplicate_summary(annotated)

        assert summary["duplicate_items"] == 2
        assert summary["duplicate_groups"] == 2
        assert format_duplicate_summary(summary) == "2 ocultos en 2 grupos"

    def test_no_duplicates_summary(self):
        """Zero duplicates -> 'sin duplicados'."""
        data = [{"title": "A", "url": "https://a"}, {"title": "B", "url": "https://b"}]
        summary = get_duplicate_summary(annotate_duplicate_groups(data))
        assert summary["duplicate_items"] == 0
        assert format_duplicate_summary(summary) == "sin duplicados"

    def test_story_key_normalization(self):
        """Punctuation/case differences collapse to the same story key."""
        assert normalize_story_key("OpenAI launches GPT-5!") == normalize_story_key("openai launches gpt 5")
        assert get_story_group_key({"title": "Hola, Mundo!"}) == "hola mundo"
        assert get_story_group_key({"name": "Fallback Name"}) == "fallback name"
        assert get_story_group_key({"url": "https://no-title"}) is None

    def test_untitled_items_never_grouped(self):
        """Items without titles are all kept (no key -> no grouping)."""
        data = [{"url": "https://a"}, {"url": "https://b"}]
        annotated = annotate_duplicate_groups(data)
        assert len(filter_duplicates(annotated, show_duplicates=False)) == 2


# --- M4: pagination math ------------------------------------------------------


class TestPaginationMath:
    """compute_total_pages / slice_page_items slicing."""

    def test_73_items_at_25(self):
        """73 items, size 25 -> 3 pages, last page has 23 items."""
        items = list(range(73))
        assert news_tab.compute_total_pages(len(items), 25) == 3
        assert len(news_tab.slice_page_items(items, 1, 25)) == 25
        assert len(news_tab.slice_page_items(items, 2, 25)) == 25
        assert len(news_tab.slice_page_items(items, 3, 25)) == 23

    def test_exact_multiple_no_extra_page(self):
        """50 items at 25/page -> exactly 2 pages (no empty third page)."""
        assert news_tab.compute_total_pages(50, 25) == 2

    def test_empty_dataset_is_one_page(self):
        """0 items -> still 1 page so the pager never renders page 0."""
        assert news_tab.compute_total_pages(0, 50) == 1

    def test_non_positive_per_page_raises(self):
        """A bogus page size must raise, never loop or divide by zero."""
        with pytest.raises(ValueError):
            news_tab.compute_total_pages(10, 0)


# --- Shared Top Tech view renderer ---------------------------------------------


class TestRenderTopTechView:
    """_render_top_tech_view: summary line + pager composition."""

    @pytest.fixture(autouse=True)
    def _stub_trends(self, monkeypatch):
        """Trend badges come from watcher data; stub the map so no data/ files are read."""
        monkeypatch.setattr(news_tab, "get_trending_items_map", lambda: {})

    def test_summary_line_when_duplicates_hidden(self, two_source_fixture):
        """Default state (toggle OFF) renders '1 oculto en 1 grupo' above the table."""
        children, page = news_tab._render_top_tech_view(two_source_fixture, show_duplicates=False)
        rendered = str(children)
        assert "1 oculto en 1 grupo" in rendered
        assert page == 1

    def test_no_summary_line_when_duplicates_shown(self, two_source_fixture):
        """Toggle ON: everything is visible, no 'ocultos' line."""
        children, _page = news_tab._render_top_tech_view(two_source_fixture, show_duplicates=True)
        rendered = str(children)
        assert "oculto" not in rendered
        assert "sin duplicados" not in rendered  # no noise when showing all

    def test_pager_appears_beyond_one_page(self):
        """60 unique items at 25/page -> pager with 'Página 1 de 3' and prev/next buttons."""
        items = [{"title": f"Story {i}", "url": f"https://x/{i}", "source_display_name": "S", "published": "2026-08-27T00:00:00+00:00"} for i in range(60)]
        children, page = news_tab._render_top_tech_view(items, per_page=25, page=1)
        rendered = str(children)

        assert "Página 1 de 3 · 60 items" in rendered
        assert page == 1

    def test_page_clamped_to_range(self):
        """Asking for page 99 of 3 lands on page 3."""
        items = [{"title": f"Story {i}", "url": f"https://x/{i}"} for i in range(60)]
        children, page = news_tab._render_top_tech_view(items, per_page=25, page=99)
        assert page == 3
        assert "Página 3 de 3" in str(children)

    def test_no_pager_on_single_page(self, two_source_fixture):
        """One page of content -> no pager, no 'Página' text."""
        children, _page = news_tab._render_top_tech_view(two_source_fixture)
        assert "Página" not in str(children)

    def test_table_rows_keep_read_state_hash(self, two_source_fixture):
        """Rows still carry data-item-hash so read_state.js keeps working."""
        children, _page = news_tab._render_top_tech_view(two_source_fixture)
        assert "data-item-hash" in str(children)


# --- Toggle control helper -----------------------------------------------------


class TestDuplicateToggle:
    """duplicate_filter.create_duplicate_toggle: layout-only switch."""

    def test_default_off_with_expected_id(self):
        """Default is OFF (duplicates hidden) and uses the component-id convention."""
        toggle = create_duplicate_toggle("news-toptech")
        assert toggle.id == "news-toptech-show-duplicates"
        assert toggle.value == []
        assert toggle.switch is True

    def test_checked_state(self):
        """checked=True pre-selects the switch."""
        toggle = create_duplicate_toggle("x", checked=True)
        assert toggle.value == [1]


# --- Layout smoke + controller wiring ------------------------------------------


class TestTopTechLayoutSmoke:
    """render_news_tab with stubbed data: control ids present, legacy ids preserved."""

    @pytest.fixture(autouse=True)
    def _stub_data(self, monkeypatch, stub_news_data):
        """No data/ files touched: data loader and trend map are stubbed."""
        monkeypatch.setattr(news_tab, "get_all_news_data", lambda: stub_news_data)
        monkeypatch.setattr(news_tab, "get_trending_items_map", lambda: {})

    def test_top_tech_controls_present(self):
        """The Top Tech subtab ships the M4 selector, M5 toggle and page store."""
        layout = news_tab.render_news_tab()
        ids = _collect_ids(layout)

        assert "news-toptech-items-per-page" in ids
        assert "news-toptech-show-duplicates" in ids
        assert "news-toptech-page" in ids
        assert f"{news_tab.TOP_TECH_SEARCH_ID}-results" in ids

    def test_selector_options_and_default(self):
        """Options are exactly 25/50/100/250 with 50 preselected (spec 01 M4)."""
        layout = news_tab.render_news_tab()
        selector = next(item for item in _walk(layout) if getattr(item, "id", None) == "news-toptech-items-per-page")

        assert [opt["value"] for opt in selector.options] == [25, 50, 100, 250]
        assert selector.value == 50
        assert selector.clearable is False

    def test_legacy_ids_preserved(self):
        """Every pre-existing load-bearing id survives the change untouched."""
        layout = news_tab.render_news_tab()
        ids = _collect_ids(layout)
        rendered = str(layout)

        # Grepped by Tests/unit/test_tab_render.py
        for legacy in ("news-global-search-input", "news-mark-all-read", "news-global-results", "news-source-tabs-main", "news-export-download", "news-toggle-hide-read", "news-read-count"):
            assert legacy in ids, f"legacy id lost: {legacy}"
        # Other subtabs keep their generic controller wiring
        assert "news-search-hackernews" in ids
        assert "news-search-hackernews-results" in ids
        assert "news-mark-all-read" in rendered

    def test_single_controller_owns_results(self):
        """Exactly one callback writes the Top Tech results container (Single Callback Pattern)."""
        from dash import Dash

        app = Dash(__name__)
        news_tab.register_news_search_callbacks(app)

        owners = [key for key in app.callback_map if f"{news_tab.TOP_TECH_SEARCH_ID}-results" in key]
        assert len(owners) == 1
        # The page store is written by that same single controller
        assert any("news-toptech-page.data" in key for key in owners)
        # Page size + dedup toggle are Inputs of that controller
        callback_spec = str(app.callback_map[owners[0]].get("inputs", []))
        assert "news-toptech-items-per-page" in callback_spec
        assert "news-toptech-show-duplicates" in callback_spec

    def test_static_layout_deduped_first_page(self):
        """The initial (no-callback) render is already deduped: fixture has 1 cross-source dup."""
        layout = news_tab.render_news_tab()
        rendered = str(layout)

        assert "1 oculto en 1 grupo" in rendered
        # 52 total items, 1 hidden -> 51 visible, capped to the default first page of 50
        assert rendered.count("data-item-hash") == 50


if __name__ == "__main__":
    pytest.main([__file__])
