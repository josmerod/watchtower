"""Unit tests for T-053: ⭐ saved-items extension to News / Tech Radar / Markets.

Covers the shared saved-items module extensions (registry, button builder,
toggle callback factory), the per-tab renderers marking already-saved items,
and the Knowledge Garden delegation — fixtures only, no external services.
"""

import json

import dash
import pytest

from src.web.dashboard.components import markets_tab, news_tab, saved_items, tech_radar_tab
from src.web.dashboard.components.knowledge_garden_tab import _render_saved_subtab, _save_button as kg_save_button

# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #


@pytest.fixture
def clean_saved_file(tmp_path, monkeypatch):
    """Point the saved-items store at a temp file with a clean registry."""
    fake = tmp_path / "saved_items.json"
    monkeypatch.setattr(saved_items, "SAVED_FILE", fake)
    saved_items.SAVE_CANDIDATES.clear()
    yield fake
    saved_items.SAVE_CANDIDATES.clear()


def _buttons_by_type(root, btn_type):
    """Collect every component whose pattern id matches ``btn_type``."""
    found = []
    stack = [root]
    while stack:
        node = stack.pop()
        if not isinstance(node, str) and isinstance(getattr(node, "id", None), dict) and node.id.get("type") == btn_type:
            found.append(node)
        children = getattr(node, "children", None)
        if children is None:
            continue
        if isinstance(children, (list, tuple)):
            stack.extend(children)
        elif not isinstance(children, str):
            stack.append(children)
    return found


_NEWS_ARTICLE_SAVED = {"title": "Llama 4 is out", "url": "http://example.com/llama4", "source_display_name": "TechCrunch", "published": "2026-08-20T10:00:00"}
_NEWS_ARTICLE_FRESH = {"title": "Rust 2.0 announced", "url": "http://example.com/rust2", "source_display_name": "Ars Technica", "published": "2026-08-21T09:00:00"}

_RADAR_FILE = "news/google_ai_blog_latest.json"
_RADAR_ARTICLE_SAVED = {"title": "Gemini 3 released", "link": "http://example.com/gemini3", "published": "2026-08-19T00:00:00"}
_RADAR_ARTICLE_FRESH = {"title": "TPU v8 details", "link": "http://example.com/tpu8", "published": "2026-08-18T00:00:00"}

_COIN = {"id": "bitcoin", "rank": 1, "name": "Bitcoin", "symbol": "BTC", "price_usd": 79000.0, "change_24h_pct": 1.0, "change_7d_pct": -2.0, "market_cap_usd": 1.6e12, "volume_24h_usd": 3e10, "ath_change_pct": -36.0}


# --------------------------------------------------------------------------- #
# Shared module: registry, payload shape, toggle response
# --------------------------------------------------------------------------- #


class TestSharedSavedItems:
    def test_save_button_registers_candidate_with_tab(self, clean_saved_file):
        item = {"url": "http://example.com/a", "title": "A", "source": "src"}
        btn = saved_items.save_button(item, "news-save-btn", tab="news")
        h = saved_items.item_hash("http://example.com/a", "A")
        assert btn.id == {"type": "news-save-btn", "hash": h}
        assert saved_items.SAVE_CANDIDATES[h]["tab"] == "news"
        assert btn.children == "☆" and btn.color == "outline-secondary"

    def test_toggle_payload_shape_includes_tab(self, clean_saved_file):
        item = {"url": "http://example.com/a", "title": "A", "source": "TechCrunch", "tab": "news"}
        saved_items.toggle_saved(item)
        record = json.loads(clean_saved_file.read_text(encoding="utf-8"))[0]
        assert set(record) == {"hash", "title", "url", "source", "saved_at", "tab"}
        assert record["tab"] == "news" and record["title"] == "A"

    def test_lookup_candidate_file_first_registry_fallback(self, clean_saved_file):
        saved_items.toggle_saved({"url": "http://example.com/s", "title": "S", "tab": "news"})
        h_saved = saved_items.item_hash("http://example.com/s", "S")
        # Saved file wins (record is complete there)
        assert saved_items.lookup_candidate(h_saved)["tab"] == "news"
        # Unsaved item: registry fallback after a render registered it
        saved_items.save_button({"url": "http://example.com/f", "title": "F"}, "kg-save-btn", tab="knowledge_garden")
        h_fresh = saved_items.item_hash("http://example.com/f", "F")
        assert saved_items.lookup_candidate(h_fresh)["tab"] == "knowledge_garden"
        assert saved_items.lookup_candidate("no-such-hash") is None

    def test_toggle_response_flips_and_noops(self, clean_saved_file):
        h = saved_items.save_button({"url": "http://example.com/t", "title": "T"}, "markets-save-btn", tab="markets").id["hash"]
        assert saved_items.toggle_response(h) == ("★", "warning", "Quitar de guardados")
        assert saved_items.toggle_response(h) == ("☆", "outline-secondary", "Guardar para luego")
        assert saved_items.load_saved() == []
        unknown = saved_items.toggle_response("deadbeef")
        assert all(result is dash.no_update for result in unknown)

    def test_same_item_starred_from_two_tabs_shares_one_record(self, clean_saved_file):
        h_news = saved_items.save_button({"url": "http://example.com/dup", "title": "Dup"}, "news-save-btn", tab="news").id["hash"]
        h_radar = saved_items.save_button({"link": "http://example.com/dup", "title": "Dup"}, "tech-radar-save-btn", tab="tech_radar").id["hash"]
        assert h_news == h_radar  # url/link normalize to the same key
        saved_items.toggle_response(h_news)  # star from News
        assert len(saved_items.load_saved()) == 1
        saved_items.toggle_response(h_radar)  # unstar via the radar button
        assert saved_items.load_saved() == []

    def test_register_save_toggle_callback_registers_one_callback_per_type(self):
        app = dash.Dash("test-saved-toggle")
        saved_items.register_save_toggle_callback(app, "news-save-btn")
        saved_items.register_save_toggle_callback(app, "markets-save-btn")
        keys = " ".join(app.callback_map.keys())
        assert "news-save-btn" in keys and "markets-save-btn" in keys


