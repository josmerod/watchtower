"""Unit tests for the weekly digest ETL (T-054) — local files only, tmp_path fixtures."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from src.etl.analytics import weekly_digest_etl as wde

NOW = datetime(2026, 8, 28, 10, 0, 0)


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _seed_data_root(tmp_path: Path) -> Path:
    """Create a realistic mini data/ tree covering every digest input."""
    root = tmp_path / "data"
    _write(
        root / "analytics" / "trends" / "latest_trends.json",
        [
            {"term": "docker", "mentions": 12, "sources_count": 4, "url": "https://x/docker-1", "is_trending": True},
            {"term": "docker", "mentions": 12, "sources_count": 4, "url": "https://x/docker-2", "is_trending": True},
            {"term": "kubernetes", "mentions": 6, "sources_count": 3, "url": "https://x/k8s", "is_trending": True},
        ],
    )
    _write(
        root / "news" / "hn_frontpage_latest.json",
        [
            {"title": "Docker ships a big release", "link": "https://x/docker-1", "published": (NOW - timedelta(days=1)).isoformat()},
            {"title": "A quiet story about knitting", "link": "https://x/knit", "published": (NOW - timedelta(days=3)).isoformat()},
            {"title": "Ancient kubernetes drama", "link": "https://x/old", "published": (NOW - timedelta(days=30)).isoformat()},
        ],
    )
    _write(
        root / "markets" / "coingecko_latest.json",
        [
            {"name": "Bitcoin", "symbol": "BTC", "change_24h_pct": 5.0},
            {"name": "Ether", "symbol": "ETH", "change_24h_pct": 2.0},
            {"name": "Solana", "symbol": "SOL", "change_24h_pct": 1.0},
            {"name": "XRP", "symbol": "XRP", "change_24h_pct": -1.5},
            {"name": "Doge", "symbol": "DOGE", "change_24h_pct": -9.9},
            {"name": "Cardano", "symbol": "ADA", "change_24h_pct": None},
        ],
    )
    events = root / "watchers" / "courses" / "events"
    events.mkdir(parents=True)
    (events / f"{(NOW - timedelta(days=2)).strftime('%Y%m%d%H%M%S')}_new_matching_course_001.json").write_text("{}", encoding="utf-8")
    (events / f"{(NOW - timedelta(days=20)).strftime('%Y%m%d%H%M%S')}_new_matching_course_001.json").write_text("{}", encoding="utf-8")
    _write(root / "watchers" / "courses" / "state.json", {"last_check": NOW.isoformat()})
    _write(root / "watchers" / "data_freshness" / "freshness_latest.json", {"checked_at": NOW.isoformat(), "counts": {"fresh": 8, "stale": 2, "critical": 1}})
    return root


def test_build_digest_compiles_all_sections(tmp_path):
    digest = wde.build_digest(data_root=_seed_data_root(tmp_path), now=NOW)

    # Top terms: docker (12 mentions · 4 sources) ranks above kubernetes
    assert [t["term"] for t in digest["top_terms"]] == ["docker", "kubernetes"]
    assert digest["top_terms"][0] == {"term": "docker", "mentions": 12, "sources": 4}

    # Radar best: 🔥-badged article first, stale story still included via recency backfill
    assert digest["radar_best"][0]["title"] == "Docker ships a big release"
    assert digest["radar_best"][0]["trending_terms"] == ["docker"]
    assert digest["radar_best"][0]["source"] == "Hacker News"
    assert digest["radar_best"][0]["url"] == "https://x/docker-1"
    assert len(digest["radar_best"]) == 3  # pool backfills beyond the 2 recent items

    # Market movers: top 3 gainers, losers exclude the None pct coin
    assert [c["name"] for c in digest["market_movers"]["gainers"]] == ["Bitcoin", "Ether", "Solana"]
    assert [c["name"] for c in digest["market_movers"]["losers"]] == ["Doge", "XRP"]

    assert digest["courses_watcher"]["events_last_week"] == 1
    assert digest["courses_watcher"]["total_events"] == 2

    assert digest["freshness"]["counts"] == {"fresh": 8, "stale": 2, "critical": 1}
    # Only the unseeded radar sources are reported missing — every seeded input counts as present
    missing = digest["_missing_inputs"]
    assert missing, "unseeded radar files should be reported"
    assert not [m for m in missing if "trends" in m or "markets" in m or "watchers" in m or "hn_frontpage" in m]


def test_build_digest_degrades_when_files_missing(tmp_path):
    digest = wde.build_digest(data_root=tmp_path / "data", now=NOW)
    assert digest["top_terms"] == []
    assert digest["radar_best"] == []
    assert digest["market_movers"] == {"gainers": [], "losers": []}
    assert digest["courses_watcher"] is None
    assert digest["freshness"] is None
    assert digest["_missing_inputs"]  # degraded inputs are reported, not fatal


def test_radar_recent_window_excludes_stale_when_full(tmp_path):
    root = tmp_path / "data"
    _write(root / "analytics" / "trends" / "latest_trends.json", [])
    articles = [
        {"title": f"Recent story number {i}", "link": f"https://x/r{i}", "published": (NOW - timedelta(days=1)).isoformat()}
        for i in range(4)
    ]
    articles.append({"title": "Ancient story", "link": "https://x/ancient", "published": (NOW - timedelta(days=90)).isoformat()})
    _write(root / "news" / "hn_frontpage_latest.json", articles)
    best = wde.load_radar_best(data_root=root, hot_terms={}, max_items=4, now=NOW)
    assert len(best) == 4
    assert all(a["title"] != "Ancient story" for a in best)


def test_save_writes_latest_dated_and_summary(tmp_path):
    digest = wde.build_digest(data_root=_seed_data_root(tmp_path), now=NOW)
    out = tmp_path / "out"
    paths = wde.save_digest(digest, output_dir=out)

    names = {p.name for p in paths}
    assert names == {"digest_20260828.json", "digest_latest.json", "run_summary_latest.json"}
    for p in paths:
        assert p.exists()

    latest = json.loads((out / "digest_latest.json").read_text(encoding="utf-8"))
    assert "_missing_inputs" not in latest  # internal bookkeeping stays out of the payload
    assert latest["date"] == "2026-08-28"
    assert latest["period"]["days"] == 7

    summary = json.loads((out / "run_summary_latest.json").read_text(encoding="utf-8"))
    assert summary["sections"]["top_terms"] == 2
    assert summary["sections"]["radar_best"] == 3
    assert summary["sections"]["market_movers"] == 5
