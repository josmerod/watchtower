"""ETL module for fetching Generative AI articles from Medium.

This module retrieves articles related to Generative AI, LLMs, and related
topics from various Medium RSS feeds. The fetched data is then
processed and saved into JSON and CSV files.
"""

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
logger = get_logger("MediumGenAIETL")


def get_medium_genai_data(
    max_retries: int = 3, retry_delay: int = 5
) -> list[dict[str, Any]]:
    """Fetches generative AI articles from Medium by parsing multiple RSS feeds.

    Args:
        max_retries: Maximum number of retry attempts on connection failure
        retry_delay: Delay in seconds between retry attempts

    Returns:
        List of news article dictionaries
    """
    rss_urls = [
        "https://medium.com/feed/tag/generative-ai",
        "https://medium.com/feed/tag/llm",
        "https://medium.com/feed/tag/genai",
        "https://medium.com/feed/tag/agents",
        "https://medium.com/feed/tag/ai",
        "https://medium.com/feed/tag/prompt-engineering",
        "https://medium.com/feed/tag/data-science",
        "https://medium.com/feed/tag/machine-learning",
        "https://medium.com/feed/tag/deep-learning",
        "https://medium.com/feed/tag/natural-language-processing",
        "https://medium.com/feed/tag/computer-vision",
        "https://medium.com/feed/tag/nlp",
    ]
    articles = []

    for rss_url in rss_urls:
        logger.info(f"Processing RSS feed: {rss_url}")

        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching RSS feed from {rss_url}")
                feed = feedparser.parse(rss_url)

                if not feed.entries:
                    logger.warning(f"No entries found in RSS feed from {rss_url}")
                    break

                logger.debug(
                    f"Found {len(feed.entries)} entries in RSS feed from {rss_url}"
                )

                for entry in feed.entries:
                    try:
                        # Extract article data from the entry
                        article = {
                            "title": entry.title if hasattr(entry, "title") else "",
                            "url": entry.link if hasattr(entry, "link") else "",
                            "published_at": (
                                entry.published if hasattr(entry, "published") else ""
                            ),
                            "source": "medium.com",
                            "author": entry.author if hasattr(entry, "author") else "",
                            "summary": (
                                entry.summary if hasattr(entry, "summary") else ""
                            ),
                            "medium_id": entry.id if hasattr(entry, "id") else "",
                            "feed_source": rss_url,
                        }

                        # Extract tags/categories if available
                        if hasattr(entry, "tags"):
                            article["tags"] = [
                                tag.term for tag in entry.tags if hasattr(tag, "term")
                            ]

                        # Extract source domain from entry
                        if hasattr(entry, "link"):
                            source_match = re.search(r"https?://([^/]+)", entry.link)
                            if source_match:
                                article["source"] = source_match.group(1)

                        articles.append(article)
                        logger.debug(f"Extracted article: {article['title']}")
                    except Exception as e:
                        logger.error(f"Error parsing RSS entry: {e!s}")
                        continue

                # Break out of retry loop if successful
                break

            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed for {rss_url}: {e!s}"
                )
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(
                        f"Error fetching data from RSS feed {rss_url} after {max_retries} attempts: {e!s}"
                    )

    # Remove duplicates based on medium_id and title
    unique_articles = {}
    unique_titles = set()

    for article in articles:
        # First check if we've seen this title before
        title = article.get("title", "").strip()
        medium_id = article.get("medium_id", "")

        if title and title not in unique_titles and medium_id not in unique_articles:
            unique_titles.add(title)
            unique_articles[medium_id] = article

    articles = list(unique_articles.values())
    logger.info(f"Retrieved {len(articles)} unique articles from Medium RSS feeds")
    return articles


def process_medium_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Process and transform Medium articles into a standardized format.

    Args:
        articles: List of raw article dictionaries from Medium

    Returns:
        List of processed article dictionaries
    """
    logger.info(f"Processing {len(articles)} Medium Generative AI articles")
    processed_articles = []

    for article in articles:
        try:
            processed_article = {
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "source": article.get("source", "medium.com"),
                "published_at": article.get("published_at", ""),
                "metadata": {
                    "api_source": "medium_rss",
                    "processed_at": datetime.now().isoformat(),
                    "medium_id": article.get("medium_id", ""),
                    "author": article.get("author", ""),
                    "tags": article.get("tags", []),
                    "summary": article.get("summary", ""),
                    "feed_source": article.get("feed_source", ""),
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
    """Main function to fetch and process Medium Generative AI articles."""
    logger.info("Starting Medium Generative AI ETL process")
    try:
        # Ensure output directory exists
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data/medium_genai")
        ensure_directories(["data/medium_genai"])

        # Get articles from the RSS feeds
        articles = get_medium_genai_data()

        if not articles:
            logger.warning("No articles retrieved, ETL process cannot continue")
            return

        # Process the articles
        processed_articles = process_medium_articles(articles)

        # Save to JSON file
        output_file = os.path.join(output_dir, "medium_genai.json")
        with open(output_file, "w") as f:
            json.dump(processed_articles, f, indent=2)
        logger.debug(f"Saved JSON data to {output_file}")

        # Also save as CSV for easier viewing
        csv_file = os.path.join(output_dir, "medium_genai.csv")
        import pandas as pd

        pd.DataFrame(processed_articles).to_csv(csv_file, index=False)
        logger.debug(f"Saved CSV data to {csv_file}")

        logger.info(
            f"Saved {len(processed_articles)} processed articles to {output_file} and {csv_file}"
        )

    except Exception as e:
        logger.error(f"Error in Medium Generative AI ETL process: {e!s}", exc_info=True)


if __name__ == "__main__":
    logger.info("Medium Generative AI ETL script started")
    # Run the main function
    main()
    logger.info("Medium Generative AI ETL script completed")
