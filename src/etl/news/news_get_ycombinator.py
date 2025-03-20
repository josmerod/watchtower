import os
import json
import requests
import sys
import time
from datetime import datetime
from typing import Dict, List, Any
from bs4 import BeautifulSoup
import feedparser
import re

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories

# Initialize logger for this module
logger = get_logger("YCombinatorETL")


def get_ycombinator_data(
    max_retries: int = 3, retry_delay: int = 5
) -> List[Dict[str, Any]]:
    """
    Fetches news articles from Hacker News by parsing RSS feeds from hnrss.org.

    Args:
        max_retries: Maximum number of retry attempts on connection failure
        retry_delay: Delay in seconds between retry attempts

    Returns:
        List of news article dictionaries
    """
    rss_urls = ["https://hnrss.org/frontpage", "https://hnrss.org/best"]
    articles = []
    
    for url in rss_urls:
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching RSS feed from {url}")
                feed = feedparser.parse(url)
                
                if not feed.entries:
                    logger.warning(f"No entries found in RSS feed from {url}")
                    break
                
                logger.debug(f"Found {len(feed.entries)} entries in RSS feed from {url}")
                
                for entry in feed.entries:
                    try:
                        # Extract story ID from the link or guid
                        story_id = ""
                        if hasattr(entry, 'id'):
                            id_match = re.search(r'item\?id=(\d+)', entry.id)
                            if id_match:
                                story_id = id_match.group(1)
                        
                        # Extract title
                        title = entry.title if hasattr(entry, 'title') else ""
                        
                        # Extract URL - the first link is usually the article URL
                        story_url = ""
                        if hasattr(entry, 'link'):
                            story_url = entry.link
                        
                        # Extract source domain
                        source = "news.ycombinator.com"
                        if hasattr(entry, 'link'):
                            # Try to extract domain from the URL
                            source_match = re.search(r'https?://([^/]+)', entry.link)
                            if source_match:
                                source = source_match.group(1)
                        
                        # Extract published date
                        published_at = ""
                        if hasattr(entry, 'published'):
                            published_at = entry.published
                        
                        # Create article object with the same structure as before
                        article = {
                            "title": title,
                            "url": story_url,
                            "published_at": published_at,
                            "source": source,
                            "hn_id": story_id
                        }
                        
                        # Extract comments URL and points if available
                        if hasattr(entry, 'summary'):
                            # Parse comments URL from summary
                            comments_match = re.search(r'Comments URL: &lt;(https://news.ycombinator.com/item\?id=\d+)&gt;', entry.summary)
                            if comments_match:
                                article["comments_url"] = comments_match.group(1)
                            
                            # Parse points from summary
                            points_match = re.search(r'Points: (\d+)', entry.summary)
                            if points_match:
                                article["points"] = int(points_match.group(1))
                        
                        articles.append(article)
                        logger.debug(f"Extracted article: {title}")
                    except Exception as e:
                        logger.error(f"Error parsing RSS entry: {str(e)}")
                        continue
                
                # Break out of retry loop if successful
                break
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(
                        f"Error fetching data from RSS feed after {max_retries} attempts: {str(e)}"
                    )
        
        # Add a small delay between RSS feed requests to be respectful to the server
        time.sleep(1)
    
    logger.info(f"Retrieved {len(articles)} articles from Hacker News RSS feeds")
    return articles


def process_ycombinator_articles(
    articles: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Process and transform HN articles into a standardized format.

    Args:
        articles: List of raw article dictionaries from Hacker News

    Returns:
        List of processed article dictionaries
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
                    "api_source": "hackernews_rss",
                    "processed_at": datetime.now().isoformat(),
                    "hn_id": article.get("hn_id", ""),
                    "points": article.get("points", 0),
                    "comments_url": article.get("comments_url", "")
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
    """Main function to fetch and process Hacker News articles."""
    logger.info("Starting Hacker News ETL process")
    try:
        # Ensure output directory exists
        output_dir = "data/hackernews"
        ensure_directories([output_dir])

        # Get articles from the RSS feeds
        articles = get_ycombinator_data()

        if not articles:
            logger.warning("No articles retrieved, ETL process cannot continue")
            return

        # Process the articles
        processed_articles = process_ycombinator_articles(articles)

        # Save to JSON file
        output_file = f"{output_dir}/hackernews.json"
        with open(output_file, "w") as f:
            json.dump(processed_articles, f, indent=2)
        logger.debug(f"Saved JSON data to {output_file}")

        # Also save as CSV for easier viewing
        csv_file = f"{output_dir}/hackernews.csv"
        import pandas as pd

        pd.DataFrame(processed_articles).to_csv(csv_file, index=False)
        logger.debug(f"Saved CSV data to {csv_file}")

        logger.info(
            f"Saved {len(processed_articles)} processed articles to {output_file} and {csv_file}"
        )

    except Exception as e:
        logger.error(f"Error in Hacker News ETL process: {str(e)}", exc_info=True)


if __name__ == "__main__":
    logger.info("Hacker News ETL script started")
    # Run the main function
    main()
    logger.info("Hacker News ETL script completed") 