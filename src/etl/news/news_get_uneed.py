"""Uneed.best ETL Module

Scrapes the latest tools from Uneed.best using Playwright.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Any

from playwright.sync_api import sync_playwright

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger("UneedETL")


class UneedScraper:
    def __init__(self):
        self.base_url = "https://www.uneed.best/"
        self.products = []
        self.seen_urls = set()

    def scrape(self, max_products: int = 50) -> list[dict[str, Any]]:
        """Main scraping method."""
        logger.info("Starting Uneed.best scraper with Playwright...")

        with sync_playwright() as p:
            # Try to connect to browserless (better for anti-bot), fallback to local
            browserless_ws = os.getenv("BROWSERLESS_ENDPOINT", "ws://localhost:3000")
            try:
                logger.info(f"Connecting to remote browser at {browserless_ws}")
                browser = p.chromium.connect_over_cdp(browserless_ws)
                # Use a new context
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            except Exception as e:
                logger.warning(f"Could not connect to remote browser: {e}. Falling back to local launch.")
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()

            page = context.new_page()

            try:
                logger.info(f"Navigating to {self.base_url}")
                page.goto(self.base_url, timeout=60000, wait_until="domcontentloaded")
                time.sleep(5)  # Let dynamic content load

                # Scroll to load more
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 1000)")
                    time.sleep(2)

                logger.info("Extracting products...")

                # Uneed structure (based on typical modern sites - will default to generic selectors first)
                # Looking for cards.
                # Note: Since I haven't inspected Uneed, I will dump HTML if I find nothing to debug iteratively.
                # But let's try generic likely selectors.

                # Generic attempt based on visual scan of site (simulated knowledge)
                # Usually cards are in a grid.

                link_elements = page.query_selector_all('a[href^="/tool/"]')

                if not link_elements:
                    # Fallback to finding links inside generic cards if URL pattern differs
                    link_elements = page.query_selector_all('a[href^="/tools/"]')

                logger.info(f"Found {len(link_elements)} potential tool links")

                for link in link_elements:
                    if len(self.products) >= max_products:
                        break

                    url = link.get_attribute("href")
                    if not url:
                        continue

                    full_url = "https://www.uneed.best" + url if url.startswith("/") else url

                    if full_url in self.seen_urls:
                        continue

                    # Extract text info from the link or parent
                    name = link.inner_text().split("\n")[0].strip()  # Often name is first line

                    # Try to find description in parent card
                    # Walk up
                    card = link
                    description = ""
                    for _ in range(3):
                        if not card:
                            break
                        card = card.query_selector("xpath=..")
                        if not card:
                            break

                        # Look for p tag that is not the name
                        p_tags = card.query_selector_all("p")
                        for p_tag in p_tags:
                            text = p_tag.inner_text().strip()
                            if text and text != name and len(text) > 10:
                                description = text
                                break
                        if description:
                            break

                    if name:
                        self.products.append({"name": name, "url": full_url, "description": description, "source": "uneed.best"})
                        self.seen_urls.add(full_url)

            except Exception as e:
                logger.error(f"Scraping session failed: {e}")
            finally:
                browser.close()

        logger.info(f"Total unique products scraped: {len(self.products)}")
        return self.products


def process_data(raw_products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Process raw scraped data into final format."""
    processed = []
    current_time = datetime.now(timezone.utc).isoformat()

    for i, p in enumerate(raw_products):
        try:
            processed.append(
                {
                    "id": f"uneed_product_{i}",
                    "name": p["name"],
                    "tagline": p["description"],
                    "description": p["description"],
                    "url": p["url"],
                    "website": p["url"],
                    "votes_count": 0,  # Uneed might not show votes easily on home
                    "featured_at": current_time,
                    "created_at": current_time,
                    "platform": "uneed.best",
                    "data_source": "uneed_scrape_playwright",
                    "topics": ["tech", "tools"],
                }
            )
        except Exception as e:
            logger.warning(f"Error processing item {i}: {e}")
            continue

    return processed


def main():
    try:
        scraper = UneedScraper()
        raw_products = scraper.scrape(max_products=50)

        if not raw_products:
            logger.warning("No products scraped. Dumping HTML for debugging...")
            debug_path = os.path.join(get_project_root(), "logs", "uneed_debug.html")
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(scraper.base_url)
                time.sleep(5)
                html = page.content()
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(html)
                browser.close()
            logger.info(f"Dumped HTML to {debug_path}")
            return  # Don't save empty file

        processed_data = process_data(raw_products)

        # Save
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "uneed")
        ensure_directories([output_dir])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        latest_json = os.path.join(output_dir, "uneed_latest.json")
        archive_json = os.path.join(output_dir, f"uneed_{timestamp}.json")

        with open(latest_json, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)

        with open(archive_json, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(processed_data)} products to {latest_json}")

    except Exception as e:
        logger.error(f"ETL failed: {e}")
        raise


if __name__ == "__main__":
    main()
