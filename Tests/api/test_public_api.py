"""Hermetic unit tests for the read-only public API endpoints (T-056).

All tests point the endpoints at a ``tmp_path`` data directory via
monkeypatching ``src.api.public._get_data_dir`` — the real ``data/`` dir and
the network are never touched.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import src.api.public as public_api
from src.api.main import app

client = TestClient(app)

COINS = [
    {"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC", "rank": 1, "price_usd": 79919, "fetched_at": "2026-08-27T14:36:42.567088+00:00"},
    {"id": "ethereum", "name": "Ethereum", "symbol": "ETH", "rank": 2, "price_usd": 3100, "fetched_at": "2026-08-27T14:37:42.567088+00:00"},
    {"id": "solana", "name": "Solana", "symbol": "SOL", "rank": 3, "price_usd": 210, "fetched_at": "2026-08-26T10:00:00+00:00"},
]


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the public API data root to a temp directory."""
    monkeypatch.setattr(public_api, "_get_data_dir", lambda: tmp_path)
    return tmp_path


def _write(data_dir: Path, rel_path: str, payload) -> None:
    """Write a JSON payload under the temp data dir."""
    target = data_dir / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# GET /api/v1/markets
# ---------------------------------------------------------------------------


def test_markets_ok(data_dir: Path):
    """200 with envelope shape, passthrough items, malformed entries skipped."""
    _write(data_dir, "markets/coingecko_latest.json", COINS + ["not-a-dict", {}])
    response = client.get("/api/v1/markets")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert set(body) == {"generated_at", "count", "items"}
    assert body["count"] == 3
    assert len(body["items"]) == 3
    # Items are the stored coin dicts, unchanged.
    assert body["items"][0]["id"] == "bitcoin"
    assert body["items"][0]["price_usd"] == 79919
    # generated_at is the newest fetched_at across items.
    assert body["generated_at"] == "2026-08-27T14:37:42.567088+00:00"


def test_markets_limit(data_dir: Path):
    """?limit= truncates items; out-of-range limits are rejected with 422."""
    _write(data_dir, "markets/coingecko_latest.json", COINS)
    limited = client.get("/api/v1/markets", params={"limit": 2})
    assert limited.status_code == 200
    body = limited.json()
    assert body["count"] == 2
    assert [i["id"] for i in body["items"]] == ["bitcoin", "ethereum"]
    assert client.get("/api/v1/markets", params={"limit": 501}).status_code == 422
    assert client.get("/api/v1/markets", params={"limit": 0}).status_code == 422


def test_markets_missing(data_dir: Path):
    """404 with {"error": ...} when the file does not exist."""
    response = client.get("/api/v1/markets")
    assert response.status_code == 404
    assert "error" in response.json()
    assert response.headers["cache-control"] == "no-store"


# ---------------------------------------------------------------------------
# GET /api/v1/radar
# ---------------------------------------------------------------------------


def test_radar_ok(data_dir: Path):
    """200, newest-first merge, dedupe, normalization, exact item shape."""
    _write(
        data_dir,
        "news/google_ai_blog_latest.json",
        [
            {"title": "Older Google post", "link": "https://ai.google/older", "published": "2026-08-26T08:00:00Z"},
            {"title": "Google post via published_at", "link": "https://ai.google/newer", "published_at": "2026-08-27T08:00:00Z"},
            {"title": "Duplicate link", "link": "https://ai.google/older", "published": "2026-08-28T08:00:00Z"},
            "malformed-entry",
            {"link": "https://ai.google/no-title", "published": "2026-08-28T08:00:00Z"},  # no title -> skipped
        ],
    )
    _write(
        data_dir,
        "news/hn_frontpage_latest.json",
        [
            {"title": "Newest HN story", "url": "https://news.ycombinator.com/item?id=1", "published": "2026-08-28T09:30:00Z"},
            {"title": "Undated story", "url": "https://news.ycombinator.com/item?id=2"},
        ],
    )
    response = client.get("/api/v1/radar")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert set(body) == {"generated_at", "count", "items"}
    items = body["items"]
    # 2 valid Google articles (dedupe drops the repeated link; the titleless
    # and non-dict entries are skipped) + 2 HN stories = 4, newest first with
    # the undated story last.
    assert body["count"] == 4
    assert [i["title"] for i in items] == ["Newest HN story", "Google post via published_at", "Older Google post", "Undated story"]
    # Exact shape and normalization checks.
    for item in items:
        assert set(item) == {"title", "link", "source", "published", "category"}
    assert items[0]["source"] == "hn_frontpage"
    assert items[0]["link"] == "https://news.ycombinator.com/item?id=1"
    assert items[0]["category"] == "Discussion"
    by_title = {i["title"]: i for i in items}
    assert by_title["Google post via published_at"]["published"] == "2026-08-27T08:00:00Z"
    assert by_title["Google post via published_at"]["source"] == "google_ai"
    assert by_title["Google post via published_at"]["category"] == "AI"
    assert by_title["Undated story"]["published"] == ""


