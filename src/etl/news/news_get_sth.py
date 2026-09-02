"""ServeTheHome ETL — server and homelab hardware news.

Fetches ServeTheHome's RSS feed — server hardware reviews, chip/roadmap
coverage and homelab gear, a natural sibling to Phoronix for the Unraid
audience. Feeds the Tech Radar tab's Linux/Hardware column (T-078).

Usage:
    uv run python -m src.etl.news.news_get_sth

Output:
    data/news/servethehome_latest.json (+ timestamped snapshot)
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

logger = get_logger("ServeTheHomeETL")

RSS_FEED = "https://www.servethehome.com/feed/"

# Keep the persisted file lean — the radar column shows at most 25 per source
# (and the feed itself currently only carries a handful of items).
MAX_ITEMS = 25


@with_retry
def fetch_servethehome() -> list[dict[str, Any]]:
    """Fetch and parse the ServeTheHome RSS feed."""
    entries: list[dict[str, Any]] = []
    logger.info(f"Fetching ServeTheHome RSS feed from {RSS_FEED}")
    try:
        response = requests.get(RSS_FEED, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo:
            logger.warning(f"Feed parse warning: {feed.bozo_exception}")
    except requests.RequestException as exc:
        logger.error(f"Could not fetch the ServeTheHome feed: {exc}")
        return entries

    for entry in feed.entries[:MAX_ITEMS]:
        published = _parse_date(entry.get("published", ""))
        summary = ""
        if hasattr(entry, "summary") and entry.summary:
            summary = re.sub(r"<[^>]+>", "", entry.summary).strip()
        author = ""
        if hasattr(entry, "author") and entry.author:
            author = entry.author
        entries.append(
            {
                "source": "servethehome",
                "source_category": "server_hardware",
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": published,
                "summary": summary[:500],
                "author": author,
                "categories": [t.get("term", "") for t in getattr(entry, "tags", [])],
                "guid": entry.get("id", ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "servethehome",
                "content_type": "news_article",
                "language": "en",
                "region": "global",
            }
        )
    logger.info(f"Retrieved {len(entries)} items from the ServeTheHome feed")
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


def save_servethehome_entries(entries: list[dict[str, Any]]) -> None:
    """Persist the ServeTheHome entries under ``data/news/``."""
    if not entries:
        logger.info("No ServeTheHome entries to save. Skipping.")
        return
    output_dir = os.path.join(get_project_root(), "data", "news")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "servethehome_latest.json")
    snapshot = os.path.join(output_dir, f"servethehome_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(entries)} ServeTheHome entries to {latest}")


def main() -> None:
    """Run the ServeTheHome ETL."""
    logger.info("Starting ServeTheHome RSS ETL")
    try:
        entries = fetch_servethehome()
        if not entries:
            logger.warning("No entries fetched from ServeTheHome. Exiting.")
            return
        save_servethehome_entries(entries)
        logger.info(f"ServeTheHome ETL complete: {len(entries)} articles.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"ServeTheHome ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
