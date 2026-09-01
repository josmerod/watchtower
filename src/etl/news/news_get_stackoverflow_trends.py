"""Stack Overflow Trends ETL Module

Fetches hot Stack Overflow questions from the public StackExchange 2.3 API
(no key required) and writes them in the standard news-item shape so the
Knowledge Garden "Stack Overflow" subtab has data again.

Usage:
    uv run python src/etl/news/news_get_stackoverflow_trends.py

Output:
    - JSON file: data/stackoverflow_trends/stackoverflow_trends_latest.json
    - CSV file: data/stackoverflow_trends/stackoverflow_trends_latest.csv
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Any

import requests

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("StackOverflowTrendsETL")

API_URL = "https://api.stackexchange.com/2.3/questions"
SOURCE_NAME = "stackoverflow.com"
HEADERS = {"User-Agent": "WatchtowerBot/1.0 (https://github.com/josmerod/watchtower)"}


def get_stackoverflow_questions(pagesize: int = 50, max_retries: int = 3, retry_delay: int = 5) -> list[dict[str, Any]]:
    """Fetch hot Stack Overflow questions from the public API.

    The unauthenticated quota is 300 requests/day per IP, which is far above
    what a single daily run needs.

    Args:
        pagesize: Number of questions to fetch (max 100).
        max_retries: Maximum number of retry attempts on connection failure.
        retry_delay: Delay in seconds between retry attempts.

    Returns:
        List of question dictionaries in the standard news-item shape.
    """
    params: dict[str, str | int] = {"order": "desc", "sort": "hot", "site": "stackoverflow", "pagesize": pagesize}

    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching hot Stack Overflow questions from {API_URL}")
            resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
            raw_items = payload.get("items", [])
            break
        except (requests.RequestException, ValueError) as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e!s}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error(f"Error fetching Stack Overflow data after {max_retries} attempts: {e!s}")
                return []

    questions: list[dict[str, Any]] = []
    for item in raw_items:
        try:
            created_ts = item.get("creation_date")
            published_at = datetime.fromtimestamp(created_ts, tz=timezone.utc).isoformat() if created_ts else ""
            questions.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "source": SOURCE_NAME,
                    "published_at": published_at,
                    "score": item.get("score", 0),
                    "num_comments": item.get("answer_count", 0),
                    "tags": item.get("tags", []),
                    "summary": f"Score {item.get('score', 0)} · {'answered' if item.get('is_answered') else 'unanswered'} · views {item.get('view_count', 0)}",
                    "metadata": {
                        "api_source": "stackexchange_2.3",
                        "processed_at": datetime.now().isoformat(),
                    },
                }
            )
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError, OSError) as e:
            logger.error(f"Error parsing Stack Overflow question: {e!s}")

    logger.info(f"Retrieved {len(questions)} Stack Overflow questions")
    return questions


def main():
    """Main function to fetch and save Stack Overflow trending questions."""
    logger.info("Starting Stack Overflow Trends ETL process")
    try:
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "stackoverflow_trends")
        ensure_directories(["data/stackoverflow_trends"])

        questions = get_stackoverflow_questions()
        if not questions:
            logger.warning("No questions retrieved, ETL process cannot continue")
            return

        output_file = os.path.join(output_dir, "stackoverflow_trends_latest.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(questions)} questions to {output_file}")

        csv_file = os.path.join(output_dir, "stackoverflow_trends_latest.csv")
        import pandas as pd

        pd.DataFrame(questions).to_csv(csv_file, index=False)
        logger.info(f"Saved CSV data to {csv_file}")
    except Exception as e:  # broad by design: whole-pipeline wrapper (network fetch + parse + save) incl. pandas save
        logger.error(f"Error in Stack Overflow Trends ETL process: {e!s}", exc_info=True)


if __name__ == "__main__":
    logger.info("Stack Overflow Trends ETL script started")
    main()
    logger.info("Stack Overflow Trends ETL script completed")
