"""KDnuggets ETL Module

This module fetches and processes news articles from KDnuggets using RSS feed.
It follows the same output structure as other news ETL scripts in the project.

Usage:
    python src/etl/news/news_get_kdnuggets.py

Output:
    - JSON file: data/kdnuggets/kdnuggets.json
    - CSV file: data/kdnuggets/kdnuggets.csv
"""

import json
import os
import time
from datetime import datetime
from typing import Any

import feedparser

# Add the project root to the path to ensure imports work correctly
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("KDnuggetsETL")


def get_kdnuggets_data(
    max_retries: int = 3, retry_delay: int = 5
) -> list[dict[str, Any]]:
    """Fetches news articles from KDnuggets by parsing the RSS feed.

    Args:
        max_retries: Maximum number of retry attempts on connection failure
        retry_delay: Delay in seconds between retry attempts

    Returns:
        List of news article dictionaries
    """
    rss_url = "https://www.kdnuggets.com/feed"
    articles: list[dict[str, Any]] = []

    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching RSS feed from {rss_url}")
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                logger.warning(f"No entries found in RSS feed from {rss_url}")
                break

            logger.debug(f"Found {len(feed.entries)} entries in RSS feed")

            for entry in feed.entries:
                try:
                    title = entry.title if hasattr(entry, "title") else ""
                    url = entry.link if hasattr(entry, "link") else ""
                    published_at = (
                        entry.published if hasattr(entry, "published") else ""
                    )
                    source = "kdnuggets.com"
                    article = {
                        "title": title,
                        "url": url,
                        "published_at": published_at,
                        "source": source,
                    }

                    # Add summary if available
                    if hasattr(entry, "summary"):
                        article["summary"] = entry.summary

                    # Add tags if available
                    if hasattr(entry, "tags"):
                        article["tags"] = [
                            tag.term for tag in entry.tags if hasattr(tag, "term")
                        ]

                    # Add unique id if available
                    if hasattr(entry, "id"):
                        article["kdnuggets_id"] = entry.id

                    articles.append(article)
                    logger.debug(f"Extracted article: {title}")
                except Exception as e:
                    logger.error(f"Error parsing RSS entry: {e!s}")
            break

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e!s}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(
                    f"Error fetching data from RSS feed after {max_retries} attempts: {e!s}"
                )

    # Deduplicate articles by id or title
    unique_articles: dict[str, dict[str, Any]] = {}
    unique_titles: set = set()
    for article in articles:
        uid = article.get("kdnuggets_id") or article.get("title", "").strip()
        if (
            uid
            and uid not in unique_articles
            and article.get("title", "").strip() not in unique_titles
        ):
            unique_articles[uid] = article
            unique_titles.add(article.get("title", "").strip())

    unique_list = list(unique_articles.values())
    logger.info(f"Retrieved {len(unique_list)} unique articles from KDnuggets RSS feed")
    return unique_list


def process_kdnuggets_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Process and transform KDnuggets articles into a standardized format.

    Args:
        articles: List of raw article dictionaries from KDnuggets

    Returns:
        List of processed article dictionaries
    """
    logger.info(f"Processing {len(articles)} KDnuggets articles")
    processed_articles: list[dict[str, Any]] = []

    for article in articles:
        try:
            processed_article = {
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "source": article.get("source", "kdnuggets.com"),
                "published_at": article.get("published_at", ""),
                "metadata": {
                    "api_source": "kdnuggets_rss",
                    "processed_at": datetime.now().isoformat(),
                },
            }

            # Include summary and tags in metadata if present
            if "summary" in article:
                processed_article["metadata"]["summary"] = article["summary"]
            if "tags" in article:
                processed_article["metadata"]["tags"] = article["tags"]

            processed_articles.append(processed_article)
            logger.debug(f"Processed article: {processed_article['title']}")
        except Exception as e:
            logger.error(f"Error processing article: {e!s}")
            continue

    logger.info(f"Successfully processed {len(processed_articles)} articles")
    return processed_articles


def main():
    """Main function to fetch and process KDnuggets articles."""
    logger.info("Starting KDnuggets ETL process")
    try:
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data/kdnuggets")
        ensure_directories(["data/kdnuggets"])

        articles = get_kdnuggets_data()
        if not articles:
            logger.warning("No articles retrieved, ETL process cannot continue")
            return

        processed_articles = process_kdnuggets_articles(articles)

        # Save to JSON file
        output_file = os.path.join(output_dir, "kdnuggets.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(processed_articles, f, indent=2)
        logger.debug(f"Saved JSON data to {output_file}")

        # Also save as CSV for easier viewing
        csv_file = os.path.join(output_dir, "kdnuggets.csv")
        import pandas as pd

        pd.DataFrame(processed_articles).to_csv(csv_file, index=False)
        logger.debug(f"Saved CSV data to {csv_file}")

        logger.info(
            f"Saved {len(processed_articles)} processed articles to {output_file} and {csv_file}"
        )
    except Exception as e:
        logger.error(f"Error in KDnuggets ETL process: {e!s}", exc_info=True)


if __name__ == "__main__":
    logger.info("KDnuggets ETL script started")
    main()
    logger.info("KDnuggets ETL script completed")
