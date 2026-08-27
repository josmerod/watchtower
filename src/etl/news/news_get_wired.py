"""Wired ETL — tech culture, AI, security, and science coverage.

Fetches Wired's main RSS feed — premium general-tech media with strong AI and
security sections. Feeds the Tech Radar tab's Tech Media column.

Usage:
    uv run python -m src.etl.news.news_get_wired

Output:
    data/news/wired_latest.json (+ timestamped snapshot)
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.utils.retry import with_retry

logger = get_logger("WiredETL")

RSS_FEED = "https://www.wired.com/feed/rss"


@with_retry
def fetch_wired() -> list[dict[str, Any]]:
    """Fetch and parse the Wired RSS feed."""
    entries: list[dict[str, Any]] = []
    logger.info(f"Fetching Wired RSS feed from {RSS_FEED}")
    try:
        response = requests.get(RSS_FEED, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo:
            logger.warning(f"Feed parse warning: {feed.bozo_exception}")
    except requests.RequestException as exc:
        logger.error(f"Could not fetch the Wired feed: {exc}")
        return entries

    for entry in feed.entries:
        published = _parse_date(entry.get("published", ""))
        summary = ""
        if hasattr(entry, "summary") and entry.summary:
            summary = re.sub(r"<[^>]+>", "", entry.summary).strip()
        authors = ""
        if hasattr(entry, "authors") and entry.authors:
            authors = ", ".join(a.get("name", "") for a in entry.authors if isinstance(a, dict))
        elif hasattr(entry, "author") and entry.author:
            authors = entry.author
        entries.append(
            {
                "source": "wired",
                "source_category": "tech_media",
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": published,
                "summary": summary[:500],
                "author": authors,
                "categories": [t.get("term", "") for t in getattr(entry, "tags", [])],
                "guid": entry.get("id", ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "wired",
                "content_type": "news_article",
                "language": "en",
                "region": "global",
            }
        )
    logger.info(f"Retrieved {len(entries)} items from the Wired feed")
    return entries


def _parse_date(published_raw: str) -> str:
    """Parse an RSS date string to ISO format, falling back to the raw value."""
    if not published_raw:
        return ""
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(published_raw, fmt).isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(published_raw.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return published_raw


def save_wired_entries(entries: list[dict[str, Any]]) -> None:
    """Persist the Wired entries under ``data/news/``."""
    if not entries:
        logger.info("No Wired entries to save. Skipping.")
        return
    output_dir = os.path.join(get_project_root(), "data", "news")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "wired_latest.json")
    snapshot = os.path.join(output_dir, f"wired_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(entries)} Wired entries to {latest}")


def main() -> None:
    """Run the Wired ETL."""
    logger.info("Starting Wired RSS ETL")
    try:
        entries = fetch_wired()
        if not entries:
            logger.warning("No entries fetched from Wired. Exiting.")
            return
        save_wired_entries(entries)
        logger.info(f"Wired ETL complete: {len(entries)} articles.")
    except Exception as exc:
        logger.error(f"Wired ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
