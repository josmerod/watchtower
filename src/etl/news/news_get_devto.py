"""Dev.to ETL Module

Fetches top articles from the public Dev.to API (no key required) and writes
them in the standard news-item shape so the Knowledge Garden "Dev.to" subtab
has data again.

Usage:
    uv run python src/etl/news/news_get_devto.py

Output:
    - JSON file: data/devto/devto.json
    - CSV file: data/devto/devto.csv
"""

import json
import os
import time
from datetime import datetime
from typing import Any

import requests

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("DevtoETL")

API_URL = "https://dev.to/api/articles"
SOURCE_NAME = "dev.to"
HEADERS = {"User-Agent": "WatchtowerBot/1.0 (https://github.com/josmerod/watchtower)"}


def get_devto_articles(per_page: int = 50, max_retries: int = 3, retry_delay: int = 5) -> list[dict[str, Any]]:
    """Fetch the top Dev.to articles from the public API.

    Args:
        per_page: Number of articles to fetch (max 1000 per API docs).
        max_retries: Maximum number of retry attempts on connection failure.
        retry_delay: Delay in seconds between retry attempts.

    Returns:
        List of article dictionaries in the standard news-item shape.
    """
    params = {"top": 1, "per_page": per_page}

    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching Dev.to top articles from {API_URL}")
            resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            raw_articles = resp.json()
            break
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e!s}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error(f"Error fetching Dev.to data after {max_retries} attempts: {e!s}")
                return []

    articles: list[dict[str, Any]] = []
    for item in raw_articles:
        try:
            articles.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "source": SOURCE_NAME,
                    "published_at": item.get("published_at", ""),
                    "author": (item.get("user") or {}).get("username", ""),
                    "score": item.get("positive_reactions_count", 0),
                    "num_comments": item.get("comments_count", 0),
                    "tags": item.get("tag_list", []),
                    "summary": item.get("description", ""),
                    "metadata": {
                        "api_source": "devto_public_api",
                        "processed_at": datetime.now().isoformat(),
                    },
                }
            )
        except (KeyError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"Error parsing Dev.to article: {e!s}")

    logger.info(f"Retrieved {len(articles)} Dev.to articles")
    return articles


def main():
    """Main function to fetch and save Dev.to articles."""
    logger.info("Starting Dev.to ETL process")
    try:
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "devto")
        ensure_directories(["data/devto"])

        articles = get_devto_articles()
        if not articles:
            logger.warning("No articles retrieved, ETL process cannot continue")
            return

        output_file = os.path.join(output_dir, "devto.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(articles)} articles to {output_file}")

        csv_file = os.path.join(output_dir, "devto.csv")
        import pandas as pd

        pd.DataFrame(articles).to_csv(csv_file, index=False)
        logger.info(f"Saved CSV data to {csv_file}")
    except Exception as e:  # broad by design: whole-pipeline wrapper (network fetch + parse + save) incl. pandas save
        logger.error(f"Error in Dev.to ETL process: {e!s}", exc_info=True)


if __name__ == "__main__":
    logger.info("Dev.to ETL script started")
    main()
    logger.info("Dev.to ETL script completed")
