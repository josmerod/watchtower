import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Any

import feedparser

# Add the project root to the path to ensure imports work correctly
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("DevToETL")


def get_devto_data(
    max_retries: int = 3, retry_delay: int = 5
) -> list[dict[str, Any]]:
    """Fetches articles from Dev.to by parsing RSS feeds.

    Args:
        max_retries: Maximum number of retry attempts on connection failure
        retry_delay: Delay in seconds between retry attempts

    Returns:
        List of article dictionaries
    """
    rss_urls = [
        "https://dev.to/feed",  # Main feed
        "https://dev.to/feed/latest"  # Latest articles
    ]
    articles = []

    for url in rss_urls:
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching RSS feed from {url}")
                feed = feedparser.parse(url)

                if not feed.entries:
                    logger.warning(f"No entries found in RSS feed from {url}")
                    break

                logger.debug(
                    f"Found {len(feed.entries)} entries in RSS feed from {url}"
                )

                for entry in feed.entries:
                    try:
                        # Extract title
                        title = entry.title if hasattr(entry, "title") else ""

                        # Extract URL
                        article_url = entry.link if hasattr(entry, "link") else ""

                        # Extract author (creator)
                        author = ""
                        if hasattr(entry, "author"):
                            author = entry.author
                        elif hasattr(entry, "dc_creator"):
                            author = entry.dc_creator

                        # Extract published date
                        published_at = ""
                        if hasattr(entry, "published"):
                            published_at = entry.published
                        elif hasattr(entry, "pubDate"):
                            published_at = entry.pubDate

                        # Extract GUID/ID
                        article_id = ""
                        if hasattr(entry, "id"):
                            article_id = entry.id
                        elif hasattr(entry, "guid"):
                            article_id = entry.guid

                        # Extract categories/tags
                        tags = []
                        if hasattr(entry, "tags"):
                            tags = [tag.term for tag in entry.tags if hasattr(tag, "term")]

                        # Extract description/summary (clean HTML)
                        description = ""
                        if hasattr(entry, "summary"):
                            # Remove HTML tags from description for clean text
                            description = re.sub(r'<[^>]+>', '', entry.summary)
                            # Clean up extra whitespace
                            description = re.sub(r'\s+', ' ', description).strip()
                            # Limit description length
                            if len(description) > 500:
                                description = description[:500] + "..."

                        # Create article object
                        article = {
                            "title": title,
                            "url": article_url,
                            "author": author,
                            "published_at": published_at,
                            "source": "dev.to",
                            "article_id": article_id,
                            "tags": tags,
                            "description": description,
                        }

                        articles.append(article)
                        logger.debug(f"Extracted article: {title}")
                    except Exception as e:
                        logger.error(f"Error parsing RSS entry: {e!s}")
                        continue

                # Break out of retry loop if successful
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

        # Add a small delay between RSS feed requests to be respectful to the server
        time.sleep(1)

    # Remove duplicates based on article_id
    seen_ids = set()
    unique_articles = []
    for article in articles:
        if article["article_id"] not in seen_ids:
            unique_articles.append(article)
            seen_ids.add(article["article_id"])

    logger.info(f"Retrieved {len(unique_articles)} unique articles from Dev.to RSS feeds")
    return unique_articles


def process_devto_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Process and transform Dev.to articles into a standardized format.

    Args:
        articles: List of raw article dictionaries from Dev.to

    Returns:
        List of processed article dictionaries
    """
    logger.info(f"Processing {len(articles)} Dev.to articles")
    processed_articles = []

    for article in articles:
        try:
            processed_article = {
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "source": "dev.to",
                "published_at": article.get("published_at", ""),
                "description": article.get("description", ""),
                "metadata": {
                    "api_source": "devto_rss",
                    "processed_at": datetime.now().isoformat(),
                    "author": article.get("author", ""),
                    "article_id": article.get("article_id", ""),
                    "tags": article.get("tags", []),
                },
            }
            processed_articles.append(processed_article)
            logger.debug(f"Processed article: {processed_article['title']}")
        except Exception as e:
            logger.error(f"Error processing article: {e!s}")
            continue

    logger.info(f"Successfully processed {len(processed_articles)} articles")
    return processed_articles


def main():
    """Main function to fetch and process Dev.to articles."""
    logger.info("Starting Dev.to ETL process")
    try:
        # Ensure output directory exists
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data/devto")
        ensure_directories(["data/devto"])  # This should create /app/data/devto

        # Create a simple test file to verify directory creation and write access
        test_file_path = os.path.join(output_dir, "test_output.txt")
        try:
            with open(test_file_path, "w") as f_test:
                f_test.write("Test output from news_get_devto.py main()")
            logger.info(f"Successfully wrote test file to {test_file_path}")
        except Exception as e_test:
            logger.error(f"Failed to write test file to {test_file_path}: {e_test}")

        # Get articles from the RSS feeds
        articles = get_devto_data()

        if not articles:
            logger.warning("No articles retrieved, ETL process cannot continue")
            return

        # Process the articles
        processed_articles = process_devto_articles(articles)

        # Save to JSON file
        output_file = os.path.join(output_dir, "devto.json")
        with open(output_file, "w") as f:
            json.dump(processed_articles, f, indent=2)
        logger.debug(f"Saved JSON data to {output_file}")

        # Also save as CSV for easier viewing
        csv_file = os.path.join(output_dir, "devto.csv")
        import pandas as pd

        pd.DataFrame(processed_articles).to_csv(csv_file, index=False)
        logger.debug(f"Saved CSV data to {csv_file}")

        logger.info(
            f"Saved {len(processed_articles)} processed articles to {output_file} and {csv_file}"
        )

    except Exception as e:
        logger.error(f"Error in Dev.to ETL process: {e!s}", exc_info=True)


if __name__ == "__main__":
    logger.info("Dev.to ETL script started")
    # Run the main function
    main()
    logger.info("Dev.to ETL script completed")