"""Unit tests for the shared dashboard helpers (spec 15 M1/M2)."""

import time

import pytest
from dash import html

from src.web.dashboard.components.shared.cache import TTLDataCache
from src.web.dashboard.components.shared.table import (
    badges_cell,
    create_refresh_button,
    paginate,
    pagination_controls,
    render_items_table,
    text_cell,
    title_cell,
)


class TestTTLDataCache:
    def test_caches_loader_result(self):
        calls = []

        def loader():
            calls.append(1)
            return {"data": 1}

        cache = TTLDataCache(ttl_seconds=60)
        assert cache.get(loader) == {"data": 1}
        assert cache.get(loader) == {"data": 1}
        assert len(calls) == 1

    def test_force_refresh_bypasses_cache(self):
        calls = []

        def loader():
            calls.append(1)
            return len(calls)

        cache = TTLDataCache(ttl_seconds=60)
        cache.get(loader)
        assert cache.get(loader, force_refresh=True) == 2
        assert len(calls) == 2

    def test_expiry_reloads(self):
        calls = []

        def loader():
            calls.append(1)
            return len(calls)

        cache = TTLDataCache(ttl_seconds=0.05)
        cache.get(loader)
        time.sleep(0.08)
        assert cache.get(loader) == 2
        assert len(calls) == 2

    def test_invalidate_forces_reload(self):
        calls = []

        def loader():
            calls.append(1)
            return "v"

        cache = TTLDataCache(ttl_seconds=60)
        cache.get(loader)
        cache.invalidate()
        cache.get(loader)
        assert len(calls) == 2


class TestRenderItemsTable:
    COLUMNS = [
        {"header": "Title", "cell": lambda item: title_cell(item, "")},
        {"header": "Source", "cell": lambda item: item.get("source", ""), "td_kwargs": {"className": "small"}},
    ]

    def test_empty_items_returns_alert(self):
        result = render_items_table([], self.COLUMNS)
        assert "No entries found" in result.children

    def test_renders_rows_and_headers(self):
        items = [{"title": "A", "url": "http://a", "source": "s1"}, {"title": "B", "source": "s2"}]
        result = render_items_table(items, self.COLUMNS)
        table = result.children if isinstance(result, html.Div) else result
        thead, tbody = table.children
        header_row = thead.children
        headers = [th.children for th in header_row.children]
        assert headers == ["Title", "Source"]
        assert len(tbody.children) == 2

    def test_no_wrap_returns_bare_table(self):
        result = render_items_table([{"title": "A"}], self.COLUMNS, wrap_scroll=False)
        assert not isinstance(result, html.Div)


class TestHelpers:
    def test_title_cell_prefers_first_present_field(self):
        cell = title_cell({"name": "N", "title": "T"}, "")
        assert "T" in str(cell)

    def test_title_cell_fallback_fields(self):
        cell = title_cell({"full_name": "F"}, "")
        assert "F" in str(cell)

    def test_title_cell_subtitle_truncated(self):
        cell = title_cell({"title": "T"}, "", subtitle="x" * 300)
        rendered = str(cell)
        assert "…" in rendered and "xxx" not in rendered[rendered.index("…") :]

    def test_badges_cell_fallback(self):
        cell = badges_cell([])
        assert "General" in str(cell)

    def test_text_cell_na_on_missing(self):
        assert text_cell(None) == "N/A"

    def test_refresh_button_pattern_id(self):
        btn = create_refresh_button("kg", extra={"subtab": "devto"})
        assert btn.id == {"type": "kg-refresh", "tab": "main", "subtab": "devto"}

    def test_paginate_clamps_and_slices(self):
        items = list(range(25))
        page_items, total_pages, page = paginate(items, page=2, per_page=10)
        assert page_items == list(range(10, 20))
        assert total_pages == 3 and page == 2
        _, total_pages, page = paginate(items, page=99, per_page=10)
        assert page == 3
        _, total_pages, page = paginate([], page=1, per_page=10)
        assert total_pages == 1 and page == 1

    def test_pagination_controls_ids_are_pattern_matching(self):
        controls = pagination_controls("kg", page=1, total_pages=5, showing=10, total=50)
        prev_btn = controls.children[0]
        next_btn = controls.children[2]
        assert prev_btn.id == {"type": "kg-page-btn", "dir": "prev"}
        assert next_btn.id == {"type": "kg-page-btn", "dir": "next"}
        assert prev_btn.disabled and not next_btn.disabled

    def test_pagination_controls_disables_next_on_last_page(self):
        controls = pagination_controls("kg", page=5, total_pages=5, showing=10, total=50)
        assert controls.children[2].disabled


if __name__ == "__main__":
    pytest.main([__file__])
