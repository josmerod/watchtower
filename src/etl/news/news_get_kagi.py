import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

import feedparser

# Add the project root to the path to ensure imports work correctly
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("KagiRSSETL")

# Kagi RSS feed URLs by category
KAGI_RSS_FEEDS: Dict[str, str] = {
    "world": "https://kite.kagi.com/world.xml",
    "usa": "https://kite.kagi.com/usa.xml",
    "business": "https://kite.kagi.com/business.xml",
    "science": "https://kite.kagi.com/science.xml",
    "gaming": "https://kite.kagi.com/gaming.xml",
    "ai": "https://kite.kagi.com/ai.xml",
    "europe": "https://kite.kagi.com/europe.xml",
    "spain": "https://kite.kagi.com/spain.xml",
}


def get_kagi_rss_data(
    max_retries: int = 3, retry_delay: int = 5
) -> Dict[str, List[Dict[str, Any]]]:
    """Fetches news articles from Kagi RSS feeds by category.

    Args:
        max_retries: Maximum number of retry attempts on connection failure
        retry_delay: Delay in seconds between retry attempts

    Returns:
        Dictionary mapping category names to lists of article dictionaries
    """
    all_articles = {}

    for category, url in KAGI_RSS_FEEDS.items():
        articles = []

        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching Kagi RSS feed for {category} from {url}")
                feed = feedparser.parse(url)

                if feed.bozo:
                    logger.warning(
                        f"Error parsing feed from Kagi {category}: {feed.bozo_exception}"
                    )
                    break

                if not feed.entries:
                    logger.warning(f"No entries found in Kagi RSS feed for {category}")
                    break

                logger.debug(
                    f"Found {len(feed.entries)} entries in Kagi {category} RSS feed"
                )

                for entry in feed.entries:
                    try:
                        # Extract basic article information
                        title = entry.get("title", "")
                        url_link = entry.get("link", "")

                        # Extract published date
                        published_at = ""
                        if hasattr(entry, "published"):
                            published_at = entry.published
                        elif hasattr(entry, "updated"):
                            published_at = entry.updated

                        # Extract description/summary
                        description = ""
                        if hasattr(entry, "summary"):
                            description = entry.summary
                        elif hasattr(entry, "description"):
                            description = entry.description

                        # Create article object
                        article = {
                            "title": title,
                            "url": url_link,
                            "published_at": published_at,
                            "source": f"kagi_{category}",
                            "category": category,
                            "description": description,
                        }

                        # Add any additional metadata
                        if hasattr(entry, "author"):
                            article["author"] = entry.author

                        if hasattr(entry, "tags") and entry.tags:
                            article["tags"] = [tag.term for tag in entry.tags]

                        articles.append(article)
                        logger.debug(f"Extracted Kagi {category} article: {title}")

                    except Exception as e:
                        logger.error(f"Error parsing Kagi {category} RSS entry: {e}")
                        continue

                # Break out of retry loop if successful
                break

            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed for Kagi {category}: {e}"
                )
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(
                        f"Error fetching Kagi {category} RSS feed after {max_retries} attempts: {e}"
                    )

        # Add a small delay between RSS feed requests to be respectful to the server
        time.sleep(1)

        all_articles[category] = articles
        logger.info(f"Retrieved {len(articles)} articles from Kagi {category} RSS feed")

    return all_articles


def process_kagi_articles(
    all_articles: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Process and transform Kagi articles into a standardized format.

    Args:
        all_articles: Dictionary mapping category names to lists of raw article dictionaries

    Returns:
        Dictionary mapping category names to lists of processed article dictionaries
    """
    processed_data = {}

    for category, articles in all_articles.items():
        logger.info(f"Processing {len(articles)} Kagi {category} articles")
        processed_articles = []

        for article in articles:
            try:
                processed_article = {
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", f"kagi_{category}"),
                    "published_at": article.get("published_at", ""),
                    "category": article.get("category", category),
                    "description": article.get("description", ""),
                    "metadata": {
                        "api_source": "kagi_rss",
                        "processed_at": datetime.now().isoformat(),
                        "feed_category": category,
                        "author": article.get("author", ""),
                        "tags": article.get("tags", []),
                    },
                }
                processed_articles.append(processed_article)
                logger.debug(
                    f"Processed Kagi {category} article: {processed_article['title']}"
                )

            except Exception as e:
                logger.error(f"Error processing Kagi {category} article: {e}")
                continue

        processed_data[category] = processed_articles
        logger.info(
            f"Successfully processed {len(processed_articles)} Kagi {category} articles"
        )

    return processed_data


def save_kagi_articles(processed_data: Dict[str, List[Dict[str, Any]]]) -> None:
    """Save processed Kagi articles to JSON files by category.

    Args:
        processed_data: Dictionary mapping category names to lists of processed article dictionaries
    """
    project_root = get_project_root()

    for category, articles in processed_data.items():
        if not articles:
            logger.info(
                f"No articles to save for Kagi {category}, skipping file generation"
            )
            continue

        # Create category-specific output directory
        output_dir = os.path.join(project_root, f"data/kagi_{category}")
        ensure_directories([f"data/kagi_{category}"])

        # Save to JSON file
        output_file = os.path.join(output_dir, f"kagi_{category}.json")
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(articles, f, indent=2, ensure_ascii=False)
            logger.info(
                f"Saved {len(articles)} Kagi {category} articles to {output_file}"
            )
        except Exception as e:
            logger.error(f"Error saving Kagi {category} articles to JSON: {e}")

        # Also save as CSV for easier viewing
        csv_file = os.path.join(output_dir, f"kagi_{category}.csv")
        try:
            import pandas as pd

            df = pd.DataFrame(articles)
            df.to_csv(csv_file, index=False, encoding="utf-8")
            logger.info(f"Saved Kagi {category} articles to {csv_file}")
        except ImportError:
            logger.warning(
                "pandas library not found. Skipping CSV generation for Kagi articles."
            )
        except Exception as e:
            logger.error(f"Error saving Kagi {category} articles to CSV: {e}")


def main():
    """Main function to fetch and process Kagi RSS articles."""
    logger.info("Starting Kagi RSS ETL process")
    try:
        # Get articles from all Kagi RSS feeds
        all_articles = get_kagi_rss_data()

        if not any(articles for articles in all_articles.values()):
            logger.warning(
                "No articles retrieved from any Kagi RSS feeds, ETL process cannot continue"
            )
            return

        # Process the articles
        processed_data = process_kagi_articles(all_articles)

        # Save articles by category
        save_kagi_articles(processed_data)

        total_articles = sum(len(articles) for articles in processed_data.values())
        logger.info(
            f"Kagi RSS ETL process completed successfully. Total articles processed: {total_articles}"
        )

    except Exception as e:
        logger.error(f"Error in Kagi RSS ETL process: {e}", exc_info=True)


if __name__ == "__main__":
    logger.info("Kagi RSS ETL script started")
    main()
    logger.info("Kagi RSS ETL script completed")
