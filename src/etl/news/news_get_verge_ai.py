"""The Verge AI ETL — AI news from The Verge's dedicated AI feed.

Fetches The Verge's artificial-intelligence RSS feed — coverage of AI
products, model releases, policy, and the companies driving them. Feeds the
Tech Radar tab's AI column.

Usage:
    uv run python -m src.etl.news.news_get_verge_ai

Output:
    data/news/verge_ai_latest.json (+ timestamped snapshot)
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

logger = get_logger("VergeAIETL")

RSS_FEED = "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"


@with_retry
def fetch_verge_ai() -> list[dict[str, Any]]:
    """Fetch and parse The Verge AI RSS feed."""
    entries: list[dict[str, Any]] = []
    logger.info(f"Fetching The Verge AI RSS feed from {RSS_FEED}")
    try:
        response = requests.get(RSS_FEED, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo:
            logger.warning(f"Feed parse warning: {feed.bozo_exception}")
    except requests.RequestException as exc:
        logger.error(f"Could not fetch The Verge AI feed: {exc}")
        return entries

    for entry in feed.entries:
        published_raw = entry.get("published", "")
        published = _parse_date(published_raw)
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
                "source": "verge_ai",
                "source_category": "ai_news",
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": published,
                "summary": summary[:500],
                "author": authors,
                "categories": [t.get("term", "") for t in getattr(entry, "tags", [])],
                "guid": entry.get("id", ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "theverge",
                "content_type": "news_article",
                "language": "en",
                "region": "global",
            }
        )
    logger.info(f"Retrieved {len(entries)} items from The Verge AI feed")
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


def save_verge_ai_entries(entries: list[dict[str, Any]]) -> None:
    """Persist The Verge AI entries under ``data/news/``."""
    if not entries:
        logger.info("No Verge AI entries to save. Skipping.")
        return
    output_dir = os.path.join(get_project_root(), "data", "news")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "verge_ai_latest.json")
    snapshot = os.path.join(output_dir, f"verge_ai_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(entries)} Verge AI entries to {latest}")


def main() -> None:
    """Run The Verge AI ETL."""
    logger.info("Starting The Verge AI RSS ETL")
    try:
        entries = fetch_verge_ai()
        if not entries:
            logger.warning("No entries fetched from The Verge AI. Exiting.")
            return
        save_verge_ai_entries(entries)
        logger.info(f"The Verge AI ETL complete: {len(entries)} articles.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"The Verge AI ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
