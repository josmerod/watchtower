"""Hacker News ETL Module

This module fetches and processes news articles from Hacker News using the official Firebase API.
It replaces the previous RSS-based implementation for better reliability and data richness.

Usage:
    python src/etl/news/news_get_ycombinator.py

Output:
    - JSON file: data/hackernews/hackernews.json
    - CSV file: data/hackernews/hackernews.csv
"""

import json
import os
import time
from datetime import datetime
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add the project root to the path to ensure imports work correctly
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("YCombinatorETL")

from src.utils.retry import with_retry


def create_session() -> requests.Session:
    """Create a requests session with retry strategy and proper headers."""
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set headers
    session.headers.update(
        {
            "User-Agent": "Watchtower-ETL/1.0 (HackerNews Main Analytics)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )

    return session


@with_retry
def get_ycombinator_data(max_stories: int = 150) -> list[dict[str, Any]]:
    """Fetches news articles from Hacker News API.

    Args:
        max_stories: Maximum number of stories to fetch and process

    Returns:
        List of news article dictionaries
    """
    base_url = "https://hacker-news.firebaseio.com/v0"
    session = create_session()
    articles = []

    try:
        # Get top stories IDs
        logger.info("Fetching top stories from Hacker News API")
        response = session.get(f"{base_url}/topstories.json", timeout=30)
        response.raise_for_status()

        story_ids = response.json()
        logger.info(f"Retrieved {len(story_ids)} top story IDs")

        # Process stories
        processed_count = 0

        for story_id in story_ids:
            if processed_count >= max_stories:
                break

            try:
                # Get story details
                story_response = session.get(f"{base_url}/item/{story_id}.json", timeout=30)
                story_response.raise_for_status()
                story_data = story_response.json()

                if not story_data:
                    continue

                # Skip if no URL (e.g. Ask HN or text-only posts, unless we want them too?
                # The original script prioritized links. We'll keep both but ensure URL field exists)

                title = story_data.get("title", "")
                url = story_data.get("url", "")

                # If no external URL, use the HN item URL
                if not url:
                    url = f"https://news.ycombinator.com/item?id={story_id}"

                published_at = datetime.fromtimestamp(story_data.get("time", 0)).isoformat()

                article = {
                    "title": title,
                    "url": url,
                    "published_at": published_at,
                    "source": "news.ycombinator.com",  # Default source
                    "hn_id": str(story_id),
                    "points": story_data.get("score", 0),
                    "comments_url": f"https://news.ycombinator.com/item?id={story_id}",
                    "comments_count": story_data.get("descendants", 0),
                    "author": story_data.get("by", ""),
                }

                # Extract domain for source field if possible
                if "url" in story_data:
                    try:
                        from urllib.parse import urlparse

                        domain = urlparse(story_data["url"]).netloc
                        if domain:
                            article["source"] = domain.replace("www.", "")
                    except Exception:
                        pass

                articles.append(article)
                processed_count += 1
                logger.debug(f"Processed story: {title}")

                # Be nice to the API
                time.sleep(0.05)

            except Exception as e:
                logger.warning(f"Error fetching story {story_id}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error fetching data from Hacker News API: {e}", exc_info=True)
        return []

    logger.info(f"Retrieved {len(articles)} articles from Hacker News")
    return articles


def process_ycombinator_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Process and transform HN articles into a standardized format.

    This function primarily adds metadata wrapping as the API extraction
    is already cleaner than RSS.
    """
    logger.info(f"Processing {len(articles)} Hacker News articles")
    processed_articles = []

    for article in articles:
        try:
            processed_article = {
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "source": article.get("source", "news.ycombinator.com"),
                "published_at": article.get("published_at", ""),
                "metadata": {
                    "api_source": "hackernews_api",
                    "processed_at": datetime.now().isoformat(),
                    "hn_id": article.get("hn_id", ""),
                    "points": article.get("points", 0),
                    "comments_url": article.get("comments_url", ""),
                    "comments_count": article.get("comments_count", 0),
                    "author": article.get("author", ""),
                },
            }
            processed_articles.append(processed_article)
        except Exception as e:
            logger.error(f"Error processing article: {e!s}")
            continue

    logger.info(f"Successfully processed {len(processed_articles)} articles")
    return processed_articles


def main():
    """Main function to fetch and process Hacker News articles."""
    logger.info("Starting Hacker News ETL process (API version)")
    try:
        # Ensure output directory exists
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data/hackernews")
        ensure_directories(["data/hackernews"])

        # Get articles from the API
        articles = get_ycombinator_data()

        if not articles:
            logger.warning("No articles retrieved, ETL process cannot continue")
            return

        # Process the articles
        processed_articles = process_ycombinator_articles(articles)

        # Save to JSON file
        output_file = os.path.join(output_dir, "hackernews.json")
        with open(output_file, "w") as f:
            json.dump(processed_articles, f, indent=2)
        logger.debug(f"Saved JSON data to {output_file}")

        # Also save as CSV for easier viewing
        csv_file = os.path.join(output_dir, "hackernews.csv")
        import pandas as pd

        # Create a flattened version for CSV
        csv_data = []
        for item in processed_articles:
            flat = {
                "title": item["title"],
                "url": item["url"],
                "source": item["source"],
                "published_at": item["published_at"],
                "points": item["metadata"]["points"],
                "comments_count": item["metadata"]["comments_count"],
                "comments_url": item["metadata"]["comments_url"],
            }
            csv_data.append(flat)

        pd.DataFrame(csv_data).to_csv(csv_file, index=False)
        logger.debug(f"Saved CSV data to {csv_file}")

        logger.info(f"Saved {len(processed_articles)} processed articles to {output_file} and {csv_file}")

    except Exception as e:
        logger.error(f"Error in Hacker News ETL process: {e!s}", exc_info=True)


if __name__ == "__main__":
    logger.info("Hacker News ETL script started")
    main()
    logger.info("Hacker News ETL script completed")
