"""
Ben's Bites ETL Module

This module fetches and processes news articles from Ben's Bites using the RSS feed.
It follows the same output structure as other news ETL scripts in the project.

Usage:
    python src/etl/news/news_get_bensbites.py

Output:
    - JSON file: data/bensbites/bensbites_news.json
    - CSV file: data/bensbites/bensbites_news.csv
"""

import os
import json
import sys
import time
import feedparser
from datetime import datetime
from typing import Dict, List, Any

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories, get_project_root

# Initialize logger for this module
logger = get_logger("BensBitesETL")


def get_bensbites_data(max_retries: int = 3, retry_delay: int = 5) -> List[Dict[str, Any]]:
    """
    Fetches news articles from the Ben's Bites RSS feed.
    
    Args:
        max_retries: Maximum number of retry attempts on connection failure
        retry_delay: Delay in seconds between retry attempts
    
    Returns:
        List of news article dictionaries
    """
    # RSS feed URL
    rss_url = "https://rss.beehiiv.com/feeds/moS8GVKETl.xml"
    
    logger.info(f"Fetching news articles from RSS feed: {rss_url}")
    
    all_articles = []
    
    for attempt in range(max_retries):
        try:
            # Parse the RSS feed
            feed = feedparser.parse(rss_url)
            
            if feed.bozo:
                # This indicates there was an error parsing the feed
                logger.warning(f"Error parsing RSS feed: {feed.bozo_exception}")
                raise Exception(f"RSS feed parsing error: {feed.bozo_exception}")
                
            logger.info(f"Successfully parsed RSS feed, found {len(feed.entries)} entries")
            
            # Process each entry
            for entry in feed.entries:
                try:
                    article = {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "published_at": entry.get("published", ""),
                        "source": "bensbites.com",
                        "description": entry.get("description", ""),
                    }
                    all_articles.append(article)
                    logger.debug(f"Extracted article: {article['title']}")
                except Exception as e:
                    logger.error(f"Error processing RSS entry: {str(e)}")
                    continue
            
            # Successfully got articles, break out of retry loop
            break
            
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Error fetching data from RSS feed after {max_retries} attempts: {str(e)}")
                return []
    
    logger.info(f"Retrieved a total of {len(all_articles)} articles from RSS feed")
    return all_articles


def process_bensbites_articles(
    articles: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Process and transform Ben's Bites articles into a standardized format.

    Args:
        articles: List of raw article dictionaries from the Ben's Bites RSS feed

    Returns:
        List of processed article dictionaries
    """
    logger.info(f"Processing {len(articles)} Ben's Bites articles")
    processed_articles = []

    for article in articles:
        try:
            published_at = article.get("published_at", "")
            # Try to parse the date to a more standard format if needed
            try:
                if published_at:
                    # The date from the RSS feed is already in ISO 8601 format
                    # We'll keep it as is since it's a standard format
                    
                    # Optionally: Verify it's a valid date by parsing and reformatting
                    # This also standardizes different ISO 8601 variations
                    try:
                        # Try parsing as ISO 8601
                        dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                        published_at = dt.isoformat()
                    except ValueError:
                        # If that fails, try the RFC 822 format
                        dt = datetime.strptime(published_at, "%a, %d %b %Y %H:%M:%S %z")
                        published_at = dt.isoformat()
            except Exception as e:
                logger.warning(f"Could not parse date '{published_at}', using as is: {str(e)}")
            
            processed_article = {
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "source": article.get("source", "bensbites.com"),
                "published_at": published_at,
                "metadata": {
                    "api_source": "bensbites_rss",
                    "processed_at": datetime.now().isoformat(),
                    "description": article.get("description", ""),
                },
            }
            processed_articles.append(processed_article)
            logger.debug(f"Processed article: {processed_article['title']}")
        except Exception as e:
            logger.error(f"Error processing article: {str(e)}")
            continue

    logger.info(f"Successfully processed {len(processed_articles)} articles")
    return processed_articles


def main():
    """Main function to fetch and process Ben's Bites articles."""
    logger.info("Starting Ben's Bites ETL process")
    try:
        # Ensure output directory exists
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data/bensbites")
        ensure_directories(["data/bensbites"])

        # Get articles from the RSS feed
        articles = get_bensbites_data()

        if not articles:
            logger.warning("No articles retrieved, ETL process cannot continue")
            return

        # Process the articles
        processed_articles = process_bensbites_articles(articles)

        # Save to JSON file
        output_file = os.path.join(output_dir, "bensbites_news.json")
        with open(output_file, "w") as f:
            json.dump(processed_articles, f, indent=2)
        logger.debug(f"Saved JSON data to {output_file}")

        # Also save as CSV for easier viewing
        csv_file = os.path.join(output_dir, "bensbites_news.csv")
        import pandas as pd

        pd.DataFrame(processed_articles).to_csv(csv_file, index=False)
        logger.debug(f"Saved CSV data to {csv_file}")

        logger.info(
            f"Saved {len(processed_articles)} processed articles to {output_file} and {csv_file}"
        )

    except Exception as e:
        logger.error(f"Error in Ben's Bites ETL process: {str(e)}", exc_info=True)


if __name__ == "__main__":
    logger.info("Ben's Bites ETL script started")
    # Run the main function
    main()
    logger.info("Ben's Bites ETL script completed")