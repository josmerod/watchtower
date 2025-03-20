import os
import json
import requests
import sys
import time
from datetime import datetime
from typing import Dict, List, Any
from bs4 import BeautifulSoup

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories, get_project_root

# Initialize logger for this module
logger = get_logger("FuturetoolsETL")


def get_futuretools_data(
    max_retries: int = 3, retry_delay: int = 5
) -> List[Dict[str, Any]]:
    """
    Fetches news articles from the futuretools web by scraping the HTML page.

    Args:
        max_retries: Maximum number of retry attempts on connection failure
        retry_delay: Delay in seconds between retry attempts

    Returns:
        List of news article dictionaries
    """
    # Webpage URL
    url = "https://futuretools.io/news"

    logger.info(f"Fetching news articles from {url}")

    for attempt in range(max_retries):
        try:
            # Send GET request to the webpage with increased timeout
            response = requests.get(url, timeout=30)
            response.raise_for_status()  # Raise exception for HTTP errors

            # Parse HTML content
            logger.debug("Parsing HTML content")
            soup = BeautifulSoup(response.content, "html.parser")

            # Find all news items
            news_items = soup.find_all(
                "div", role="listitem", class_="collection-item-6 w-dyn-item"
            )
            logger.debug(f"Found {len(news_items)} news items in the HTML")

            articles = []
            for item in news_items:
                try:
                    # Extract date
                    date_element = item.find("div", class_="text-block-30 blue-text-dm")
                    date = date_element.text.strip() if date_element else ""

                    # Extract link and title
                    link_element = item.find("a", class_="link-block-8 w-inline-block")
                    if link_element:
                        url = link_element.get("href", "")
                        title_element = link_element.find(
                            "div", class_="text-block-27 white-text-db-gc"
                        )
                        title = title_element.text.strip() if title_element else ""

                        article = {
                            "title": title,
                            "url": url,
                            "published_at": date,
                            "source": "futuretools.io",
                        }
                        articles.append(article)
                        logger.debug(f"Extracted article: {title}")
                except Exception as e:
                    logger.error(f"Error parsing news item: {str(e)}")
                    continue

            logger.info(f"Retrieved {len(articles)} articles from futuretools website")
            return articles

        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(
                    f"Error fetching data from futuretools website after {max_retries} attempts: {str(e)}"
                )
                return []


def process_futuretools_articles(
    articles: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Process and transform futuretools articles into a standardized format.

    Args:
        articles: List of raw article dictionaries from the futuretools website

    Returns:
        List of processed article dictionaries
    """
    logger.info(f"Processing {len(articles)} futuretools articles")
    processed_articles = []

    for article in articles:
        try:
            processed_article = {
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "source": article.get("source", "futuretools.io"),
                "published_at": article.get("published_at", ""),
                "metadata": {
                    "api_source": "futuretools_scraper",
                    "processed_at": datetime.now().isoformat(),
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
    """Main function to fetch and process futuretools articles."""
    logger.info("Starting futuretools ETL process")
    try:
        # Ensure output directory exists
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data/futuretools")
        ensure_directories(["data/futuretools"])

        # Get articles from the website
        articles = get_futuretools_data()

        if not articles:
            logger.warning("No articles retrieved, ETL process cannot continue")
            return

        # Process the articles
        processed_articles = process_futuretools_articles(articles)

        # Save to JSON file
        output_file = os.path.join(output_dir, "futuretoolsnews.json")
        with open(output_file, "w") as f:
            json.dump(processed_articles, f, indent=2)
        logger.debug(f"Saved JSON data to {output_file}")

        # Also save as CSV for easier viewing
        csv_file = os.path.join(output_dir, "futuretoolsnews.csv")
        import pandas as pd

        pd.DataFrame(processed_articles).to_csv(csv_file, index=False)
        logger.debug(f"Saved CSV data to {csv_file}")

        logger.info(
            f"Saved {len(processed_articles)} processed articles to {output_file} and {csv_file}"
        )

    except Exception as e:
        logger.error(f"Error in futuretools ETL process: {str(e)}", exc_info=True)


if __name__ == "__main__":
    logger.info("futuretools ETL script started")
    # Run the main function
    main()
    logger.info("futuretools ETL script completed") 