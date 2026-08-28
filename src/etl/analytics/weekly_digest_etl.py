"""Weekly digest ETL (T-054) — "last week" summary compiled from local files.

Reads the latest snapshots produced by other ETLs and watchers (cross-source
trends, tech radar sources, CoinGecko markets, courses watcher, data
freshness) and writes a single digest document rendered by the 📅 Digest
dashboard tab.

No network access: this ETL only reads other components' JSON outputs, so it
is idempotent, cheap and safe to run on every orchestrator cycle. Missing
inputs degrade to empty sections — never a crash.

Usage:
    uv run python src/etl/analytics/weekly_digest_etl.py

Output:
    - data/insights/digest_latest.json
    - data/insights/digest_<YYYYMMDD>.json
    - data/insights/run_summary_latest.json
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.etl.analytics.trends_etl import tokenize_title
from src.utils.file_system import get_project_root
from src.utils.logging import get_logger

logger = get_logger("WeeklyDigestETL")

LOOKBACK_DAYS = 7
MAX_TERMS = 10
MAX_RADAR_ITEMS = 10
MAX_MOVERS = 3

# Radar source files mirrored from tech_radar_tab.RADAR_SOURCES (paths and
# labels only). The ETL layer must not import dashboard components, so keep
# this list in sync with the tab when a source is added or moved.
RADAR_FILES: list[dict[str, str]] = [
    {"key": "google_ai", "label": "Google AI Blog", "file": "news/google_ai_blog_latest.json"},
    {"key": "verge_ai", "label": "The Verge AI", "file": "news/verge_ai_latest.json"},
    {"key": "kdnuggets", "label": "KDNuggets", "file": "kdnuggets/kdnuggets.json"},
    {"key": "cloud_updates", "label": "Cloud Updates", "file": "cloud_updates/cloud_updates_latest.json"},
    {"key": "selfhosted", "label": "Self-Hosted", "file": "selfhosted/selfhosted_latest.json"},
    {"key": "reddit_selfhosted", "label": "r/SelfHosted", "file": "reddit_unified/SelfHosted_latest.json"},
    {"key": "reddit_homelab", "label": "r/homelab", "file": "reddit_unified/homelab_latest.json"},
    {"key": "infoq", "label": "InfoQ", "file": "infoq/infoq_news.json"},
    {"key": "thenewstack", "label": "The New Stack", "file": "thenewstack/thenewstack_news.json"},
    {"key": "changelog", "label": "Changelog", "file": "changelog/changelog_news.json"},
    {"key": "hn_frontpage", "label": "Hacker News", "file": "news/hn_frontpage_latest.json"},
    {"key": "wired", "label": "Wired", "file": "news/wired_latest.json"},
    {"key": "mit_techreview", "label": "MIT Tech Review", "file": "news/mit_techreview_latest.json"},
]

_DATE_FORMATS = ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S")


def _data_dir(data_root: Path | None) -> Path:
    """Resolve the project ``data/`` directory (injectable for tests)."""
    return Path(data_root) if data_root is not None else Path(get_project_root()) / "data"


def _read_json(path: Path, missing: list[str] | None = None) -> Any:
    """Read a JSON file tolerantly; missing/corrupt files yield None."""
    if not path.exists():
        if missing is not None:
            missing.append(str(path))
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Skipping unreadable file {path}: {e}")
        return None


def _parse_epoch(raw: Any) -> float:
    """Best-effort epoch for a date string; unparseable/missing values give 0.0."""
    text = str(raw or "")
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def load_trends_terms(data_root: Path | None = None, max_terms: int = MAX_TERMS, missing: list[str] | None = None) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]]]:
    """Aggregate the trends snapshot into top terms plus a term→stats map.

    Returns:
        Tuple of (top_terms, hot_terms). ``top_terms`` is the ranked digest
        slice; ``hot_terms`` maps every trending term to its mentions/sources
        so the radar section can score articles by 🔥 badge weight.
    """
    trends = _read_json(_data_dir(data_root) / "analytics" / "trends" / "latest_trends.json", missing)
    hot_terms: dict[str, dict[str, int]] = {}
    for record in trends if isinstance(trends, list) else []:
        if not isinstance(record, dict) or not record.get("term"):
            continue
        term = str(record["term"])
        stats = {"mentions": int(record.get("mentions") or 0), "sources": int(record.get("sources_count") or 0)}
        # Records repeat each term per item; keep the fullest stats seen.
        if term not in hot_terms or stats["mentions"] > hot_terms[term]["mentions"]:
            hot_terms[term] = stats
    top_terms = sorted(hot_terms.items(), key=lambda kv: (-kv[1]["mentions"] * kv[1]["sources"], -kv[1]["mentions"], kv[0]))
    return ([{"term": term, "mentions": stats["mentions"], "sources": stats["sources"]} for term, stats in top_terms[:max_terms]], hot_terms)


def load_radar_best(data_root: Path | None = None, hot_terms: dict[str, dict[str, int]] | None = None, max_items: int = MAX_RADAR_ITEMS, now: datetime | None = None, missing: list[str] | None = None) -> list[dict[str, Any]]:
    """Pick the week's best radar articles, ranked by 🔥 mentions then recency.

    Articles whose title matches a trending term (or whose URL is directly
    badged in the trends snapshot) rank by mention count; the rest fall back
    to recency. Articles dated within the lookback window are preferred, but
    stale files still contribute when the window is thin.
    """
    hot_terms = hot_terms or {}
    now = now or datetime.now()
    cutoff = now.timestamp() - LOOKBACK_DAYS * 86400
    root = _data_dir(data_root)
    trending_urls: dict[str, str] = {}
    url_badged = _read_json(root / "analytics" / "trends" / "latest_trends.json")
    for record in url_badged if isinstance(url_badged, list) else []:
        if isinstance(record, dict) and record.get("url") and record.get("term"):
            trending_urls[str(record["url"])] = str(record["term"])

    candidates: list[dict[str, Any]] = []
    for source in RADAR_FILES:
        articles = _read_json(root / source["file"], missing)
        for article in articles if isinstance(articles, list) else []:
            if not isinstance(article, dict):
                continue
            title = str(article.get("title") or article.get("name") or "").strip()
            url = article.get("link") or article.get("url") or ""
            if not title or not url:
                continue
            published = str(article.get("published") or article.get("published_at") or article.get("fetched_at") or "")
            matched: set[str] = set()
            badge_term = trending_urls.get(str(url))
            if badge_term:
                matched.add(badge_term)
            matched.update(token for token in tokenize_title(title) if token in hot_terms)
            score = max((hot_terms[t]["mentions"] for t in matched), default=0)
            candidates.append(
                {
                    "title": title,
                    "url": str(url),
                    "source": source["label"],
                    "source_key": source["key"],
                    "published": published,
                    "trending_terms": sorted(matched),
                    "score": score,
                    "_epoch": _parse_epoch(published),
                }
            )
    # De-duplicate across sources that may mirror the same article.
    seen: set[str] = set()
    unique = [c for c in candidates if not (c["url"] in seen or seen.add(c["url"]))]
    recent = [c for c in unique if c["_epoch"] >= cutoff]
    pool = recent if len(recent) >= max_items else unique
    pool.sort(key=lambda c: (-c["score"], -c["_epoch"]))
    for item in pool:
        item.pop("_epoch", None)
    return pool[:max_items]


def load_market_movers(data_root: Path | None = None, max_movers: int = MAX_MOVERS, missing: list[str] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Top 24h gainers and losers from the CoinGecko snapshot."""
    coins = _read_json(_data_dir(data_root) / "markets" / "coingecko_latest.json", missing)
    priced = [c for c in coins if isinstance(c, dict) and isinstance(c.get("change_24h_pct"), (int, float))] if isinstance(coins, list) else []

    def _row(coin: dict[str, Any]) -> dict[str, Any]:
        return {"name": str(coin.get("name") or coin.get("id") or "?"), "symbol": str(coin.get("symbol") or ""), "change_24h_pct": coin["change_24h_pct"]}

    gainers = sorted((c for c in priced if c["change_24h_pct"] > 0), key=lambda c: c["change_24h_pct"], reverse=True)
    losers = sorted((c for c in priced if c["change_24h_pct"] < 0), key=lambda c: c["change_24h_pct"])
    return {"gainers": [_row(c) for c in gainers[:max_movers]], "losers": [_row(c) for c in losers[:max_movers]]}


