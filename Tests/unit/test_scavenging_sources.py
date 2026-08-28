"""Unit tests for the config-driven Scavenging tab sources (T-067).

Covers: canonical-path reads via SCAVENGING_SOURCES, the deprecated
data/scavenging/ legacy fallback when a canonical is missing, adapter
normalization of canonical model dumps, empty-state rendering, and
multi-source rendering. All paths point at tmp_path fixtures — no real
data/ files are touched.
"""

import json
from pathlib import Path

import pytest

import src.web.dashboard.components.scavenging_tab as scavenging_tab
from src.web.dashboard.components.scavenging_tab import (
    _adapt_gumroad_product,
    _adapt_travel_deal,
    discover_categories,
    get_scavenging_data,
    render_scavenging_tab,
)

# --- Fixture payloads ---------------------------------------------------------

# Scavenging display shape (what legacy files and the RSS/audible/humble/epic
# canonical files contain).
RSS_RECORD = {"title": "Nyaa item", "link": "https://nyaa.si/t/1", "published": "2026-08-20T10:00:00+00:00", "summary": "A torrent", "category": "anime", "source": "nyaa"}

# Canonical GumroadProduct dump (data/gumroad_scraper/output/ shape).
GUMROAD_DUMP = {
    "product_id": "p1",
    "name": "Free Ebook",
    "price": "Free",
    "seller": "Seller Co",
    "description": "A free ebook",
    "url": "https://gumroad.com/l/p1",
    "fetched_at": "2026-08-21T09:00:00",
    "parsed_at": "2026-08-21T09:00:05",
}

# Canonical TravelDeal dump (data/viajeros_piratas/output/ shape).
VIAJEROS_DUMP = {
    "deal_id": "vp_1_1",
    "title": "Hotel Maldivas",
    "description": "Viaje a Maldivas",
    "price": 199.0,
    "currency": "EUR",
    "raw_price": "Desde 199€",
    "category": "hotel",
    "url": "https://www.viajerospiratas.es/oferta/1",
    "published_at": "2026-08-19T08:00:00",
    "fetched_at": "2026-08-20T08:00:00",
    "parsed_at": "2026-08-20T08:01:00",
    "page_number": 1,
    "position": 1,
    "source": "viajeros_piratas",
}


