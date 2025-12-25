"""Ben's Bites ETL Module

This module fetches and processes news articles from Ben's Bites using Playwright.
It follows the same output structure as other news ETL scripts in the project.

Usage:
    python src/etl/news/news_get_bensbites.py

Output:
    - JSON file: data/bensbites/bensbites_news.json
    - CSV file: data/bensbites/bensbites_news.csv
"""

import json
import os
import random
import time
from datetime import datetime, timedelta
from typing import Any

from playwright.sync_api import sync_playwright

# Add the project root to the path to ensure imports work correctly
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("BensBitesETL")


def get_bensbites_data(max_retries: int = 3, retry_delay: int = 5, max_pages: int = 4) -> list[dict[str, Any]]:
    """Fetches trending news articles from Ben's Bites website using Playwright.

    Args:
        max_retries: Maximum number of retry attempts on connection failure
        retry_delay: Delay in seconds between retry attempts
        max_pages: Maximum number of pages to fetch (default: 4)

    Returns:
        List of news article dictionaries
    """
    base_url = "https://news.bensbites.com/trending"
    logger.info(f"Fetching trending articles from: {base_url}")

    all_articles = []
    seen_urls = set()  # To prevent duplicate articles

    try:
        with sync_playwright() as p:
            # Launch browser with more browser-like settings
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                color_scheme="dark",
            )

            # Add common headers
            context.set_extra_http_headers(
                {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache",
                }
            )

            page = context.new_page()

            # Process each page
            for page_num in range(max_pages):
                # Add a variable delay between pages to appear more human-like
                if page_num > 0:
                    delay = 15  # Increasing delay for each subsequent page
                    logger.info(f"Waiting {delay} seconds before fetching page {page_num + 1}")
                    time.sleep(delay)

                current_url = f"{base_url}?page={page_num + 1}" if page_num > 0 else base_url
                logger.info(f"Processing page {page_num + 1}: {current_url}")

                # Navigate to the page and wait for content to load
                success = False
                for attempt in range(max_retries):
                    try:
                        # Clear cache and cookies between attempts
                        if attempt > 0:
                            context.clear_cookies()
                            time.sleep(retry_delay * (attempt + 1))  # Exponential backoff

                        # Navigate to the page and wait for content (relaxed condition)
                        try:
                            response = page.goto(current_url, wait_until="domcontentloaded", timeout=60000)
                        except Exception as nav_err:
                            logger.warning(f"Navigation timeout/error on page {page_num + 1}: {nav_err}")
                            if attempt < max_retries - 1:
                                continue
                            break

                        if not response.ok:
                            logger.warning(f"Page {page_num + 1} returned status {response.status}")
                            if attempt < max_retries - 1:
                                continue
                            break

                        # Simulate human-like scrolling
                        page.mouse.move(100, 100)
                        for _ in range(3):
                            page.mouse.wheel(0, 100)
                            time.sleep(0.5)

                        # Wait for the content to load
                        content = page.wait_for_selector(".grid.lg\\:grid-cols-12", state="visible", timeout=15000)

                        if content:
                            # Add a small random delay to simulate reading
                            time.sleep(1.5 + random.random())
                            success = True
                            break

                        logger.warning(f"Page {page_num + 1} content not found")

                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Failed to load page {page_num + 1}, attempt {attempt + 1}/{max_retries}: {e!s}")
                            time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                        else:
                            logger.error(f"Failed to load page {page_num + 1} after {max_retries} attempts")

                if not success:
                    logger.warning(f"Skipping page {page_num + 1} due to loading failures")
                    # If first page fails, abort entirely
                    if page_num == 0:
                        logger.error("First page failed to load, aborting")
                        break
                    continue

                # Extract articles
                articles = page.query_selector_all("div[wire\\:id] div[wire\\:id]")
                article_count = len(articles)
                logger.info(f"Found {article_count} potential articles on page {page_num + 1}")

                # If we find no articles, assume we've reached the end
                if article_count == 0:
                    logger.info("No articles found on page, assuming end of content")
                    break

                for article in articles:
                    try:
                        # Extract title and URL
                        title_element = article.query_selector("h3.text-primary.leading-5 a")
                        if not title_element:
                            continue

                        title = title_element.inner_text().strip()
                        url = title_element.get_attribute("href")

                        # Skip if we've already seen this URL
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)

                        # Extract source
                        source_element = article.query_selector("span.font-normal.text-secondary.text-xs.italic")
                        source = source_element.inner_text().strip() if source_element else "bensbites.com"

                        # Extract timestamp
                        time_element = article.query_selector("div.flex.space-x-1\\.5.text-xs.text-secondary span:nth-child(2)")
                        published_at = time_element.inner_text().strip() if time_element else ""

                        # Convert relative time to timestamp
                        current_time = datetime.now()
                        if "hours ago" in published_at:
                            hours = int(published_at.split()[0])
                            published_at = (current_time.replace(microsecond=0) - timedelta(hours=hours)).isoformat()
                        elif "minutes ago" in published_at:
                            minutes = int(published_at.split()[0])
                            published_at = (current_time.replace(microsecond=0) - timedelta(minutes=minutes)).isoformat()
                        else:
                            published_at = current_time.replace(microsecond=0).isoformat()

                        # Extract votes if available
                        votes_element = article.query_selector("div.flex svg + span.mx-1")
                        votes = votes_element.inner_text().strip() if votes_element else "0"

                        # Extract tags if available
                        tag_element = article.query_selector("a.text-gray-600.bg-gray-50")
                        tag = tag_element.inner_text().strip() if tag_element else ""

                        article_data = {
                            "title": title,
                            "url": (url if url.startswith("http") else f"https://news.bensbites.com{url}"),
                            "published_at": published_at,
                            "source": source,
                            "votes": votes,
                            "tag": tag,
                            "description": "",  # No description available in the list view
                            "page": page_num + 1,
                        }
                        all_articles.append(article_data)
                        logger.debug(f"Extracted article: {article_data['title']}")

                    except Exception as e:
                        logger.error(f"Error processing article: {e!s}")
                        continue

            # Clean up
            page.close()
            context.close()
            browser.close()

    except Exception as e:
        logger.error(f"Error during scraping: {e!s}")
        return []

    logger.info(f"Retrieved a total of {len(all_articles)} unique articles across {max_pages} pages")
    return all_articles


def process_bensbites_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Process and transform Ben's Bites articles into a standardized format.

    Args:
        articles: List of raw article dictionaries from Ben's Bites

    Returns:
        List of processed article dictionaries
    """
    logger.info(f"Processing {len(articles)} Ben's Bites articles")
    processed_articles = []

    for article in articles:
        try:
            processed_article = {
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "source": article.get("source", "bensbites.com"),
                "published_at": article.get("published_at", ""),
                "metadata": {
                    "api_source": "bensbites_playwright",
                    "processed_at": datetime.now().isoformat(),
                    "description": article.get("description", ""),
                    "votes": article.get("votes", "0"),
                    "tag": article.get("tag", ""),
                    "page": article.get("page", 1),
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
    """Main function to fetch and process Ben's Bites articles."""
    logger.info("Starting Ben's Bites ETL process")
    try:
        # Ensure output directory exists
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data/bensbites")
        ensure_directories(["data/bensbites"])

        # Get articles from the website
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

        logger.info(f"Saved {len(processed_articles)} processed articles to {output_file} and {csv_file}")

    except Exception as e:
        logger.error(f"Error in Ben's Bites ETL process: {e!s}", exc_info=True)


if __name__ == "__main__":
    logger.info("Ben's Bites ETL script started")
    main()
    logger.info("Ben's Bites ETL script completed")
