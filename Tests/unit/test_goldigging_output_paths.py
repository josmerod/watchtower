"""Unit tests for goldigging ETL save paths (T-067).

Every test monkeypatches the project root to a tmp_path fixture and asserts
each ETL writes ONLY its canonical output — and never creates the legacy
data/scavenging/ directory. No network, no real data/ files touched.
"""

import json
from datetime import datetime
from types import SimpleNamespace

import pytest

import src.etl.base as etl_base
import src.etl.goldigging.epic_free_games_etl as epic_etl
import src.etl.goldigging.goldigging_scavenging_etl as rss_etl
from src.etl.goldigging.audible_releases_etl import AudibleReleasesETL
from src.etl.goldigging.gumroad_scraper_etl import GumroadScraperETL
from src.etl.goldigging.humble_books_etl import HumbleBook, HumbleBooksETL
from src.etl.goldigging.viajeros_piratas_etl import ViajerosPrivatasETL
from src.models.ecommerce import GumroadProduct, TravelDeal


class _FakeSettings:
    """Minimal settings stand-in redirecting BaseETL dirs under tmp_path."""

    def __init__(self, project_root):
        self.project_root = str(project_root)
        self.etl = SimpleNamespace(batch_size=100)


@pytest.fixture
def fake_root(tmp_path, monkeypatch):
    """Point BaseETL's project root (and thus data dirs) at tmp_path."""
    monkeypatch.setattr(etl_base, "get_settings", lambda: _FakeSettings(tmp_path))
    return tmp_path


# --- humble_books --------------------------------------------------------------


def test_humble_books_writes_canonical_only(fake_root):
    etl = HumbleBooksETL()
    books = [HumbleBook(title="Book A", bundle_name="Bundle", url="https://humble.dadand.dev/bundles/1", fetched_at=datetime(2026, 8, 28, 10, 0))]

    etl.load(books)

    canonical = fake_root / "data" / "humble_books" / "output" / "humble_books_latest.json"
    assert canonical.is_file()
    records = json.loads(canonical.read_text(encoding="utf-8"))
    assert records[0]["category"] == "humble_books"
    assert records[0]["title"] == "Book A"
    # Legacy location must not be created anymore.
    assert not (fake_root / "data" / "scavenging").exists()


# --- audible_releases ----------------------------------------------------------


def test_audible_releases_writes_canonical_only(fake_root):
    etl = AudibleReleasesETL()
    entries = [
        {
            "title": "Audiobook",
            "link": "https://audible.es/pd/1",
            "published": "2026-08-28T00:00:00+00:00",
            "summary": "s",
            "category": "audible",
            "source": "audible_releases_etl",
            "deal_type": "Audiobook",
            "price": "Included",
        }
    ]

    etl.load(entries)

    out_dir = fake_root / "data" / "audible_releases" / "output"
    assert (out_dir / "audible_releases_latest.json").is_file()
    assert (out_dir / "audible_releases_latest.csv").is_file()
    records = json.loads((out_dir / "audible_releases_latest.json").read_text(encoding="utf-8"))
    assert records[0]["title"] == "Audiobook"
    assert not (fake_root / "data" / "scavenging").exists()


# --- viajeros_piratas ----------------------------------------------------------


def _travel_deal() -> TravelDeal:
    now = datetime(2026, 8, 28, 10, 0)
    return TravelDeal(
        deal_id="vp_1_1",
        title="Hotel Maldivas",
        description="Viaje",
        price=199.0,
        currency="EUR",
        raw_price="Desde 199€",
        category="hotel",
        url="https://www.viajerospiratas.es/oferta/1",
        published_at=now,
        fetched_at=now,
        parsed_at=now,
        page_number=1,
        position=1,
    )


def test_viajeros_piratas_writes_canonical_only(fake_root):
    etl = ViajerosPrivatasETL(max_pages=1)
    etl.load([_travel_deal()])

    out_dir = fake_root / "data" / "viajeros_piratas" / "output"
    assert (out_dir / "viajeros_piratas_deals.json").is_file()
    assert (out_dir / "viajeros_piratas_deals.csv").is_file()
    records = json.loads((out_dir / "viajeros_piratas_deals.json").read_text(encoding="utf-8"))
    assert records[0]["title"] == "Hotel Maldivas"
    # No scavenging-format copy anymore.
    assert not (fake_root / "data" / "scavenging").exists()


# --- gumroad_scraper -----------------------------------------------------------


def _gumroad_product() -> GumroadProduct:
    now = datetime(2026, 8, 28, 10, 0)
    return GumroadProduct(product_id="p1", name="Free Ebook", price="Free", seller="Seller", description="D", url="https://gumroad.com/l/p1", fetched_at=now, parsed_at=now)


def test_gumroad_writes_canonical_only(fake_root):
    etl = GumroadScraperETL(first_run=True)
    etl.load([_gumroad_product()])

    out_dir = fake_root / "data" / "gumroad_scraper" / "output"
    assert (out_dir / "gumroad_free_products.json").is_file()
    assert (out_dir / "gumroad_free_products.csv").is_file()
    records = json.loads((out_dir / "gumroad_free_products.json").read_text(encoding="utf-8"))
    assert records[0]["name"] == "Free Ebook"
    assert not (fake_root / "data" / "scavenging").exists()


# --- epic_free_games -----------------------------------------------------------


def test_epic_free_games_writes_canonical_only(tmp_path, monkeypatch):
    monkeypatch.setattr(epic_etl, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(
        epic_etl,
        "fetch_free_games",
        lambda: [{"title": "Game — Free now (Epic)", "link": "https://store.epicgames.com/p/g", "published": "2026-08-28T00:00", "summary": "s", "category": "epic_free", "source": "epic_games"}],
    )

    epic_etl.main()

    canonical = tmp_path / "data" / "epic_free_games" / "output" / "epic_free_games_latest.json"
    assert canonical.is_file()
    records = json.loads(canonical.read_text(encoding="utf-8"))
    assert records[0]["category"] == "epic_free"
    assert not (tmp_path / "data" / "scavenging").exists()


# --- goldigging_scavenging (RSS aggregator) ------------------------------------


def test_rss_aggregator_writes_canonical_only(tmp_path, monkeypatch):
    monkeypatch.setattr(rss_etl, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(rss_etl, "fetch_rss_entries", lambda url: [{"title": "Entry", "link": "https://nyaa.si/t/1", "published": "2026-08-28T00:00:00+00:00", "summary": "s"}])

    rss_etl.process_category("anime", {"nyaa": {"type": "rss", "url": "https://nyaa.si/?page=rss"}})

    out_dir = tmp_path / "data" / "goldigging_scavenging" / "output"
    aggregated = out_dir / "anime_rss_entries.json"
    assert aggregated.is_file()
    assert (out_dir / "anime_rss_entries.csv").is_file()
    records = json.loads(aggregated.read_text(encoding="utf-8"))
    assert records[0]["category"] == "anime"
    assert records[0]["source"] == "nyaa"
    # Per-source debug output also lives under the canonical dir now.
    assert (out_dir / "anime" / "nyaa_entries.json").is_file()
    assert not (tmp_path / "data" / "scavenging").exists()
