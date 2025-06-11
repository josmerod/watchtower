import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Any

import feedparser

# Add the project root to the path to ensure imports work correctly
from utils.file_system import ensure_directories, get_project_root
from utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("GoodDevsETL")


def get_gooddevs_articles(
    max_retries: int = 3, retry_delay: int = 5
) -> list[dict[str, Any]]:
    """Fetches articles from a curated list of tech authors and bloggers.

    Args:
        max_retries: Maximum number of retry attempts on connection failure
        retry_delay: Delay in seconds between retry attempts

    Returns:
        List of news article dictionaries
    """
    rss_urls = [
        "https://krebsonsecurity.com/feed/",
        "https://jvns.ca/atom.xml",
        "https://danluu.com/atom.xml",
        "https://simonwillison.net/atom/everything/",
        "https://stratechery.passport.online/feed/rss/CMaAXahiDxTEaGaQ9KeTh",
        "https://www.schneier.com/feed/atom/",
        "https://jacquesmattheij.com/rss.xml",
        "https://shkspr.mobi/blog/feed/atom",
        "http://blog.samaltman.com/posts.atom",
        "https://blog.codinghorror.com/rss",
        "https://drewdevault.com/blog/index.xml",
        "https://antirez.com/rss",
        "https://www.jeffgeerling.com/blog.xml",
        "https://fabiensanglard.net/rss.xml",
        "https://blog.jgc.org/feeds/posts/default",
        "https://www.reddit.com/domain/gwern.net/.rss",
        "https://martinfowler.com/feed.atom",
        "https://pluralistic.net/feed/",
        "https://dynomight.net/feed.xml",
        "https://mtlynch.io/index.xml",
        "https://blog.pragmaticengineer.com/feed/",
        "https://xeiaso.net/blog.rss",
        "https://www.astralcodexten.com/feed",
        "https://eli.thegreenplace.net/feeds/all.atom.xml",
        "https://xkcd.com/rss.xml",
        "https://longform.asmartbear.com/index.xml",
        "https://austinhenley.com/blog/feed.rss",
        "https://robertheaton.com/feed.xml",
        "https://cdn.jwz.org/blog/feed/",
        "https://www.marginalia.nu/log/index.xml",
        "https://calnewport.com/feed",
        "https://velvetshark.com/rss.xml",
        "https://tldr.tech/api/rss/tech",
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

                # Extract domain from the URL to use as a source identifier
                source_domain = re.search(r"https?://(?:www\.)?([^/]+)", rss_url)
                source = source_domain.group(1) if source_domain else "unknown"

                for entry in feed.entries:
                    try:
                        # Extract article data from the entry
                        article = {
                            "title": entry.title if hasattr(entry, "title") else "",
                            "url": entry.link if hasattr(entry, "link") else "",
                            "published_at": "",  # Will handle different date formats below
                            "source": source,
                            "author": "",  # Will try to extract below
                            "article_id": entry.id if hasattr(entry, "id") else "",
                            "feed_source": rss_url,
                        }

                        # Handle different date formats
                        if hasattr(entry, "published"):
                            article["published_at"] = entry.published
                        elif hasattr(entry, "updated"):
                            article["published_at"] = entry.updated

                        # Removed summary extraction to reduce noise

                        # Handle different author formats
                        if hasattr(entry, "author"):
                            article["author"] = entry.author
                        elif hasattr(entry, "author_detail") and hasattr(
                            entry.author_detail, "name"
                        ):
                            article["author"] = entry.author_detail.name
                        else:
                            # Use domain as fallback for author
                            article["author"] = source

                        # Extract tags/categories if available
                        if hasattr(entry, "tags"):
                            article["tags"] = [
                                tag.term for tag in entry.tags if hasattr(tag, "term")
                            ]
                        elif hasattr(entry, "categories"):
                            article["tags"] = entry.categories
                        else:
                            article["tags"] = []

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

    # Remove duplicates based on article_id and title
    unique_articles = {}
    unique_titles = set()

    for article in articles:
        # First check if we've seen this title before
        title = article.get("title", "").strip()
        article_id = article.get("article_id", "")
        url = article.get("url", "")

        # Use URL as a fallback ID if article_id is empty
        identifier = article_id if article_id else url

        if title and title not in unique_titles and identifier not in unique_articles:
            unique_titles.add(title)
            unique_articles[identifier] = article

    articles = list(unique_articles.values())
    logger.info(f"Retrieved {len(articles)} unique articles from author RSS feeds")
    return articles


def process_gooddevs_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Process and transform articles into a standardized format.

    Args:
        articles: List of raw article dictionaries

    Returns:
        List of processed article dictionaries
    """
    logger.info(f"Processing {len(articles)} articles from tech authors")
    processed_articles = []

    for article in articles:
        try:
            processed_article = {
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "source": article.get("source", "unknown"),
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
            logger.error(f"Error processing article: {e!s}")
            continue

    logger.info(f"Successfully processed {len(processed_articles)} articles")
    return processed_articles


def main():
    """Main function to fetch and process articles from top tech authors."""
    logger.info("Starting Good Devs RSS ETL process")
    try:
        # Ensure output directory exists
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data/gooddevs")
        ensure_directories(["data/gooddevs"])

        # Get articles from the RSS feeds
        articles = get_gooddevs_articles()

        if not articles:
            logger.warning("No articles retrieved, ETL process cannot continue")
            return

        # Process the articles
        processed_articles = process_gooddevs_articles(articles)

        # Save to JSON file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"gooddevs_{timestamp}.json")
        with open(output_file, "w") as f:
            json.dump(processed_articles, f, indent=2)
        logger.debug(f"Saved JSON data to {output_file}")

        # Also save latest version
        latest_file = os.path.join(output_dir, "gooddevs_latest.json")
        with open(latest_file, "w") as f:
            json.dump(processed_articles, f, indent=2)

        # Also save as CSV for easier viewing
        csv_file = os.path.join(output_dir, f"gooddevs_{timestamp}.csv")
        import pandas as pd

        pd.DataFrame(processed_articles).to_csv(csv_file, index=False)
        logger.debug(f"Saved CSV data to {csv_file}")

        # Save latest CSV version
        latest_csv = os.path.join(output_dir, "gooddevs_latest.csv")
        pd.DataFrame(processed_articles).to_csv(latest_csv, index=False)

        logger.info(
            f"Saved {len(processed_articles)} processed articles to {output_file} and {csv_file}"
        )

    except Exception as e:
        logger.error(f"Error in Good Devs ETL process: {e!s}", exc_info=True)


if __name__ == "__main__":
    logger.info("Good Devs RSS ETL script started")
    # Run the main function
    main()
    logger.info("Good Devs RSS ETL script completed")
