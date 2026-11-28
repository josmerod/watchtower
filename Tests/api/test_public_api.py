"""Hermetic unit tests for the read-only public API endpoints (T-056).

All tests point the endpoints at a ``tmp_path`` data directory via
monkeypatching ``src.api.public._get_data_dir`` — the real ``data/`` dir and
the network are never touched.
"""

import json
from datetime import datetime, timedelta, timezone
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
# GET /api/v1/digest (T-084)
# ---------------------------------------------------------------------------

DIGEST = {
    "generated_at": "2026-09-10T08:00:00+00:00",
    "hot_terms": [{"term": "agent", "mentions": 68, "sources": 12}],
    "missing_inputs": [],
}


def test_digest_ok(data_dir: Path):
    """200, digest payload returned as stored."""
    _write(data_dir, "insights/digest_latest.json", DIGEST)
    response = client.get("/api/v1/digest")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["generated_at"] == DIGEST["generated_at"]
    assert body["hot_terms"][0]["term"] == "agent"


def test_digest_missing(data_dir: Path):
    """404 when the digest file does not exist."""
    response = client.get("/api/v1/digest")
    assert response.status_code == 404
    assert "error" in response.json()


# ---------------------------------------------------------------------------
# GET /api/v1/security/kev (T-084)
# ---------------------------------------------------------------------------

SECURITY = {
    "generated_at": "2026-09-10T06:00:00+00:00",
    "items": [
        {"cve": "CVE-2026-0001", "vendor": "acme", "product": "widget"},
        {"cve": "CVE-2026-0002", "vendor": "n8n", "product": "n8n"},
        {"cve": "CVE-2026-0003", "vendor": "other", "product": "thing"},
    ],
    "stack_matches": [{"repo": "n8n-io/n8n", "service_label": "n8n", "cves": [{"cve": "CVE-2026-0002"}]}],
}


def test_security_kev_ok(data_dir: Path):
    """200, KEV items + stack_matches cross-reference served."""
    _write(data_dir, "security/security_latest.json", SECURITY)
    response = client.get("/api/v1/security/kev")
    assert response.status_code == 200
    body = response.json()
    assert body["kev_count"] == 3
    assert len(body["items"]) == 3
    assert body["stack_matches"][0]["repo"] == "n8n-io/n8n"


def test_security_kev_limit(data_dir: Path):
    """?limit caps the returned KEV items without touching the count."""
    _write(data_dir, "security/security_latest.json", SECURITY)
    response = client.get("/api/v1/security/kev?limit=2")
    assert response.status_code == 200
    body = response.json()
    assert body["kev_count"] == 3
    assert len(body["items"]) == 2


def test_security_kev_missing(data_dir: Path):
    """404 when the security file does not exist."""
    response = client.get("/api/v1/security/kev")
    assert response.status_code == 404
    assert "error" in response.json()


# ---------------------------------------------------------------------------
# GET /api/v1/valencia/events (T-084)
# ---------------------------------------------------------------------------

def _valencia_payload() -> dict:
    """Valencia events with dates relative to now — hardcoded dates rot (this is the second time)."""

    def _iso(days: int, hour: int) -> str:
        return (datetime.now(timezone.utc) + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()

    return {
        "events": [
            {"title": "Past conference", "start_date": _iso(-30, 10)},
            # The ETL writes calendar dates without a time: these used to drop out of the
            # filtered view at 00:01 of their own day (T-160)
            {"title": "Yesterday, date only", "start_date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")},
            {"title": "Today, date only", "start_date": datetime.now().strftime("%Y-%m-%d")},
            {"title": "Soon meetup", "start_date": _iso(3, 20)},
            {"title": "Next month gig", "start_date": _iso(35, 21)},
            {"title": "Undated thing"},
        ]
    }


def test_valencia_events_all(data_dir: Path):
    """200, full list as stored (undated events included when unfiltered)."""
    _write(data_dir, "valencia_events/valencia_events.json", _valencia_payload())
    response = client.get("/api/v1/valencia/events")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 6
    assert body["items"][0]["title"] == "Past conference"


def test_valencia_events_days_filter(data_dir: Path):
    """?days=N keeps only events starting inside [today, now+N] — past and undated excluded, today kept."""
    _write(data_dir, "valencia_events/valencia_events.json", _valencia_payload())
    response = client.get("/api/v1/valencia/events?days=30")
    assert response.status_code == 200
    assert [e["title"] for e in response.json()["items"]] == ["Today, date only", "Soon meetup"]

    response = client.get("/api/v1/valencia/events?days=40")
    assert [e["title"] for e in response.json()["items"]] == ["Today, date only", "Soon meetup", "Next month gig"]


def test_valencia_events_missing(data_dir: Path):
    """404 when the Valencia events file does not exist."""
    response = client.get("/api/v1/valencia/events")
    assert response.status_code == 404
    assert "error" in response.json()


# The optional filters of T-143. Fixed dates: a window of days does not depend on today.