def load_courses_context(data_root: Path | None = None, now: datetime | None = None, missing: list[str] | None = None) -> dict[str, Any] | None:
    """Count courses-watcher events in the lookback window (None when absent)."""
    watcher_dir = _data_dir(data_root) / "watchers" / "courses"
    now = now or datetime.now()
    if not watcher_dir.exists():
        if missing is not None:
            missing.append(str(watcher_dir))
        return None
    events_dir = watcher_dir / "events"
    total = 0
    in_window = 0
    if events_dir.exists():
        for event_file in events_dir.glob("*.json"):
            total += 1
            stamp = event_file.name.split("_", 1)[0]
            try:
                event_time = datetime.strptime(stamp, "%Y%m%d%H%M%S").timestamp()
            except ValueError:
                continue
            if event_time >= now.timestamp() - LOOKBACK_DAYS * 86400:
                in_window += 1
    state = _read_json(watcher_dir / "state.json")
    return {"events_last_week": in_window, "total_events": total, "last_check": str(state.get("last_check") or "") if isinstance(state, dict) else ""}


def load_freshness_context(data_root: Path | None = None, missing: list[str] | None = None) -> dict[str, Any] | None:
    """Freshness snapshot counts (None when the watcher has not run yet)."""
    freshness = _read_json(_data_dir(data_root) / "watchers" / "data_freshness" / "freshness_latest.json", missing)
    if not isinstance(freshness, dict):
        return None
    counts = freshness.get("counts") if isinstance(freshness.get("counts"), dict) else {}
    return {"checked_at": str(freshness.get("checked_at") or ""), "counts": {k: int(counts.get(k) or 0) for k in ("fresh", "stale", "critical")}}


