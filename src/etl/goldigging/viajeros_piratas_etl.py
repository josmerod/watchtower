"""
Viajeros Piratas Travel Deals Scraper ETL

This ETL scrapes travel deals from Viajeros Piratas website using Playwright.
It handles pagination and extracts deal information including price, destination, and type.
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from playwright.async_api import (
    Browser,
    Page,
    async_playwright,
)
from playwright.async_api import (
    TimeoutError as PlaywrightTimeoutError,
)

from src.etl.base import BaseETL
from src.models.ecommerce import TravelDeal, TravelDealRawData
from src.utils.logging import get_logger

logger = get_logger("ViajerosPrivatasETL")


class ViajerosPrivatasETL(BaseETL[TravelDealRawData, TravelDeal]):
    """
    ETL class for scraping travel deals from Viajeros Piratas using Playwright.
    """

    def __init__(self, max_pages: int = 10):
        """
        Initialize the Viajeros Piratas scraper.

        Args:
            max_pages: Maximum number of pages to scrape (default: 10)
        """
        super().__init__(
            name="viajeros_piratas",
            description="Scrapes travel deals from Viajeros Piratas website",
            enable_checkpointing=True,
            max_retries=3,
            retry_delay=5,
        )

        self.max_pages = max_pages
        self.base_url = "https://www.viajerospiratas.es/"

        # Browser settings
        self.browser_timeout = 60000  # 60 seconds
        self.page_timeout = 30000  # 30 seconds
        self.wait_timeout = 10000  # 10 seconds

        self.logger.info(
            f"Initialized Viajeros Piratas scraper for {self.max_pages} pages max"
        )

    def _build_url(self, page_num: int = 1) -> str:
        """Build the URL for a specific page."""
        if page_num == 1:
            return self.base_url
        return f"{self.base_url}?page={page_num}"

    async def _setup_browser(self) -> tuple[Browser, Page]:
        """Set up Playwright browser and page."""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=False,  # Visible browser for better compatibility
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
            ],
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="es-ES",
        )

        page = await context.new_page()
        page.set_default_timeout(self.page_timeout)

        return browser, page

    def _parse_relative_time(self, time_str: str) -> datetime:
        """Parse relative time strings like 'hace 21 horas' into datetime."""
        if not time_str:
            return datetime.utcnow()

        time_str = time_str.lower().strip()
        now = datetime.utcnow()

        # Handle specific patterns
        if "hace" in time_str:
            if "minuto" in time_str:
                minutes = re.search(r"(\d+)", time_str)
                if minutes:
                    from datetime import timedelta

                    return now - timedelta(minutes=int(minutes.group(1)))
            elif "hora" in time_str:
                hours = re.search(r"(\d+)", time_str)
                if hours:
                    from datetime import timedelta

                    return now - timedelta(hours=int(hours.group(1)))
            elif "día" in time_str:
                days = re.search(r"(\d+)", time_str)
                if days:
                    from datetime import timedelta

                    return now - timedelta(days=int(days.group(1)))

        # Handle absolute dates like "1/7/2025"
        date_match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", time_str)
        if date_match:
            day, month, year = date_match.groups()
            try:
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass

        return now

    def _extract_price(self, price_text: str) -> Dict[str, Any]:
        """Extract price information from text."""
        if not price_text:
            return {"raw_price": "", "amount": 0.0, "currency": "EUR"}

        # Extract price with regex
        price_match = re.search(r"(\d+)€", price_text)
        if price_match:
            amount = float(price_match.group(1))
            return {"raw_price": price_text, "amount": amount, "currency": "EUR"}

        return {"raw_price": price_text, "amount": 0.0, "currency": "EUR"}

    def _categorize_deal(self, title: str, description: str) -> str:
        """Categorize the deal based on title and description."""
        text = f"{title} {description}".lower()

        if any(word in text for word in ["hotel", "spa", "resort"]):
            return "hotel"
        elif any(word in text for word in ["vuelo", "vuelos", "flight"]):
            return "flight"
        elif any(
            word in text
            for word in ["vacaciones", "viaje", "escapada", "ruta", "tour", "circuito"]
        ):
            return "vacation"
        elif any(word in text for word in ["entrada", "parque", "attraction"]):
            return "attraction"
        else:
            return "other"

    async def _extract_deal_data(
        self, page: Page, page_num: int
    ) -> List[TravelDealRawData]:
        """Extract deal data from a page."""
        deals = []

        try:
            # Wait for the page to load
            await page.wait_for_load_state("networkidle", timeout=self.wait_timeout)

            # Save debug HTML for first page (moved before selector wait)
            if page_num == 1:
                try:
                    debug_content = await page.content()
                    debug_file = self.output_dir / "debug_viajeros_piratas.html"
                    with open(debug_file, "w", encoding="utf-8") as f:
                        f.write(debug_content)
                    self.logger.info(f"Saved debug HTML to {debug_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to save debug HTML: {e}")

            # Wait for deal elements to be present
            try:
                await page.wait_for_selector(
                    "article, .deal, .offer, .post", timeout=self.wait_timeout
                )
            except Exception as e:
                self.logger.warning(f"Timeout waiting for selectors: {e}")
                # Continue to try parsing anyway, as content might be there just not matching selectors exactly

            # Try multiple selectors to find deal elements
            deal_selectors = [
                "a[href*='/vacaciones/']",
                "a[href*='/hoteles/']",
                "a[href*='/vuelos/']",
                "a[href*='/cruceros/']",
                "a[href*='/viajes/']",
                "article",
                ".deal",
            ]

            deal_elements = []
            for selector in deal_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    # Filter out small elements or duplicates if needed
                    valid_elements = []
                    for el in elements:
                        # Ensure it's a deal card (has significant text)
                        text = await el.inner_text()
                        if len(text) > 20:
                            valid_elements.append(el)
                    
                    if valid_elements:
                        deal_elements = valid_elements
                        self.logger.info(
                            f"Found {len(valid_elements)} elements with selector: {selector}"
                        )
                        break

            if not deal_elements:
                self.logger.warning(f"No deal elements found on page {page_num}")
                return deals

            for idx, element in enumerate(deal_elements, 1):
                try:
                    # Extract deal data
                    deal_data = await self._extract_single_deal(element, page_num, idx)
                    if deal_data:
                        deals.append(deal_data)

                except Exception as e:
                    self.logger.warning(
                        f"Error extracting deal {idx} on page {page_num}: {e}"
                    )
                    continue

            self.logger.info(f"Extracted {len(deals)} deals from page {page_num}")

        except Exception as e:
            self.logger.error(f"Error extracting deals from page {page_num}: {e}")

        return deals

    async def _extract_single_deal(
        self, element, page_num: int, position: int
    ) -> Optional[TravelDealRawData]:
        """Extract data from a single deal element."""
        try:
            # Get all text content from the element
            text_content = await element.inner_text()

            if not text_content or len(text_content.strip()) < 20:
                return None

            # Extract title
            # Try to find the title element specifically
            title = ""
            
            # Strategy 1: Look for specific classes (if known/stable)
            # Strategy 2: Look for the largest text or specific structure
            
            # Try to find title by excluding price and time
            lines = text_content.split("\n")
            clean_lines = [l.strip() for l in lines if l.strip()]
            
            # Usually title is the first or second meaningful line
            # Skip "Vacaciones", "Hoteles" etc if they appear first
            categories = ["Vacaciones", "Hoteles", "Vuelos", "Cruceros", "Viajes"]
            
            for line in clean_lines:
                if line in categories:
                    continue
                if "Desde" in line or "€" in line:
                    continue
                if "hace" in line:
                    continue
                title = line
                break
            
            if not title and clean_lines:
                title = clean_lines[0]

            # Extract price information
            price_text = ""
            price_selectors = [".price", "[class*='price']", "[class*='cost']"]
            for selector in price_selectors:
                price_element = await element.query_selector(selector)
                if price_element:
                    price_text = (await price_element.inner_text()).strip()
                    break

            if not price_text:
                # Search for price patterns in text
                # Look for "Desde X€" or just "X€"
                price_match = re.search(r"(?:Desde\s+)?(\d+(?:[.,]\d+)?\s*€)", text_content, re.IGNORECASE)
                if price_match:
                    price_text = price_match.group(1)

            # Extract time information
            time_text = ""
            # Search for time patterns in text
            time_match = re.search(
                r"hace\s+\d+\s+\w+|\d{1,2}/\d{1,2}/\d{4}",
                text_content,
                re.IGNORECASE,
            )
            if time_match:
                time_text = time_match.group(0)

            # Extract link
            link = ""
            # If the element itself is an 'a' tag
            tag_name = await element.evaluate("el => el.tagName")
            if tag_name == "A":
                href = await element.get_attribute("href")
                if href:
                    link = urljoin(self.base_url, href)
            else:
                link_element = await element.query_selector("a")
                if link_element:
                    href = await link_element.get_attribute("href")
                    if href:
                        link = urljoin(self.base_url, href)

            # Generate unique ID
            deal_id = f"vp_{page_num}_{position}"

            # Store raw HTML for transformation
            raw_html = await element.inner_html()

            return TravelDealRawData(
                deal_id=deal_id,
                raw_content=raw_html,
                text_content=text_content,
                title=title,
                price_text=price_text,
                time_text=time_text,
                link=link,
                page_number=page_num,
                position=position,
                fetched_at=datetime.utcnow(),
            )

        except Exception as e:
            self.logger.warning(f"Error extracting single deal: {e}")
            return None

    async def _extract_async(self) -> List[TravelDealRawData]:
        """Async extraction method to handle Playwright operations."""
        all_deals = []

        async with async_playwright() as playwright:
            browser = None

            try:
                browser = await playwright.chromium.launch(
                    headless=False,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-web-security",
                    ],
                )

                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="es-ES",
                )

                page = await context.new_page()
                page.set_default_timeout(self.page_timeout)

                # Load checkpoint if available
                start_page = 1
                if self.current_checkpoint:
                    start_page = self.current_checkpoint.metadata.get("current_page", 1)
                    self.logger.info(f"Resuming from page {start_page}")

                for page_num in range(start_page, self.max_pages + 1):
                    self.logger.info(f"Scraping page {page_num}/{self.max_pages}")

                    url = self._build_url(page_num)
                    self.logger.info(f"Generated URL: {url}")

                    try:
                        # Navigate to page
                        await page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=self.browser_timeout,
                        )

                        # Wait for content to load
                        await page.wait_for_timeout(3000)

                        # Extract deals from this page
                        page_deals = await self._extract_deal_data(page, page_num)

                        if not page_deals:
                            self.logger.warning(f"No deals found on page {page_num}")
                            # Continue to next page instead of breaking
                            continue

                        all_deals.extend(page_deals)
                        self.logger.info(
                            f"Extracted {len(page_deals)} deals from page {page_num}"
                        )

                        # Update checkpoint
                        if self.enable_checkpointing:
                            if not self.current_checkpoint:
                                from src.etl.base import ETLCheckpoint

                                self.current_checkpoint = ETLCheckpoint(
                                    etl_name=self.name,
                                    checkpoint_id=f"{self.name}_{datetime.utcnow().isoformat()}",
                                    timestamp=datetime.utcnow(),
                                    metadata={},
                                )
                            self.current_checkpoint.metadata["current_page"] = page_num
                            self.current_checkpoint.processed_count = len(all_deals)
                            self._save_checkpoint(self.current_checkpoint)

                        # Brief pause between pages
                        await page.wait_for_timeout(2000)

                    except PlaywrightTimeoutError:
                        self.logger.error(f"Timeout on page {page_num}")
                        break
                    except Exception as e:
                        self.logger.error(f"Error on page {page_num}: {e}")
                        continue

            finally:
                if browser:
                    await browser.close()

        self.logger.info(
            f"Extracted {len(all_deals)} total deals from {self.max_pages} pages"
        )
        return all_deals

    def extract(self) -> List[TravelDealRawData]:
        """Extract raw deal data from Viajeros Piratas using Playwright."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self._extract_async())
                    finally:
                        new_loop.close()

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result()
            else:
                return loop.run_until_complete(self._extract_async())
        except RuntimeError:
            return asyncio.run(self._extract_async())

    def transform(self, data: List[TravelDealRawData]) -> List[TravelDeal]:
        """Transform raw deal data into structured TravelDeal objects."""
        transformed_deals = []

        for raw_deal in data:
            try:
                deal = self._parse_deal_data(raw_deal)
                if deal:
                    transformed_deals.append(deal)

            except Exception as e:
                self.logger.error(f"Error transforming deal {raw_deal.deal_id}: {e}")
                continue

        self.logger.info(f"Transformed {len(transformed_deals)} deals")
        return transformed_deals

    def _parse_deal_data(self, raw_deal: TravelDealRawData) -> Optional[TravelDeal]:
        """Parse raw deal data into structured format."""
        try:
            # Extract price information
            price_info = self._extract_price(raw_deal.price_text)

            # Parse time
            published_time = self._parse_relative_time(raw_deal.time_text)

            # Categorize deal
            category = self._categorize_deal(raw_deal.title, raw_deal.text_content)

            # Extract description (clean up text content)
            description = raw_deal.text_content.strip()
            lines = description.split("\n")
            # Remove empty lines and duplicate content
            clean_lines = [
                line.strip() for line in lines if line.strip() and len(line.strip()) > 3
            ]
            description = "\n".join(clean_lines[:5])  # Take first 5 meaningful lines

            return TravelDeal(
                deal_id=raw_deal.deal_id,
                title=raw_deal.title,
                description=description,
                price=price_info["amount"],
                currency=price_info["currency"],
                raw_price=price_info["raw_price"],
                category=category,
                url=raw_deal.link,
                published_at=published_time,
                fetched_at=raw_deal.fetched_at,
                parsed_at=datetime.utcnow(),
                page_number=raw_deal.page_number,
                position=raw_deal.position,
                source="viajeros_piratas",
            )

        except Exception as e:
            self.logger.error(f"Error parsing deal data for {raw_deal.deal_id}: {e}")
            return None

    def load(self, data: List[TravelDeal]) -> None:
        """Load the transformed deals into JSON and CSV files."""
        if not data:
            self.logger.warning("No deals to load")
            return

        # Prepare data for saving
        deals_data = []
        for deal in data:
            deals_data.append(deal.model_dump())

        # Save as JSON
        json_file = self.output_dir / "viajeros_piratas_deals.json"
        try:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(deals_data, f, indent=2, ensure_ascii=False, default=str)
            self.logger.info(f"Saved {len(deals_data)} deals to {json_file}")
        except Exception as e:
            self.logger.error(f"Error saving JSON file: {e}")

        # Save as CSV
        csv_file = self.output_dir / "viajeros_piratas_deals.csv"
        try:
            import pandas as pd

            df = pd.DataFrame(deals_data)
            df.to_csv(csv_file, index=False, encoding="utf-8")
            self.logger.info(f"Saved {len(deals_data)} deals to {csv_file}")
        except Exception as e:
            self.logger.error(f"Error saving CSV file: {e}")

        # Save in scavenging format for compatibility
        scavenging_data = []
        for deal in data:
            scavenging_data.append(
                {
                    "title": deal.title,
                    "link": str(deal.url),
                    "published": deal.published_at.isoformat(),
                    "summary": deal.description,
                    "category": "viajeros_piratas",
                    "source": "viajeros_piratas_etl",
                    "price": f"{deal.price}€" if deal.price > 0 else deal.raw_price,
                    "deal_type": deal.category,
                    "currency": deal.currency,
                }
            )

        # Save in scavenging format
        scavenging_file = Path(
            self.data_dir.parent.parent
            / "data"
            / "scavenging"
            / "viajeros_piratas_deals.json"
        )
        scavenging_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(scavenging_file, "w", encoding="utf-8") as f:
                json.dump(scavenging_data, f, indent=2, ensure_ascii=False, default=str)
            self.logger.info(
                f"Saved {len(scavenging_data)} deals in scavenging format to {scavenging_file}"
            )
        except Exception as e:
            self.logger.error(f"Error saving scavenging format file: {e}")


def main():
    """Main function to run the Viajeros Piratas scraper."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Viajeros Piratas Travel Deals Scraper"
    )
    parser.add_argument(
        "--max-pages", type=int, default=10, help="Maximum pages to scrape"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)

    scraper = ViajerosPrivatasETL(max_pages=args.max_pages)

    try:
        metrics = scraper.run()
        logger.info(f"Scraper completed successfully: {metrics}")
    except Exception as e:
        logger.error(f"Scraper failed: {e}")
        raise


if __name__ == "__main__":
    main()