# --------------------------------------------------------------------------- #
# News: "🔎 Global" results only
# --------------------------------------------------------------------------- #


class TestNewsGlobalSave:
    def test_registry_accepts_news_extractor(self, clean_saved_file):
        news_tab._build_global_results_table([dict(_NEWS_ARTICLE_FRESH)], "rust")
        h = saved_items.item_hash(_NEWS_ARTICLE_FRESH["url"], _NEWS_ARTICLE_FRESH["title"])
        assert saved_items.SAVE_CANDIDATES[h]["tab"] == "news"

    def test_global_table_marks_saved_items(self, clean_saved_file):
        saved_items.toggle_saved({**_NEWS_ARTICLE_SAVED, "tab": "news"})
        table = news_tab._build_global_results_table([dict(_NEWS_ARTICLE_SAVED), dict(_NEWS_ARTICLE_FRESH)], "")
        buttons = _buttons_by_type(table, "news-save-btn")
        assert len(buttons) == 2
        by_hash = {b.id["hash"]: b for b in buttons}
        saved_btn = by_hash[saved_items.item_hash(_NEWS_ARTICLE_SAVED["url"], _NEWS_ARTICLE_SAVED["title"])]
        fresh_btn = by_hash[saved_items.item_hash(_NEWS_ARTICLE_FRESH["url"], _NEWS_ARTICLE_FRESH["title"])]
        assert saved_btn.children == "★" and saved_btn.color == "warning"
        assert fresh_btn.children == "☆" and fresh_btn.color == "outline-secondary"

    def test_per_source_tables_have_no_star_buttons(self, clean_saved_file):
        # Top Tech table builder (shared by the per-source style tables) stays star-free
        table = news_tab._build_news_table([dict(_NEWS_ARTICLE_FRESH)], None)
        assert _buttons_by_type(table, "news-save-btn") == []


# --------------------------------------------------------------------------- #
# Tech Radar: unified "🔄 Todos" feed rows only
# --------------------------------------------------------------------------- #


