"""
Gumroad Free Products Scraper ETL

This ETL scrapes free products from Gumroad's discover page using Playwright.
It handles pagination using the 'from' parameter and supports both regular runs (500 items) and first run (10000 items).
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

from src.etl.base import BaseETL
from src.models.ecommerce import GumroadProduct, GumroadRawData
from src.utils.logging import get_logger

logger = get_logger("GumroadETL")


class GumroadScraperETL(BaseETL[GumroadRawData, GumroadProduct]):
    """
    ETL class for scraping free products from Gumroad using Playwright.
    Uses 'from' parameter for pagination instead of page numbers.
    """

    def __init__(self, first_run: bool = False, max_items: int = None):
        """
        Initialize the Gumroad scraper.
        
        Args:
            first_run: If True, scrapes up to 10000 items. If False, scrapes up to 500 items.
            max_items: Override the default item limit.
        """
        super().__init__(
            name="gumroad_scraper",
            description="Scrapes free products from Gumroad discover page",
            enable_checkpointing=True,
            max_retries=3,
            retry_delay=5,
        )
        
        self.first_run = first_run
        self.max_items = max_items or (10000 if first_run else 500)
        self.base_url = "https://gumroad.com/products/search"
        self.base_params = {
            "max_price": "1",
            "sort": "hot_and_new"
        }
        
        # Browser settings
        self.browser_timeout = 60000  # 60 seconds
        self.page_timeout = 30000     # 30 seconds
        self.wait_timeout = 10000     # 10 seconds
        
        # Pagination settings
        self.items_per_page = 48  # Typical items per page on Gumroad
        
        self.logger.info(f"Initialized Gumroad scraper for {'first run' if first_run else 'regular run'} "
                        f"with {self.max_items} items max")

    def _build_url(self, from_offset: int = 0) -> str:
        """Build the URL for a specific starting position."""
        params = self.base_params.copy()
        if from_offset > 0:
            params["from"] = str(from_offset)
        
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        # Match the exact format from Gumroad search results
        return f"{self.base_url}?&{param_str}"

    async def _setup_browser(self) -> tuple[Browser, Page]:
        """Set up Playwright browser and page."""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-images",  # Speed up loading
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        
        page = await context.new_page()
        page.set_default_timeout(self.page_timeout)
        
        return browser, page

    async def _extract_product_data(self, page: Page, from_offset: int) -> List[GumroadRawData]:
        """Extract product data from a JSON API response."""
        products = []
        
        try:
            # Wait for the page to load
            await page.wait_for_load_state("networkidle", timeout=self.wait_timeout)
            
            # Get the page content - it should be JSON
            content = await page.content()
            
            # Extract JSON from the HTML
            if '<pre>' in content:
                # Extract JSON from the <pre> tag
                json_start = content.find('<pre>') + 5
                json_end = content.find('</pre>')
                json_str = content[json_start:json_end]
            else:
                # Try to find JSON in the content
                json_str = content
            
            try:
                # Parse the JSON response
                data = json.loads(json_str)
                
                if 'products' in data and isinstance(data['products'], list):
                    products_list = data['products']
                    self.logger.info(f"Found {len(products_list)} products at offset {from_offset} from JSON response")
                    
                    for idx, product in enumerate(products_list, 1):
                        try:
                            # Extract product ID
                            product_id = product.get('permalink', f"unknown_{from_offset}_{idx}")
                            
                            # Store the raw JSON product data
                            raw_content = json.dumps(product, indent=2)
                            
                            products.append(GumroadRawData(
                                product_id=product_id,
                                raw_content=raw_content,
                                fetched_at=datetime.utcnow(),
                                page_number=from_offset // self.items_per_page + 1,
                                position=idx
                            ))
                            
                        except Exception as e:
                            self.logger.warning(f"Error extracting product {idx} at offset {from_offset}: {e}")
                            continue
                else:
                    self.logger.warning(f"No products found in JSON response at offset {from_offset}")
                    
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response at offset {from_offset}: {e}")
                return products
                    
        except Exception as e:
            self.logger.error(f"Error extracting products at offset {from_offset}: {e}")
        
        return products

    async def _has_more_results(self, page: Page, products_count: int, current_offset: int = 0) -> bool:
        """Check if there are more results available based on the JSON response."""
        try:
            # Get the page content and parse JSON
            content = await page.content()
            
            # Extract JSON from the HTML
            if '<pre>' in content:
                json_start = content.find('<pre>') + 5
                json_end = content.find('</pre>')
                json_str = content[json_start:json_end]
            else:
                json_str = content
            
            try:
                data = json.loads(json_str)
                
                # Check the total number of products available
                total_products = data.get('total', 0)
                
                # Calculate how many products we've processed so far
                processed_so_far = current_offset + products_count
                
                # If we've processed fewer products than the total available, there are more results
                if processed_so_far < total_products:
                    self.logger.info(f"More results available: {processed_so_far}/{total_products} processed")
                    return True
                
                # If we've processed all available products, no more results
                self.logger.info(f"All results processed: {processed_so_far}/{total_products}")
                return False
                
            except json.JSONDecodeError:
                # If we can't parse JSON, assume no more results
                return False
            
        except Exception as e:
            self.logger.warning(f"Error checking for more results: {e}")
            return False

    def _load_existing_data(self) -> List[GumroadProduct]:
        """Load existing data from JSON file if it exists."""
        json_file = self.output_dir / "gumroad_free_products.json"
        
        if not json_file.exists():
            return []
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert to GumroadProduct objects
            products = []
            for item in data:
                try:
                    # Handle datetime fields
                    if isinstance(item.get('fetched_at'), str):
                        item['fetched_at'] = datetime.fromisoformat(item['fetched_at'].replace('Z', '+00:00'))
                    if isinstance(item.get('parsed_at'), str):
                        item['parsed_at'] = datetime.fromisoformat(item['parsed_at'].replace('Z', '+00:00'))
                    
                    products.append(GumroadProduct(**item))
                except Exception as e:
                    self.logger.warning(f"Error parsing existing product: {e}")
                    continue
            
            self.logger.info(f"Loaded {len(products)} existing products from {json_file}")
            return products
            
        except Exception as e:
            self.logger.error(f"Error loading existing data: {e}")
            return []

    def _merge_with_existing(self, new_products: List[GumroadProduct], existing_products: List[GumroadProduct]) -> List[GumroadProduct]:
        """Merge new products with existing ones, avoiding duplicates."""
        if not existing_products:
            return new_products
        
        # Create a set of existing product IDs for fast lookup
        existing_ids = {product.product_id for product in existing_products}
        
        # Filter out duplicates from new products
        unique_new_products = []
        for product in new_products:
            if product.product_id not in existing_ids:
                unique_new_products.append(product)
        
        # Add new products at the beginning (most recent first)
        merged_products = unique_new_products + existing_products
        
        self.logger.info(f"Merged {len(unique_new_products)} new products with {len(existing_products)} existing products")
        return merged_products

    async def _extract_async(self) -> List[GumroadRawData]:
        """Async extraction method to handle Playwright operations."""
        all_products = []
        
        async with async_playwright() as playwright:
            browser = None
            
            try:
                browser = await playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-extensions",
                        "--disable-plugins",
                    ]
                )
                
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                )
                
                page = await context.new_page()
                page.set_default_timeout(self.page_timeout)
                
                # Load checkpoint if available
                from_offset = 0
                if self.current_checkpoint:
                    from_offset = self.current_checkpoint.metadata.get("from_offset", 0)
                    self.logger.info(f"Resuming from offset {from_offset}")
                
                items_loaded = 0
                
                while items_loaded < self.max_items:
                    current_offset = from_offset + items_loaded
                    self.logger.info(f"Scraping from offset {current_offset} (loaded {items_loaded}/{self.max_items})")
                    
                    url = self._build_url(current_offset)
                    self.logger.info(f"Generated URL: {url}")
                    
                    try:
                        # Navigate to page
                        await page.goto(url, wait_until="domcontentloaded", timeout=self.browser_timeout)
                        
                        # Wait a bit for dynamic content
                        await page.wait_for_timeout(2000)
                        
                        # Save debug HTML file for the first page
                        if current_offset == 0:
                            debug_content = await page.content()
                            debug_file = self.output_dir / "debug_page_content.html"
                            with open(debug_file, 'w', encoding='utf-8') as f:
                                f.write(debug_content)
                            self.logger.info(f"Saved debug HTML to {debug_file}")
                        
                        # Extract products from this page
                        page_products = await self._extract_product_data(page, current_offset)
                        
                        if not page_products:
                            self.logger.warning(f"No products found at offset {current_offset}")
                            # Check if we've reached the end
                            if not await self._has_more_results(page, 0, current_offset):
                                self.logger.info(f"No more results available at offset {current_offset}")
                                break
                            continue
                        
                        all_products.extend(page_products)
                        items_loaded += len(page_products)
                        self.logger.info(f"Extracted {len(page_products)} products from offset {current_offset}")
                        
                        # Update checkpoint
                        if self.enable_checkpointing:
                            if not self.current_checkpoint:
                                from src.etl.base import ETLCheckpoint
                                self.current_checkpoint = ETLCheckpoint(
                                    etl_name=self.name,
                                    checkpoint_id=f"{self.name}_{datetime.utcnow().isoformat()}",
                                    timestamp=datetime.utcnow(),
                                    metadata={}
                                )
                            self.current_checkpoint.metadata["from_offset"] = from_offset
                            self.current_checkpoint.metadata["items_loaded"] = items_loaded
                            self.current_checkpoint.processed_count = len(all_products)
                            self._save_checkpoint(self.current_checkpoint)
                        
                        # Check if we've reached the end naturally
                        if not await self._has_more_results(page, len(page_products), current_offset):
                            self.logger.info(f"Reached end of available results at offset {current_offset}")
                            break
                        
                        # Brief pause between pages
                        await page.wait_for_timeout(1000)
                        
                    except PlaywrightTimeoutError:
                        self.logger.error(f"Timeout at offset {current_offset}")
                        break
                    except Exception as e:
                        self.logger.error(f"Error at offset {current_offset}: {e}")
                        continue
                        
            finally:
                if browser:
                    await browser.close()
        
        self.logger.info(f"Extracted {len(all_products)} total products from {self.max_items} items max")
        return all_products

    def extract(self) -> List[GumroadRawData]:
        """Extract raw product data from Gumroad using Playwright."""
        # Run the async extraction in an event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an event loop, create a new thread
                import concurrent.futures
                import threading
                
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
            # No event loop running, create a new one
            return asyncio.run(self._extract_async())

    def transform(self, data: List[GumroadRawData]) -> List[GumroadProduct]:
        """Transform raw product data into structured GumroadProduct objects."""
        transformed_products = []
        
        for raw_product in data:
            try:
                product = self._parse_product_html(raw_product)
                if product:
                    transformed_products.append(product)
                    
            except Exception as e:
                self.logger.error(f"Error transforming product {raw_product.product_id}: {e}")
                continue
        
        self.logger.info(f"Transformed {len(transformed_products)} products")
        return transformed_products

    def _parse_product_html(self, raw_product: GumroadRawData) -> Optional[GumroadProduct]:
        """Parse JSON content to extract product details."""
        try:
            # Parse the JSON data
            product_data = json.loads(raw_product.raw_content)
            
            # Extract product name
            name = product_data.get('name')
            if not name:
                self.logger.warning(f"Could not extract name for product {raw_product.product_id}")
                return None
            
            # Extract price information
            price_cents = product_data.get('price_cents', 0)
            currency_code = product_data.get('currency_code', 'USD').upper()
            
            if price_cents == 0:
                price = "Free"
            else:
                price = f"${price_cents / 100:.2f} {currency_code}"
            
            # Extract seller information
            seller = None
            seller_data = product_data.get('seller', {})
            if seller_data:
                seller = seller_data.get('name')
            
            # Extract description
            description = product_data.get('description')
            
            # Extract thumbnail URL
            thumbnail_url = product_data.get('thumbnail_url')
            
            # Build product URL
            product_url = product_data.get('url', f"https://gumroad.com/l/{raw_product.product_id}")
            
            # Extract ratings
            ratings = product_data.get('ratings', {})
            rating = ratings.get('average')
            num_ratings = ratings.get('count')
            
            # Extract file type
            file_type = product_data.get('native_type')
            
            # Build additional info from the raw data
            additional_info = {
                "page_number": raw_product.page_number,
                "position": raw_product.position,
                "raw_json_length": len(raw_product.raw_content),
                "product_id_encoded": product_data.get('id'),
                "is_pay_what_you_want": product_data.get('is_pay_what_you_want', False),
                "quantity_remaining": product_data.get('quantity_remaining'),
                "is_sales_limited": product_data.get('is_sales_limited', False),
                "duration_in_months": product_data.get('duration_in_months'),
                "recurrence": product_data.get('recurrence')
            }
            
            return GumroadProduct(
                product_id=raw_product.product_id,
                name=name,
                price=price,
                seller=seller,
                description=description,
                url=product_url,
                fetched_at=raw_product.fetched_at,
                parsed_at=datetime.utcnow(),
                tags=None,  # Not available in JSON response
                thumbnail_url=thumbnail_url,
                rating=rating,
                num_ratings=num_ratings,
                file_type=file_type,
                additional_info=additional_info
            )
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON for product {raw_product.product_id}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error parsing product data for {raw_product.product_id}: {e}")
            return None

    def load(self, data: List[GumroadProduct]) -> None:
        """Load the transformed products into JSON and CSV files, merging with existing data."""
        if not data:
            self.logger.warning("No products to load")
            return
        
        # For incremental runs, merge with existing data
        if not self.first_run:
            existing_products = self._load_existing_data()
            data = self._merge_with_existing(data, existing_products)
        
        # Prepare data for saving
        products_data = []
        for product in data:
            products_data.append(product.model_dump())
        
        # Save as JSON
        json_file = self.output_dir / "gumroad_free_products.json"
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(products_data, f, indent=2, ensure_ascii=False, default=str)
            self.logger.info(f"Saved {len(products_data)} products to {json_file}")
        except Exception as e:
            self.logger.error(f"Error saving JSON file: {e}")
        
        # Save as CSV
        csv_file = self.output_dir / "gumroad_free_products.csv"
        try:
            import pandas as pd
            df = pd.DataFrame(products_data)
            df.to_csv(csv_file, index=False, encoding='utf-8')
            self.logger.info(f"Saved {len(products_data)} products to {csv_file}")
        except Exception as e:
            self.logger.error(f"Error saving CSV file: {e}")
        
        # Also save in the scavenging format for compatibility
        scavenging_data = []
        for product in data:
            scavenging_data.append({
                "title": product.name,
                "link": str(product.url),
                "published": product.fetched_at.isoformat(),
                "summary": product.description or "",
                "category": "gumroad_free",
                "source": "gumroad_scraper",
                "price": product.price,
                "seller": product.seller,
            })
        
        # Save in scavenging format
        scavenging_file = Path(self.data_dir.parent.parent / "data" / "scavenging" / "gumroad_free_products.json")
        scavenging_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(scavenging_file, 'w', encoding='utf-8') as f:
                json.dump(scavenging_data, f, indent=2, ensure_ascii=False, default=str)
            self.logger.info(f"Saved {len(scavenging_data)} products in scavenging format to {scavenging_file}")
        except Exception as e:
            self.logger.error(f"Error saving scavenging format file: {e}")


def main():
    """Main function to run the Gumroad scraper."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gumroad Free Products Scraper")
    parser.add_argument("--first-run", action="store_true", help="Run first-time scraping (10000 items)")
    parser.add_argument("--max-items", type=int, help="Override maximum items to scrape")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    scraper = GumroadScraperETL(
        first_run=args.first_run,
        max_items=args.max_items
    )
    
    try:
        metrics = scraper.run()
        logger.info(f"Scraper completed successfully: {metrics}")
    except Exception as e:
        logger.error(f"Scraper failed: {e}")
        raise


if __name__ == "__main__":
    main() 