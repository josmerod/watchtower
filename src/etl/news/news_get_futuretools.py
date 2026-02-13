"""ETL module for scraping news articles from FutureTools.io using Playwright.

This module fetches news articles related to AI tools and technologies
by scraping the FutureTools.io news page. It uses Playwright to handle
dynamic content rendering.
"""

import json
import os
import time
from datetime import datetime
from typing import Any

from playwright.sync_api import sync_playwright

# Import from the installed package
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("FuturetoolsETL")


def get_futuretools_data(max_retries: int = 3, retry_delay: int = 5) -> list[dict[str, Any]]:
    """Fetches news articles from the futuretools web by scraping the page with Playwright.

    Args:
        max_retries: Maximum number of retry attempts on connection failure
        retry_delay: Delay in seconds between retry attempts

    Returns:
        List of news article dictionaries
    """
    # Webpage URL
    url = "https://futuretools.io/news"

    logger.info(f"Fetching news articles from {url} using Playwright")

    for attempt in range(max_retries):
        try:
            with sync_playwright() as p:
                browserless_ws = os.getenv("BROWSERLESS_ENDPOINT", "ws://localhost:3000")
                
                try:
                    logger.info(f"Connecting to remote browser at {browserless_ws}")
                    browser = p.chromium.connect_over_cdp(browserless_ws)
                except Exception as e:
                    logger.warning(f"Could not connect to remote browser: {e}. Falling back to local launch.")
                    browser = p.chromium.launch(headless=True)

                context = browser.new_context()
                page = context.new_page()
                
                # Navigate to page
                page.goto(url, wait_until="networkidle", timeout=60000)
                
                # Wait for the list items to appear
                try:
                    page.wait_for_selector('div[role="listitem"]', timeout=30000)
                except Exception:
                    logger.warning("Timeout waiting for listitem selector. Continuing, maybe empty or slow load.")

                # Extract news items
                # The original soup selector was: div[role="listitem"][class*="collection-item-6"]
                # We'll use a CSS selector that matches that structure
                list_items = page.query_selector_all('div[role="listitem"]')
                logger.debug(f"Found {len(list_items)} potential news items via Playwright")
                
                articles = []
                for item in list_items:
                    try:
                        # Extract date
                        date_elem = item.query_selector('.text-block-30.blue-text-dm')
                        if not date_elem:
                            # Try alternative selector if structure changed
                            date_elem = item.query_selector('div[class*="text-block-30"]')
                            
                        date = date_elem.inner_text().strip() if date_elem else ""

                        # Extract link and title
                        link_elem = item.query_selector('a.link-block-8.w-inline-block')
                        if not link_elem:
                            link_elem = item.query_selector('a[href^="http"]') # Fallback

                        if link_elem:
                            article_url = link_elem.get_attribute("href") or ""
                            
                            title_elem = link_elem.query_selector('.text-block-27.white-text-db-gc')
                            if not title_elem:
                                # Try to get text from the link itself or generic div inside
                                title = link_elem.inner_text().strip()
                            else:
                                title = title_elem.inner_text().strip()

                            if title and article_url:
                                article = {
                                    "title": title,
                                    "url": article_url,
                                    "published_at": date,
                                    "source": "futuretools.io",
                                }
                                articles.append(article)
                                logger.debug(f"Extracted article: {title}")
                    except Exception as e:
                        logger.error(f"Error parsing news item: {e}")
                        continue
                
                logger.info(f"Retrieved {len(articles)} articles from futuretools website")
                
                browser.close()
                return articles

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e!s}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Error fetching data from futuretools website after {max_retries} attempts: {e!s}")
                return []
    return []


def process_futuretools_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Process and transform futuretools articles into a standardized format.

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
            logger.error(f"Error processing article: {e!s}")
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
        with open(output_file, "w", encoding='utf-8') as f:
            json.dump(processed_articles, f, indent=2, ensure_ascii=False)
        logger.debug(f"Saved JSON data to {output_file}")

        # Also save as CSV for easier viewing
        csv_file = os.path.join(output_dir, "futuretoolsnews.csv")
        import pandas as pd

        pd.DataFrame(processed_articles).to_csv(csv_file, index=False)
        logger.debug(f"Saved CSV data to {csv_file}")

        logger.info(f"Saved {len(processed_articles)} processed articles to {output_file} and {csv_file}")

    except Exception as e:
        logger.error(f"Error in futuretools ETL process: {e!s}", exc_info=True)


if __name__ == "__main__":
    logger.info("futuretools ETL script started")
    # Run the main function
    main()
    logger.info("futuretools ETL script completed")