def build_digest(data_root: Path | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Compile the full weekly digest document from local snapshots."""
    now = now or datetime.now()
    missing: list[str] = []
    top_terms, hot_terms = load_trends_terms(data_root, missing=missing)
    digest = {
        "generated_at": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "period": {"start": datetime.fromtimestamp(now.timestamp() - LOOKBACK_DAYS * 86400).isoformat(), "end": now.isoformat(), "days": LOOKBACK_DAYS},
        "top_terms": top_terms,
        "radar_best": load_radar_best(data_root, hot_terms=hot_terms, now=now, missing=missing),
        "market_movers": load_market_movers(data_root, missing=missing),
        "courses_watcher": load_courses_context(data_root, now=now, missing=missing),
        "freshness": load_freshness_context(data_root, missing=missing),
        "_missing_inputs": sorted(set(missing)),
    }
    return digest


def save_digest(digest: dict[str, Any], output_dir: Path | None = None) -> list[Path]:
    """Persist the digest (latest + dated copies) and its run summary."""
    out = Path(output_dir) if output_dir is not None else Path(get_project_root()) / "data" / "insights"
    out.mkdir(parents=True, exist_ok=True)
    payload = {k: v for k, v in digest.items() if not k.startswith("_")}
    paths = []
    for name in (f"digest_{digest['date'].replace('-', '')}.json", "digest_latest.json"):
        path = out / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths.append(path)
    summary = {
        "ran_at": digest["generated_at"],
        "period_days": digest["period"]["days"],
        "sections": {
            "top_terms": len(digest["top_terms"]),
            "radar_best": len(digest["radar_best"]),
            "market_movers": len(digest["market_movers"]["gainers"]) + len(digest["market_movers"]["losers"]),
            "courses_watcher": digest["courses_watcher"],
            "freshness": digest["freshness"],
        },
        "missing_inputs": digest.get("_missing_inputs", []),
        "outputs": [str(p) for p in paths],
    }
    summary_path = out / "run_summary_latest.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    paths.append(summary_path)
    return paths


def run() -> dict[str, Any]:
    """Run the weekly digest pipeline end to end."""
    digest = build_digest()
    paths = save_digest(digest)
    summary = {
        "ran_at": digest["generated_at"],
        "top_terms": len(digest["top_terms"]),
        "radar_best": len(digest["radar_best"]),
        "market_movers": {k: len(v) for k, v in digest["market_movers"].items()},
        "courses_watcher": digest["courses_watcher"],
        "freshness": digest["freshness"],
        "missing_inputs": digest.get("_missing_inputs", []),
        "outputs": [str(p) for p in paths],
    }
    logger.info(f"Weekly digest: {summary['top_terms']} terms, {summary['radar_best']} radar picks, {summary['market_movers']} movers ({len(summary['missing_inputs'])} missing inputs)")
    return summary


if __name__ == "__main__":
    run()