def test_radar_limit(data_dir: Path):
    """?limit= caps the merged feed and count reflects the truncation."""
    _write(data_dir, "news/wired_latest.json", [{"title": f"Article {i}", "published": f"2026-08-{20 + i:02d}T00:00:00Z"} for i in range(4)])
    response = client.get("/api/v1/radar", params={"limit": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["items"][0]["title"] == "Article 3"
    assert client.get("/api/v1/radar", params={"limit": 501}).status_code == 422


def test_radar_missing_all_files(data_dir: Path):
    """404 with {"error": ...} when no radar source file exists at all."""
    response = client.get("/api/v1/radar")
    assert response.status_code == 404
    assert "error" in response.json()
    assert response.headers["cache-control"] == "no-store"


def test_radar_multi_file_source_dedupe(data_dir: Path):
    """A source reading several files dedupes across them (reddit_pulse)."""
    _write(data_dir, "reddit_unified/SelfHosted_latest.json", [{"title": "Shared post", "link": "https://reddit/1", "published": "2026-08-27T00:00:00Z"}])
    _write(
        data_dir,
        "reddit_unified/homelab_latest.json",
        [{"title": "Shared post", "link": "https://reddit/1", "published": "2026-08-28T00:00:00Z"}, {"title": "Homelab only", "url": "https://reddit/2", "published": "2026-08-26T00:00:00Z"}],
    )
    body = client.get("/api/v1/radar").json()
    assert body["count"] == 2
    assert {i["title"] for i in body["items"]} == {"Shared post", "Homelab only"}
    assert all(i["category"] == "Self-Hosting" for i in body["items"])


# ---------------------------------------------------------------------------
# GET /api/v1/freshness
# ---------------------------------------------------------------------------

FRESHNESS = {
    "checked_at": "2026-08-28T07:15:21.034170+00:00",
    "counts": {"fresh": 1, "stale": 1, "critical": 1},
    "sources": [
        {"key": "google_ai", "label": "Google AI Blog", "path": "news/google_ai_blog_latest.json", "exists": True, "age_hours": 1.0, "status": "fresh"},
        {"key": "infoq", "label": "InfoQ", "path": "infoq/infoq_news.json", "exists": True, "age_hours": 100.0, "status": "stale"},
        {"key": "kdnuggets", "label": "KDnuggets", "path": "kdnuggets/kdnuggets.json", "exists": False, "age_hours": None, "status": "critical"},
        "malformed-entry",
    ],
}


def test_freshness_ok(data_dir: Path):
    """200, summary preserved as stored, stale_sources lists non-fresh records."""
    _write(data_dir, "watchers/data_freshness/freshness_latest.json", FRESHNESS)
    response = client.get("/api/v1/freshness")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["checked_at"] == FRESHNESS["checked_at"]
    assert body["counts"] == FRESHNESS["counts"]
    assert len(body["sources"]) == 4  # stored list untouched (incl. malformed)
    assert [s["key"] for s in body["stale_sources"]] == ["infoq", "kdnuggets"]
    assert body["stale_sources"][1]["status"] == "critical"


def test_freshness_missing(data_dir: Path):
    """404 with {"error": ...} when the freshness file does not exist."""
    response = client.get("/api/v1/freshness")
    assert response.status_code == 404
    assert "error" in response.json()
    assert response.headers["cache-control"] == "no-store"


# ---------------------------------------------------------------------------
# OpenAPI wiring
# ---------------------------------------------------------------------------


def test_openapi_includes_public_endpoints():
    """The new endpoints show up in the generated OpenAPI schema."""
    schema = client.get("/openapi.json").json()
    for path in ("/api/v1/markets", "/api/v1/radar", "/api/v1/freshness"):
        assert path in schema["paths"]
        assert "get" in schema["paths"][path]
