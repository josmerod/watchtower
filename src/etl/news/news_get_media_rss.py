# src/etl/news/news_get_media_rss.py
import json
import os
import sys
from datetime import datetime
from typing import Any

import feedparser

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("MediaRSSETL")

# Mapping of source names to RSS feed URLs
RSS_FEEDS: dict[str, str] = {
    "ars_technica": "https://feeds.arstechnica.com/arstechnica/index",
    "the_verge": "https://www.theverge.com/rss/index.xml",
    "hackernoon": "https://hackernoon.com/feed",
}


def fetch_media_feeds() -> list[dict[str, Any]]:
    """Fetches and parses RSS feeds from specialized media sources.

    Returns:
        List of entries with metadata from each RSS feed.
    """
    entries: list[dict[str, Any]] = []

    for source, url in RSS_FEEDS.items():
        logger.info(f"Fetching RSS feed from {source} at {url}")
        feed = feedparser.parse(url)

        for entry in feed.entries:
            published_raw = entry.get("published", "")
            try:
                published = datetime.strptime(
                    published_raw, "%a, %d %b %Y %H:%M:%S %z"
                ).isoformat()
            except Exception:
                published = published_raw

            entries.append(
                {
                    "source": source,
                    "title": entry.get("title"),
                    "link": entry.get("link"),
                    "published": published,
                }
            )

    logger.info(f"Retrieved {len(entries)} items from media RSS feeds")
    return entries


def save_media_entries(entries: list[dict[str, Any]]) -> None:
    """Saves media RSS feed entries to JSON and CSV in the data/news directory.

    Args:
        entries: List of media RSS entry dictionaries.
    """
    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data/news")
    ensure_directories(["data/news"])

    json_path = os.path.join(output_dir, "media_rss.json")
    csv_path = os.path.join(output_dir, "media_rss.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)

    import pandas as pd  # type: ignore

    pd.DataFrame(entries).to_csv(csv_path, index=False)

    logger.info(f"Saved media RSS entries to {json_path} and {csv_path}")


def main() -> None:
    """Main entry point for the media RSS ETL process.
    """
    entries = fetch_media_feeds()
    save_media_entries(entries)


if __name__ == "__main__":
    logger.info("Starting Media RSS ETL process")
    main()
    logger.info("Media RSS ETL process completed")
