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
logger = get_logger("MeneameETL")


def get_meneame_articles(max_retries: int = 3, retry_delay: int = 5) -> dict[str, list[dict[str, Any]]]:
    """Fetches articles from Meneame RSS feeds for general and tecnologia sections.

    Args:
        max_retries: Maximum number of retry attempts on connection failure
        retry_delay: Delay in seconds between retry attempts

    Returns:
        Dictionary mapping feed type ('general' or 'tecnologia') to lists of article dictionaries
    """
    rss_feeds = {
        "general": "https://www.meneame.net/rss",
        "tecnologia": "https://www.meneame.net/m/tecnologia/rss",
    }

    articles_by_feed: dict[str, list[dict[str, Any]]] = {key: [] for key in rss_feeds}

    for feed_type, rss_url in rss_feeds.items():
        logger.info(f"Processing Meneame {feed_type} RSS feed: {rss_url}")
        feed_articles: list[dict[str, Any]] = []

        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching RSS feed from {rss_url}")
                feed = feedparser.parse(rss_url)

                if not feed.entries:
                    logger.warning(f"No entries found in RSS feed from {rss_url}")
                    break

                for entry in feed.entries:
                    try:
                        article: dict[str, Any] = {
                            "title": getattr(entry, "title", ""),
                            "url": getattr(entry, "link", ""),
                            "published_at": getattr(entry, "published", "") or "",
                            "source": feed_type,
                            "article_id": getattr(entry, "id", "") or "",
                            "feed_source": rss_url,
                        }

                        # Handle author if available
                        if hasattr(entry, "author"):
                            article["author"] = entry.author
                        else:
                            article["author"] = feed_type

                        # Handle tags/categories if available
                        if hasattr(entry, "tags"):
                            article["tags"] = [tag.term for tag in entry.tags if hasattr(tag, "term")]
                        else:
                            article["tags"] = []

                        feed_articles.append(article)
                    except Exception as e:
                        logger.error(f"Error parsing RSS entry: {e}")
                        continue

                break
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {rss_url}: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Error fetching data from RSS feed {rss_url} after {max_retries} attempts: {e}")

        # Remove duplicates based on article_id and title
        unique_articles: dict[str, dict[str, Any]] = {}
        unique_titles: set = set()
        for art in feed_articles:
            title = art.get("title", "").strip()
            identifier = art.get("article_id") if art.get("article_id") else art.get("url", "")
            if title and title not in unique_titles and identifier not in unique_articles:
                unique_titles.add(title)
                unique_articles[identifier] = art

        articles_by_feed[feed_type] = list(unique_articles.values())

    return articles_by_feed


def process_meneame_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Process and transform Meneame articles into a standardized format.

    Args:
        articles: List of raw article dictionaries

    Returns:
        List of processed article dictionaries
    """
    logger.info(f"Processing {len(articles)} Meneame articles")
    processed_articles: list[dict[str, Any]] = []

    for article in articles:
        try:
            processed_article: dict[str, Any] = {
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "source": article.get("source", ""),
                "published_at": article.get("published_at", ""),
                "metadata": {
                    "api_source": "rss",
                    "processed_at": datetime.now().isoformat(),
                    "article_id": article.get("article_id", ""),
                    "author": article.get("author", ""),
                    "tags": article.get("tags", []),
                    "feed_source": article.get("feed_source", ""),
                },
            }
            processed_articles.append(processed_article)
            logger.debug(f"Processed article: {processed_article['title']}")
        except Exception as e:
            logger.error(f"Error processing article: {e}")
            continue

    logger.info(f"Successfully processed {len(processed_articles)} Meneame articles")
    return processed_articles


def main():
    """Main function to fetch and process Meneame RSS feeds."""
    logger.info("Starting Meneame RSS ETL process")
    try:
        # Ensure output directory exists
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data/meneame")
        ensure_directories(["data/meneame"])

        # Get articles for each feed type
        articles_by_feed = get_meneame_articles()

        for feed_type, articles in articles_by_feed.items():
            if not articles:
                logger.warning(f"No articles retrieved for Meneame {feed_type}, skipping ETL for this feed")
                continue

            # Process articles
            processed_articles = process_meneame_articles(articles)

            # Save processed data as JSON and CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_file = os.path.join(output_dir, f"meneame_{feed_type}_{timestamp}.json")
            with open(json_file, "w") as f:
                json.dump(processed_articles, f, indent=2)
            latest_json = os.path.join(output_dir, f"meneame_{feed_type}_latest.json")
            with open(latest_json, "w") as f:
                json.dump(processed_articles, f, indent=2)

            # Also save CSV for easier viewing
            csv_file = os.path.join(output_dir, f"meneame_{feed_type}_{timestamp}.csv")
            import pandas as pd

            pd.DataFrame(processed_articles).to_csv(csv_file, index=False)
            latest_csv = os.path.join(output_dir, f"meneame_{feed_type}_latest.csv")
            pd.DataFrame(processed_articles).to_csv(latest_csv, index=False)

            logger.info(f"Saved {len(processed_articles)} processed articles for {feed_type} to {json_file} and {csv_file}")

    except Exception as e:
        logger.error(f"Error in Meneame ETL process: {e}", exc_info=True)


if __name__ == "__main__":
    logger.info("Meneame RSS ETL script started")
    main()
    logger.info("Meneame RSS ETL script completed")