def _valencia_record(title: str, start_at: str, category: str | None = "otro") -> dict:
    """An event as the ETL stores it since T-143: the aware moment, and the calendar date next to it."""
    return {"title": title, "category": category, "start_date": start_at[:10], "start_at": start_at}


VALENCIA_RANGE = [
    _valencia_record("Teatro ayer", "2026-11-27T20:00:00+01:00", "teatro"),
    _valencia_record("Música hoy", "2026-11-28T23:00:00+01:00", "música"),
    # Half past midnight in València, still the 28th in UTC: the day of the event is the 29th.
    _valencia_record("Noche en UTC", "2026-11-29T00:30:00+01:00", "música"),
    _valencia_record("Charla tech", "2026-11-29T19:00:00+01:00", "tech"),
    _valencia_record("Feria lejana", "2026-12-20T00:00:00+01:00", "ferias"),
    {"title": "Sin categoría", "start_date": "2026-11-28"},  # an older file: the date only
    {"title": "Sin zona horaria", "start_date": "2026-11-28T19:30:00", "category": "teatro"},  # an older file: a bare timestamp
    {"title": "Sin fecha", "category": "tech"},
]


def _valencia_titles(params: dict) -> list[str]:
    response = client.get("/api/v1/valencia/events", params=params)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"generated_at", "count", "items"} and body["count"] == len(body["items"])  # the envelope does not change
    assert response.headers["cache-control"] == "no-store"
    return [item["title"] for item in body["items"]]


def test_valencia_events_category_filter(data_dir: Path):
    """?category= keeps one category; case and accents do not count, and a record without one is "otro"."""
    _write(data_dir, "valencia_events/valencia_events.json", VALENCIA_RANGE)

    assert _valencia_titles({"category": "musica"}) == ["Música hoy", "Noche en UTC"]
    assert _valencia_titles({"category": "  MÚSICA "}) == ["Música hoy", "Noche en UTC"]
    assert _valencia_titles({"category": "otro"}) == ["Sin categoría"]
    assert _valencia_titles({"category": "tech"}) == ["Charla tech", "Sin fecha"]  # no window: the undated one stays
    assert _valencia_titles({"category": "no-existe"}) == []


def test_valencia_events_from_and_to(data_dir: Path):
    """?from= and ?to= bound the days an event starts on, in València's time, both ends inclusive."""
    _write(data_dir, "valencia_events/valencia_events.json", VALENCIA_RANGE)

    assert _valencia_titles({"from": "2026-11-29"}) == ["Noche en UTC", "Charla tech", "Feria lejana"]
    assert _valencia_titles({"to": "2026-11-28"}) == ["Teatro ayer", "Música hoy", "Sin categoría", "Sin zona horaria"]
    assert _valencia_titles({"from": "2026-11-28", "to": "2026-11-29"}) == ["Música hoy", "Noche en UTC", "Charla tech", "Sin categoría", "Sin zona horaria"]
    assert _valencia_titles({"from": "2026-11-29", "to": "2026-11-28"}) == []  # a reversed range is empty, not swapped
    assert "Sin fecha" not in _valencia_titles({"to": "2027-01-01"})  # a window never lists what has no date


def test_valencia_events_filters_combine_and_from_replaces_days(data_dir: Path):
    _write(data_dir, "valencia_events/valencia_events.json", VALENCIA_RANGE)

    assert _valencia_titles({"from": "2026-11-29", "category": "tech"}) == ["Charla tech"]
    assert _valencia_titles({"from": "2026-11-29", "category": "teatro"}) == []
    # A range of days is the window: `days` no longer cuts it.
    assert _valencia_titles({"days": 1, "from": "2026-12-01"}) == ["Feria lejana"]


def test_valencia_events_a_date_that_is_not_one_is_refused(data_dir: Path):
    _write(data_dir, "valencia_events/valencia_events.json", VALENCIA_RANGE)

    for params in ({"from": "ayer"}, {"to": "2026-13-40"}, {"from": "29/11/2026"}):
        assert client.get("/api/v1/valencia/events", params=params).status_code == 422


def test_valencia_events_filters_keep_the_envelope_and_the_records(data_dir: Path):
    """A filtered answer is the same envelope, with the records as stored."""
    _write(data_dir, "valencia_events/valencia_events.json", VALENCIA_RANGE)

    everything = client.get("/api/v1/valencia/events").json()
    filtered = client.get("/api/v1/valencia/events", params={"category": "ferias"}).json()
    assert filtered["items"] == everything["items"][4:5]
    assert filtered["generated_at"] == everything["generated_at"]


# ---------------------------------------------------------------------------
# OpenAPI wiring
# ---------------------------------------------------------------------------


def test_openapi_includes_public_endpoints():
    """The new endpoints show up in the generated OpenAPI schema."""
    schema = client.get("/openapi.json").json()
    for path in ("/api/v1/markets", "/api/v1/radar", "/api/v1/freshness", "/api/v1/digest", "/api/v1/security/kev", "/api/v1/valencia/events"):
        assert path in schema["paths"]
        assert "get" in schema["paths"][path]
