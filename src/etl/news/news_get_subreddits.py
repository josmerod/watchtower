# src/etl/news/news_get_subreddits.py
import json
import os
import sys
import time
from datetime import datetime
from typing import Any

import requests

# Ensure project root is on path
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("SubredditsETL")

# List of subreddits to scrape
SUBREDDITS: list[str] = ["programming", "MachineLearning", "datascience"]


def get_subreddits_posts(limit: int = 50) -> list[dict[str, Any]]:
    """Fetches hot posts from specified subreddits using Reddit's public JSON endpoints.

    Args:
        limit: Maximum number of posts to retrieve per subreddit.

    Returns:
        List of post dictionaries with metadata.
    """
    headers = {"User-Agent": "watchtower-bot/0.1"}
    posts: list[dict[str, Any]] = []

    for subreddit in SUBREDDITS:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
        try:
            logger.info(f"Fetching subreddit: {subreddit}")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            for child in data.get("data", {}).get("children", []):
                p = child.get("data", {})
                post = {
                    "subreddit": subreddit,
                    "title": p.get("title"),
                    "url": p.get("url"),
                    "created_utc": datetime.fromtimestamp(
                        p.get("created_utc", 0), datetime.UTC
                    ).isoformat(),
                    "score": p.get("score"),
                    "num_comments": p.get("num_comments"),
                }
                posts.append(post)
            # Respect Reddit rate limits
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error fetching {subreddit}: {e}")

    logger.info(f"Retrieved {len(posts)} posts from subreddits")
    return posts


def save_subreddit_posts(posts: list[dict[str, Any]]) -> None:
    """Saves subreddit posts to JSON and CSV in the data/news directory.

    Args:
        posts: List of subreddit post dictionaries.
    """
    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data/news")
    ensure_directories(["data/news"])

    json_path = os.path.join(output_dir, "subreddits.json")
    csv_path = os.path.join(output_dir, "subreddits.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2)

    import pandas as pd  # type: ignore

    pd.DataFrame(posts).to_csv(csv_path, index=False)

    logger.info(f"Saved subreddit posts to {json_path} and {csv_path}")


def main() -> None:
    """Main entry point for the subreddit scraping ETL process.
    """
    posts = get_subreddits_posts()
    save_subreddit_posts(posts)


if __name__ == "__main__":
    logger.info("Starting Subreddits ETL process")
    main()
    logger.info("Subreddits ETL process completed")
