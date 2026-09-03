"""Azure blog ETL — Microsoft Azure product and engineering announcements.

Fetches the Azure blog's RSS feed — service announcements, previews and GA
updates. Widens the radar's cloud coverage beyond the AWS-centric
cloud_updates aggregate (which has no Azure feed). Feeds the Tech Radar
tab's Cloud column (T-082).

Usage:
    uv run python -m src.etl.news.news_get_azure_blog

Output:
    data/news/azure_blog_latest.json (+ timestamped snapshot)
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

logger = get_logger("AzureBlogETL")

RSS_FEED = "https://azure.microsoft.com/en-us/blog/feed/"

# Keep the persisted file lean — the radar column shows at most 25 per source
# (and the feed itself currently only carries ~10 items).
MAX_ITEMS = 25


@with_retry
def fetch_azure_blog() -> list[dict[str, Any]]:
    """Fetch and parse the Azure blog RSS feed."""
    entries: list[dict[str, Any]] = []
    logger.info(f"Fetching Azure blog RSS feed from {RSS_FEED}")
    try:
        response = requests.get(RSS_FEED, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo:
            logger.warning(f"Feed parse warning: {feed.bozo_exception}")
    except requests.RequestException as exc:
        logger.error(f"Could not fetch the Azure blog feed: {exc}")
        return entries

    for entry in feed.entries[:MAX_ITEMS]:
        published = _parse_date(entry.get("published", ""))
        summary = ""
        if hasattr(entry, "summary") and entry.summary:
            summary = _clean_summary(entry.summary)
        author = ""
        if hasattr(entry, "author") and entry.author:
            author = entry.author
        entries.append(
            {
                "source": "azure_blog",
                "source_category": "cloud",
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": published,
                "summary": summary[:500],
                "author": author,
                "categories": [t.get("term", "") for t in getattr(entry, "tags", [])],
                "guid": entry.get("id", ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "azure.microsoft.com",
                "content_type": "news_article",
                "language": "en",
                "region": "global",
            }
        )
    logger.info(f"Retrieved {len(entries)} items from the Azure blog feed")
    return entries


def _clean_summary(raw_html: str) -> str:
    """Strip HTML and drop the blog's trailing ``The post … appeared first in`` footer."""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = re.sub(r"\s+", " ", text).strip()
    if " The post " in text:
        text = text.split(" The post ")[0].strip()
    return text


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


def save_azure_blog_entries(entries: list[dict[str, Any]]) -> None:
    """Persist the Azure blog entries under ``data/news/``."""
    if not entries:
        logger.info("No Azure blog entries to save. Skipping.")
        return
    output_dir = os.path.join(get_project_root(), "data", "news")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "azure_blog_latest.json")
    snapshot = os.path.join(output_dir, f"azure_blog_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(entries)} Azure blog entries to {latest}")


def main() -> None:
    """Run the Azure blog ETL."""
    logger.info("Starting Azure blog RSS ETL")
    try:
        entries = fetch_azure_blog()
        if not entries:
            logger.warning("No entries fetched from the Azure blog. Exiting.")
            return
        save_azure_blog_entries(entries)
        logger.info(f"Azure blog ETL complete: {len(entries)} articles.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"Azure blog ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
