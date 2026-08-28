"""The New Stack ETL Module

Fetches The New Stack RSS feed (cloud-native, infrastructure, dev tools) for
the Technology Radar tab. No API key required.

Usage:
    uv run python src/etl/news/news_get_thenewstack.py

Output:
    - JSON file: data/thenewstack/thenewstack_news.json
    - CSV file: data/thenewstack/thenewstack_news.csv
"""

import json
import os
import time
from datetime import datetime
from typing import Any

import feedparser

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("TheNewStackETL")

RSS_URL = "https://thenewstack.io/feed/"
SOURCE_NAME = "thenewstack.io"


def get_thenewstack_articles(max_retries: int = 3, retry_delay: int = 5) -> list[dict[str, Any]]:
    """Fetch articles from The New Stack RSS feed."""
    entries = []
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching RSS feed from {RSS_URL}")
            feed = feedparser.parse(RSS_URL)
            entries = feed.entries or []
            break
        except Exception as e:  # broad by design: feedparser network fetch + parse of external feed (retry loop)
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e!s}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error(f"Error fetching The New Stack after {max_retries} attempts: {e!s}")

    articles: list[dict[str, Any]] = []
    for entry in entries:
        try:
            articles.append(
                {
                    "title": getattr(entry, "title", ""),
                    "url": getattr(entry, "link", ""),
                    "published_at": getattr(entry, "published", getattr(entry, "updated", "")),
                    "source": SOURCE_NAME,
                    "summary": getattr(entry, "summary", ""),
                    "metadata": {"api_source": "thenewstack_rss", "processed_at": datetime.now().isoformat()},
                }
            )
        except (AttributeError, KeyError, TypeError) as e:
            logger.error(f"Error parsing The New Stack entry: {e!s}")

    logger.info(f"Retrieved {len(articles)} The New Stack articles")
    return articles


def main():
    """Main function to fetch and save The New Stack articles."""
    logger.info("Starting The New Stack ETL process")
    try:
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "thenewstack")
        ensure_directories(["data/thenewstack"])

        articles = get_thenewstack_articles()
        if not articles:
            logger.warning("No articles retrieved, ETL process cannot continue")
            return

        output_file = os.path.join(output_dir, "thenewstack_news.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(articles)} articles to {output_file}")

        csv_file = os.path.join(output_dir, "thenewstack_news.csv")
        import pandas as pd

        pd.DataFrame(articles).to_csv(csv_file, index=False)
        logger.info(f"Saved CSV data to {csv_file}")
    except Exception as e:  # broad by design: whole-pipeline wrapper (network fetch + parse + save) incl. pandas save
        logger.error(f"Error in The New Stack ETL process: {e!s}", exc_info=True)


if __name__ == "__main__":
    main()
