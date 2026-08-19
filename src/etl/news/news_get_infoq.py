"""InfoQ ETL Module

Fetches the InfoQ feed (software engineering, architecture, culture) for the
Technology Radar tab. No API key required.

Usage:
    uv run python src/etl/news/news_get_infoq.py

Output:
    - JSON file: data/infoq/infoq_news.json
    - CSV file: data/infoq/infoq_news.csv
"""

import json
import os
import time
from datetime import datetime
from typing import Any

import feedparser

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("InfoQETL")

RSS_URL = "https://feed.infoq.com/"
SOURCE_NAME = "infoq.com"


def get_infoq_articles(max_retries: int = 3, retry_delay: int = 5) -> list[dict[str, Any]]:
    """Fetch articles from the InfoQ RSS feed."""
    entries = []
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching RSS feed from {RSS_URL}")
            feed = feedparser.parse(RSS_URL)
            entries = feed.entries or []
            break
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e!s}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error(f"Error fetching InfoQ after {max_retries} attempts: {e!s}")

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
                    "metadata": {"api_source": "infoq_rss", "processed_at": datetime.now().isoformat()},
                }
            )
        except Exception as e:
            logger.error(f"Error parsing InfoQ entry: {e!s}")

    logger.info(f"Retrieved {len(articles)} InfoQ articles")
    return articles


def main():
    """Main function to fetch and save InfoQ articles."""
    logger.info("Starting InfoQ ETL process")
    try:
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "infoq")
        ensure_directories(["data/infoq"])

        articles = get_infoq_articles()
        if not articles:
            logger.warning("No articles retrieved, ETL process cannot continue")
            return

        output_file = os.path.join(output_dir, "infoq_news.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(articles)} articles to {output_file}")

        csv_file = os.path.join(output_dir, "infoq_news.csv")
        import pandas as pd

        pd.DataFrame(articles).to_csv(csv_file, index=False)
        logger.info(f"Saved CSV data to {csv_file}")
    except Exception as e:
        logger.error(f"Error in InfoQ ETL process: {e!s}", exc_info=True)


if __name__ == "__main__":
    main()
