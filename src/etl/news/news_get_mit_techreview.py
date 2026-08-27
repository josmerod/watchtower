"""MIT Technology Review ETL — emerging-technology analysis and research.

Fetches MIT Tech Review's RSS feed — research-grade coverage of AI, biotech,
compute, and climate tech. Feeds the Tech Radar tab's Emerging Tech column.

Usage:
    uv run python -m src.etl.news.news_get_mit_techreview

Output:
    data/news/mit_techreview_latest.json (+ timestamped snapshot)
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

logger = get_logger("MITTechReviewETL")

RSS_FEED = "https://www.technologyreview.com/feed/"


@with_retry
def fetch_mit_techreview() -> list[dict[str, Any]]:
    """Fetch and parse the MIT Technology Review RSS feed."""
    entries: list[dict[str, Any]] = []
    logger.info(f"Fetching MIT Tech Review RSS feed from {RSS_FEED}")
    try:
        response = requests.get(RSS_FEED, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo:
            logger.warning(f"Feed parse warning: {feed.bozo_exception}")
    except requests.RequestException as exc:
        logger.error(f"Could not fetch the MIT Tech Review feed: {exc}")
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
                "source": "mit_techreview",
                "source_category": "emerging_tech",
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": published,
                "summary": summary[:500],
                "author": authors,
                "categories": [t.get("term", "") for t in getattr(entry, "tags", [])],
                "guid": entry.get("id", ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "technologyreview",
                "content_type": "news_article",
                "language": "en",
                "region": "global",
            }
        )
    logger.info(f"Retrieved {len(entries)} items from the MIT Tech Review feed")
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


def save_mit_techreview_entries(entries: list[dict[str, Any]]) -> None:
    """Persist the MIT Tech Review entries under ``data/news/``."""
    if not entries:
        logger.info("No MIT Tech Review entries to save. Skipping.")
        return
    output_dir = os.path.join(get_project_root(), "data", "news")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "mit_techreview_latest.json")
    snapshot = os.path.join(output_dir, f"mit_techreview_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(entries)} MIT Tech Review entries to {latest}")


def main() -> None:
    """Run the MIT Tech Review ETL."""
    logger.info("Starting MIT Tech Review RSS ETL")
    try:
        entries = fetch_mit_techreview()
        if not entries:
            logger.warning("No entries fetched from MIT Tech Review. Exiting.")
            return
        save_mit_techreview_entries(entries)
        logger.info(f"MIT Tech Review ETL complete: {len(entries)} articles.")
    except Exception as exc:
        logger.error(f"MIT Tech Review ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
