"""tldr.tech ETL Module

Fetches the TLDR newsletter RSS feeds (Tech, AI, Data) and merges them into a
single file so the News tab renders one "tldr.tech" subtab with per-edition
source tags. No API key required.

Usage:
    uv run python src/etl/news/news_get_tldr.py

Output:
    - JSON file: data/tldr/tldr_news.json
    - CSV file: data/tldr/tldr_news.csv
"""

import json
import os
import time
from datetime import datetime
from typing import Any

import feedparser

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("TldrETL")

FEEDS: dict[str, str] = {
    "tldr.tech/tech": "https://tldr.tech/api/rss/tech",
    "tldr.tech/ai": "https://tldr.tech/api/rss/ai",
    "tldr.tech/data": "https://tldr.tech/api/rss/data",
}


def get_tldr_articles(max_retries: int = 3, retry_delay: int = 5) -> list[dict[str, Any]]:
    """Fetch and merge the TLDR newsletter feeds.

    Args:
        max_retries: Maximum number of retry attempts per feed.
        retry_delay: Delay in seconds between retry attempts.

    Returns:
        List of article dictionaries tagged with their edition source.
    """
    articles: list[dict[str, Any]] = []
    for source_name, url in FEEDS.items():
        feed = None
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching {url}")
                feed = feedparser.parse(url)
                if feed.entries:
                    break
                logger.warning(f"No entries in {url}")
                feed = None
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} for {source_name} failed: {e!s}")
                feed = None
                time.sleep(retry_delay)
        if feed is None:
            continue

        for entry in feed.entries:
            try:
                published = ""
                if hasattr(entry, "published"):
                    published = entry.published
                elif hasattr(entry, "updated"):
                    published = entry.updated
                articles.append(
                    {
                        "title": getattr(entry, "title", ""),
                        "url": getattr(entry, "link", ""),
                        "published_at": published,
                        "source": source_name,
                        "summary": getattr(entry, "summary", ""),
                        "metadata": {
                            "api_source": "tldr_rss",
                            "processed_at": datetime.now().isoformat(),
                        },
                    }
                )
            except Exception as e:
                logger.error(f"Error parsing entry from {source_name}: {e!s}")

    # Deduplicate by URL (same story can appear in several editions)
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for article in articles:
        key = article.get("url") or article.get("title", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(article)

    logger.info(f"Retrieved {len(unique)} unique TLDR articles from {len(FEEDS)} feeds")
    return unique


def main():
    """Main function to fetch and save TLDR articles."""
    logger.info("Starting tldr.tech ETL process")
    try:
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "tldr")
        ensure_directories(["data/tldr"])

        articles = get_tldr_articles()
        if not articles:
            logger.warning("No articles retrieved, ETL process cannot continue")
            return

        output_file = os.path.join(output_dir, "tldr_news.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(articles)} articles to {output_file}")

        csv_file = os.path.join(output_dir, "tldr_news.csv")
        import pandas as pd

        pd.DataFrame(articles).to_csv(csv_file, index=False)
        logger.info(f"Saved CSV data to {csv_file}")
    except Exception as e:
        logger.error(f"Error in tldr.tech ETL process: {e!s}", exc_info=True)


if __name__ == "__main__":
    main()