class TestTechRadarUnifiedSave:
    def test_registry_accepts_radar_extractor(self, clean_saved_file):
        tech_radar_tab._render_unified_feed(all_data={_RADAR_FILE: [dict(_RADAR_ARTICLE_FRESH)]})
        h = saved_items.item_hash(_RADAR_ARTICLE_FRESH["link"], _RADAR_ARTICLE_FRESH["title"])
        assert saved_items.SAVE_CANDIDATES[h]["tab"] == "tech_radar"

    def test_unified_feed_marks_saved_items(self, clean_saved_file):
        saved_items.toggle_saved({**_RADAR_ARTICLE_SAVED, "tab": "tech_radar"})
        feed = tech_radar_tab._render_unified_feed(all_data={_RADAR_FILE: [dict(_RADAR_ARTICLE_SAVED), dict(_RADAR_ARTICLE_FRESH)]})
        buttons = _buttons_by_type(feed, "tech-radar-save-btn")
        assert len(buttons) == 2
        by_hash = {b.id["hash"]: b for b in buttons}
        saved_btn = by_hash[saved_items.item_hash(_RADAR_ARTICLE_SAVED["link"], _RADAR_ARTICLE_SAVED["title"])]
        fresh_btn = by_hash[saved_items.item_hash(_RADAR_ARTICLE_FRESH["link"], _RADAR_ARTICLE_FRESH["title"])]
        assert saved_btn.children == "★" and saved_btn.color == "warning"
        assert fresh_btn.children == "☆" and fresh_btn.color == "outline-secondary"

    def test_per_source_columns_and_stack_rows_have_no_star_buttons(self, clean_saved_file):
        all_data = {_RADAR_FILE: [dict(_RADAR_ARTICLE_FRESH)]}
        card_source = next(s for s in tech_radar_tab.RADAR_SOURCES if s["key"] == "google_ai")
        section = tech_radar_tab._render_source_section(card_source, all_data=all_data)
        assert _buttons_by_type(section, "tech-radar-save-btn") == []

        stack_source = next(s for s in tech_radar_tab.RADAR_SOURCES if s["key"] == "mi_stack")
        release = {"repo": "immich", "title": "immich v2.0", "link": "http://example.com/immich", "published": "2026-08-01"}
        stack_files = {f: [dict(release)] for f in tech_radar_tab._source_files(stack_source)}
        stack_section = tech_radar_tab._render_stack_section(stack_source, all_data=stack_files)
        assert _buttons_by_type(stack_section, "tech-radar-save-btn") == []


# --------------------------------------------------------------------------- #
# Markets: main table rows
# --------------------------------------------------------------------------- #


class TestMarketsSave:
    def test_coin_save_record_payload(self):
        record = markets_tab._coin_save_record(_COIN)
        assert record == {"title": "Bitcoin (BTC)", "url": "https://www.coingecko.com/en/coins/bitcoin", "source": "Markets (CoinGecko)"}

    def test_registry_accepts_markets_extractor(self, clean_saved_file, monkeypatch):
        monkeypatch.setattr(markets_tab, "_load_coins", lambda: [dict(_COIN)])
        markets_tab.render_markets_tab()
        h = saved_items.item_hash("https://www.coingecko.com/en/coins/bitcoin", "Bitcoin (BTC)")
        assert saved_items.SAVE_CANDIDATES[h]["tab"] == "markets"

    def test_markets_table_marks_saved_coins(self, clean_saved_file, monkeypatch):
        monkeypatch.setattr(markets_tab, "_load_coins", lambda: [dict(_COIN)])
        layout = markets_tab.render_markets_tab()
        buttons = _buttons_by_type(layout, "markets-save-btn")
        assert len(buttons) == 1 and buttons[0].children == "☆"

        saved_items.toggle_saved({**markets_tab._coin_save_record(_COIN), "tab": "markets"})
        layout = markets_tab.render_markets_tab()
        buttons = _buttons_by_type(layout, "markets-save-btn")
        assert buttons[0].children == "★" and buttons[0].color == "warning"

    def test_register_markets_callbacks_wires_toggle(self):
        app = dash.Dash("test-markets")
        markets_tab.register_markets_callbacks(app)
        assert any("markets-save-btn" in key for key in app.callback_map)


# --------------------------------------------------------------------------- #
# Knowledge Garden: delegation stays intact
# --------------------------------------------------------------------------- #


class TestKnowledgeGardenDelegation:
    def test_kg_save_button_delegates_to_shared_builder(self, clean_saved_file):
        article = {"url": "http://example.com/kg", "title": "KG item", "source": "LessWrong"}
        btn = kg_save_button(article)
        h = saved_items.item_hash("http://example.com/kg", "KG item")
        assert btn.id == {"type": "kg-save-btn", "hash": h}
        assert saved_items.SAVE_CANDIDATES[h]["tab"] == "knowledge_garden"
        assert btn.children == "☆" and btn.color == "outline-secondary"

    def test_saved_subtab_shows_origin_tab_badge(self, clean_saved_file):
        record = {
            "hash": saved_items.item_hash("http://example.com/x", "Cross tab"),
            "title": "Cross tab",
            "url": "http://example.com/x",
            "source": "TechCrunch",
            "saved_at": "2026-08-28T10:00:00",
            "tab": "news",
        }
        clean_saved_file.write_text(json.dumps([record], ensure_ascii=False), encoding="utf-8")
        subtab = _render_saved_subtab()
        assert "Cross tab" in str(subtab)
        assert "news" in str(subtab)  # origin badge distinguishes tabs
