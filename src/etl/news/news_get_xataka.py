"""Xataka ETL — Spain's biggest Spanish-language tech blog.

Fetches Xataka's main RSS feed — consumer tech, robotics/AI and science
coverage in Spanish, the dedicated per-source sibling of the multi-blog
``news_get_spanish_tech`` aggregate that feeds the News tab (that ETL mixes
Xataka with Hipertextual/Genbeta/WWWhat's new; this one gives Xataka its own
Tech Radar column, T-078).

Usage:
    uv run python -m src.etl.news.news_get_xataka

Output:
    data/news/xataka_latest.json (+ timestamped snapshot)
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

logger = get_logger("XatakaETL")

RSS_FEED = "https://www.xataka.com/index.xml"

# Keep the persisted file lean — the radar column shows at most 25 per source.
MAX_ITEMS = 25


@with_retry
def fetch_xataka() -> list[dict[str, Any]]:
    """Fetch and parse the Xataka RSS feed."""
    entries: list[dict[str, Any]] = []
    logger.info(f"Fetching Xataka RSS feed from {RSS_FEED}")
    try:
        response = requests.get(RSS_FEED, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo:
            logger.warning(f"Feed parse warning: {feed.bozo_exception}")
    except requests.RequestException as exc:
        logger.error(f"Could not fetch the Xataka feed: {exc}")
        return entries

    for entry in feed.entries[:MAX_ITEMS]:
        published = _parse_date(entry.get("published", ""))
        summary = ""
        if hasattr(entry, "summary") and entry.summary:
            # Xataka summaries open with a leading <img> tag — strip markup,
            # then drop any leading whitespace left behind.
            summary = re.sub(r"<[^>]+>", " ", entry.summary)
            summary = re.sub(r"\s+", " ", summary).strip()
        authors = ""
        if hasattr(entry, "authors") and entry.authors:
            authors = ", ".join(a.get("name", "") for a in entry.authors if isinstance(a, dict))
        elif hasattr(entry, "author") and entry.author:
            authors = entry.author
        entries.append(
            {
                "source": "xataka",
                "source_category": "tech_media_es",
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": published,
                "summary": summary[:500],
                "author": authors,
                "categories": [t.get("term", "") for t in getattr(entry, "tags", [])],
                "guid": entry.get("id", ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "xataka",
                "content_type": "news_article",
                "language": "es",
                "region": "es",
            }
        )
    logger.info(f"Retrieved {len(entries)} items from the Xataka feed")
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


def save_xataka_entries(entries: list[dict[str, Any]]) -> None:
    """Persist the Xataka entries under ``data/news/``."""
    if not entries:
        logger.info("No Xataka entries to save. Skipping.")
        return
    output_dir = os.path.join(get_project_root(), "data", "news")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "xataka_latest.json")
    snapshot = os.path.join(output_dir, f"xataka_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(entries)} Xataka entries to {latest}")


def main() -> None:
    """Run the Xataka ETL."""
    logger.info("Starting Xataka RSS ETL")
    try:
        entries = fetch_xataka()
        if not entries:
            logger.warning("No entries fetched from Xataka. Exiting.")
            return
        save_xataka_entries(entries)
        logger.info(f"Xataka ETL complete: {len(entries)} articles.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"Xataka ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