def _write_json(path, payload) -> str:
    """Write a JSON list payload and return the string path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def _patch_sources(monkeypatch, sources) -> None:
    """Replace the module-level SCAVENGING_SOURCES with test entries."""
    monkeypatch.setattr(scavenging_tab, "SCAVENGING_SOURCES", sources)


# --- Discovery + fallback -----------------------------------------------------


def test_discover_prefers_canonical_over_legacy_fallback(tmp_path, monkeypatch):
    """Canonical wins when both canonical and legacy files exist."""
    canonical = _write_json(tmp_path / "gumroad_scraper" / "output" / "gumroad_free_products.json", [GUMROAD_DUMP])
    legacy = _write_json(
        tmp_path / "scavenging" / "gumroad_free_products.json",
        [{"title": "legacy", "link": "https://old", "published": "2026-01-01T00:00:00", "summary": "old", "category": "gumroad_free", "source": "gumroad_scraper"}],
    )
    _patch_sources(monkeypatch, [{"key": "gumroad_free", "label": "Gumroad free", "category": "gumroad_free", "adapter": _adapt_gumroad_product, "paths": [canonical, legacy]}])

    categories = discover_categories()
    assert categories == {"gumroad_free": Path(canonical)}
    # The adapted canonical content (not the legacy copy) is served.
    data = get_scavenging_data("gumroad_free")
    assert data[0]["title"] == "Free Ebook"


def test_legacy_fallback_used_when_canonical_missing(tmp_path, monkeypatch):
    """Historical data/scavenging/ files still render when no canonical exists yet."""
    legacy = _write_json(
        tmp_path / "scavenging" / "humble_books.json",
        [{"title": "Legacy book", "link": "https://humble", "published": "2026-02-01T00:00:00", "summary": "b", "category": "humble_books", "source": "humble_scraper"}],
    )
    _patch_sources(monkeypatch, [{"key": "humble_books", "label": "Humble books", "category": "humble_books", "paths": [str(tmp_path / "humble_books" / "output" / "humble_books_latest.json"), legacy]}])

    categories = discover_categories()
    assert "humble_books" in categories
    # Legacy records are already display-shaped: adapter-less passthrough.
    data = get_scavenging_data("humble_books")
    assert data[0]["title"] == "Legacy book"
    assert data[0]["category"] == "humble_books"


def test_source_without_any_file_is_absent(tmp_path, monkeypatch):
    """A source whose files do not exist does not appear as a category."""
    _patch_sources(
        monkeypatch,
        [
            {
                "key": "epic_free",
                "label": "Epic free",
                "category": "epic_free",
                "paths": [str(tmp_path / "epic_free_games" / "output" / "epic_free_games_latest.json"), str(tmp_path / "scavenging" / "epic_free_games.json")],
            }
        ],
    )
    assert discover_categories() == {}
    assert get_scavenging_data("epic_free") == []


# --- Adapters -----------------------------------------------------------------


def test_travel_deal_adapter_maps_canonical_model_dump():
    adapted = _adapt_travel_deal(dict(VIAJEROS_DUMP))
    assert adapted["title"] == "Hotel Maldivas"
    assert adapted["link"] == "https://www.viajerospiratas.es/oferta/1"
    assert adapted["published"] == "2026-08-19T08:00:00"
    assert adapted["summary"] == "Viaje a Maldivas"
    assert adapted["category"] == "viajeros_piratas"
    assert adapted["deal_type"] == "hotel"
    assert adapted["price"] == "199.0€"
    assert adapted["currency"] == "EUR"


def test_travel_deal_adapter_passes_legacy_shape_through():
    legacy = {"title": "T", "link": "l", "published": "p", "summary": "s", "category": "viajeros_piratas", "source": "viajeros_piratas_etl", "price": "99€", "deal_type": "hotel"}
    assert _adapt_travel_deal(dict(legacy)) == legacy


def test_gumroad_adapter_maps_canonical_model_dump():
    adapted = _adapt_gumroad_product(dict(GUMROAD_DUMP))
    assert adapted["title"] == "Free Ebook"
    assert adapted["link"] == "https://gumroad.com/l/p1"
    assert adapted["published"] == "2026-08-21T09:00:00"
    assert adapted["summary"] == "A free ebook"
    assert adapted["category"] == "gumroad_free"
    assert adapted["source"] == "gumroad_scraper"
    assert adapted["price"] == "Free"
    assert adapted["seller"] == "Seller Co"


def test_gumroad_adapter_passes_legacy_shape_through():
    legacy = {"title": "T", "link": "l", "published": "p", "summary": "s", "category": "gumroad_free", "source": "gumroad_scraper"}
    assert _adapt_gumroad_product(dict(legacy)) == legacy


# --- Rendering ----------------------------------------------------------------


@pytest.fixture
def two_source_config(tmp_path, monkeypatch):
    """Config with one scavenging-shaped canonical and one model-dump canonical."""
    anime = _write_json(tmp_path / "goldigging_scavenging" / "output" / "anime_rss_entries.json", [RSS_RECORD])
    gumroad = _write_json(tmp_path / "gumroad_scraper" / "output" / "gumroad_free_products.json", [GUMROAD_DUMP, {**GUMROAD_DUMP, "product_id": "p2", "name": "Second"}])
    sources = [
        {"key": "anime", "label": "Anime", "category": "anime", "paths": [anime, str(tmp_path / "scavenging" / "anime_rss_entries.json")]},
        {"key": "gumroad_free", "label": "Gumroad free", "category": "gumroad_free", "adapter": _adapt_gumroad_product, "paths": [gumroad, str(tmp_path / "scavenging" / "gumroad_free_products.json")]},
    ]
    _patch_sources(monkeypatch, sources)
    return tmp_path


def test_tab_renders_from_canonical_paths(two_source_config):
    """Both canonical files render as subtabs with their config labels."""
    layout = render_scavenging_tab()
    rendered = str(layout)
    assert "Anime" in rendered
    assert "Gumroad free" in rendered
    assert "Nyaa item" in rendered
    assert "Free Ebook" in rendered
    # One search id per discovered category.
    assert "scavenging-search-anime" in rendered
    assert "scavenging-search-gumroad_free" in rendered


def test_tab_empty_state_preserved(tmp_path, monkeypatch):
    """No resolvable files at all -> the historical warning alert."""
    _patch_sources(monkeypatch, [{"key": "anime", "label": "Anime", "category": "anime", "paths": [str(tmp_path / "nope" / "anime_rss_entries.json")]}])
    rendered = str(render_scavenging_tab())
    assert "No scavenging data found" in rendered


def test_get_scavenging_data_unknown_key_returns_empty(tmp_path, monkeypatch, two_source_config):
    """Unknown keys (no config entry) return an empty list, as before."""
    assert get_scavenging_data("does_not_exist") == []


def test_category_injected_for_sparse_records(tmp_path, monkeypatch):
    """Records lacking a category get the config category as display fallback."""
    sparse = _write_json(tmp_path / "epic_free_games" / "output" / "epic_free_games_latest.json", [{"title": "Game", "link": "https://epic", "published": "2026-08-01T00:00:00", "summary": "s"}])
    _patch_sources(monkeypatch, [{"key": "epic_free", "label": "Epic free", "category": "epic_free", "paths": [sparse]}])
    data = get_scavenging_data("epic_free")
    assert data[0]["category"] == "epic_free"
