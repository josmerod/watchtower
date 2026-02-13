import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Optional, Set
from pathlib import Path
import os
import json
from pathlib import Path

from playwright.async_api import async_playwright, Page

from src.etl.base import BaseETL
from src.models.opensource_model import OpenSourceProjectItem
from src.utils.logging import get_logger

class OpenSourceProjectsETL(BaseETL[dict, OpenSourceProjectItem]):
    def __init__(self):
        super().__init__(
            name="open_source_intelligence",
            description="ETL for opensourceprojects.dev",
            enable_enrichment=False  # Disabled for debugging pagination
        )
        self.base_url = "https://www.opensourceprojects.dev"
        self.existing_urls: Set[str] = set()
        self.MAX_PAGES = 50  # Safety limit for pagination
        
    def _load_existing_urls(self):
        """Load URLs from the latest output to detect duplicates during extraction."""
        latest_file = self.output_dir / "latest.json"
        if latest_file.exists():
            try:
                with open(latest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        if "url" in item:
                            self.existing_urls.add(item["url"])
                self.logger.info(f"Loaded {len(self.existing_urls)} existing URLs for duplicate detection.")
            except Exception as e:
                self.logger.warning(f"Failed to load existing data: {e}")

    async def _extract_async(self) -> List[dict]:
        self.logger.info("Starting async extraction with Playwright...")
        extracted_items = []
        
        # Load existing for incremental update
        self._load_existing_urls()
        
        async with async_playwright() as p:
            try:
                browserless_ws = os.getenv("BROWSERLESS_ENDPOINT")
                if browserless_ws:
                    self.logger.info(f"Connecting to remote browser at {browserless_ws}")
                    try:
                        browser = await p.chromium.connect_over_cdp(browserless_ws)
                    except Exception as e:
                        self.logger.warning(f"Could not connect to remote browser: {e}. Falling back to local launch.")
                        browser = await p.chromium.launch(headless=True)
                else:
                     self.logger.info("No remote browser configured. Launching local browser.")
                     browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                current_url = self.base_url
                page_num = 1
                stop_extraction = False
                
                last_page_hash = ""
                
                # Initial navigation
                self.logger.info(f"Navigating to {current_url}")
                await page.goto(current_url, timeout=60000)
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(5000) # Ensure hydration
                
                while not stop_extraction and page_num <= self.MAX_PAGES:
                    self.logger.info(f"Scraping page {page_num}/{self.MAX_PAGES}: {page.url}")
                    
                    # Get all project cards
                    cards = await page.query_selector_all("article.project-card")
                    if not cards:
                        self.logger.warning("No cards found on page.")
                        break
                        
                    self.logger.info(f"Found {len(cards)} cards on page {page_num}")
                    
                    items_on_page = 0
                    
                    for card in cards:
                        # Check if sponsored
                        classes = await card.get_attribute("class")
                        if classes and "sponsor-card" in classes:
                            continue
                            
                        # Extract data
                        title_el = await card.query_selector("h3.card-title")
                        title = await title_el.inner_text() if title_el else "Unknown Title"
                        
                        desc_el = await card.query_selector("p.card-excerpt")
                        description = await desc_el.inner_text() if desc_el else ""
                        # Clean description "By @..."
                        if "• " in description:
                            description = description.split("• ", 1)[1]
                            
                        link_el = await card.query_selector(".repo-info a.repo-link")
                        if link_el:
                            url = await link_el.get_attribute("href")
                        else:
                            # Try main card link if repo link not found
                            main_link = await card.query_selector("a.image-link-overlay")
                            url = await main_link.get_attribute("href") if main_link else ""
                            # If relative URL, make absolute (though repo link is usually absolute)
                            if url and url.startswith("/"):
                                url = self.base_url + url
                        
                        if not url:
                            continue
                            
                        # Duplicate check
                        if url in self.existing_urls:
                            self.logger.info(f"Found duplicate URL: {url}. Stopping extraction.")
                            stop_extraction = True
                            break

                            
                        # Tags
                        tags = []
                        tag_els = await card.query_selector_all(".project-tag span")
                        for tag_el in tag_els:
                            t = await tag_el.inner_text()
                            if t and t.upper() != "GITHUB":
                                tags.append(t)
                                
                        # Date
                        time_el = await card.query_selector("time.card-date")
                        date_str = await time_el.get_attribute("datetime") if time_el else None
                        
                        item = {
                            "title": title.strip(),
                            "description": description.strip(),
                            "url": url,
                            "tags": tags,
                            "published_at": date_str
                        }
                        extracted_items.append(item)
                        items_on_page += 1
                        
                    if stop_extraction:
                        break
                        
                    # Prepare for next page
                    # Prepare for next page (find 'Next' specifically among buttons)
                    # Scroll to bottom to ensure elements are rendered/visible
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)

                    next_btn = None
                    pagination_buttons = await page.query_selector_all("button.pagination-nav")
                    self.logger.info(f"Found {len(pagination_buttons)} pagination buttons.")
                    
                    for btn in pagination_buttons:
                        txt = await btn.text_content() # text_content includes hidden text
                        txt = txt.strip()
                        self.logger.info(f"Button text: '{txt}'")
                        
                        if "next" in txt.lower():
                            next_btn = btn
                            break
                    
                    if next_btn:
                        # Check if disabled
                        disabled = await next_btn.get_attribute("disabled")
                        if disabled is not None:
                            self.logger.info("Found 'Next' button but it is disabled. Stopping.")
                            break
                            
                        await next_btn.click()
                        page_num += 1
                        
                        # Wait for update
                        await page.wait_for_timeout(5000) # Generous wait
                        
                        if page_num > self.MAX_PAGES:
                            self.logger.info(f"Reached max pages ({self.MAX_PAGES}). Stopping.")
                            break
                            
                        # Check for stuck pagination (same content as previous)
                        # Use extracted_items[-1] which is the last item of the newly scraped page
                        if not extracted_items:
                             pass
                        else:
                            current_page_hash = extracted_items[-1]["title"]
                            if current_page_hash == last_page_hash:
                                self.logger.warning("Pagination detected same content as previous page. Stopping.")
                                break
                            last_page_hash = current_page_hash

                    else:
                        self.logger.info("No 'Next' button found on page. Stopping.")
                        break
                        
            except Exception as e:
                self.logger.error(f"Error during extraction loop: {e}")
            finally:
                if 'browser' in locals():
                    await browser.close()
                
        return extracted_items

    def extract(self) -> List[dict]:
        return asyncio.run(self._extract_async())

    def transform(self, data: List[dict]) -> List[OpenSourceProjectItem]:
        transformed = []
        for item in data:
            try:
                # Parse date if needed, Pydantic handles ISO strings well usually
                title = item.get("title", "")
                url = item.get("url", "")
                
                # Normalize published_at to naive UTC to match created_at (which is naive utcnow)
                pub_at = item.get("published_at")
                if isinstance(pub_at, str):
                    try:
                        # Handle basic ISO format with Z
                        if pub_at.endswith("Z"):
                            pub_at = pub_at[:-1]
                        # Remove specific offsets if present allowing Pydantic to parse as naive or strip it manually
                        # But simplest is to let Pydantic parse, but we are passing to init.
                        # If we pass a string with offset, Pydantic makes it aware.
                        # So we parse here.
                        dt = datetime.fromisoformat(pub_at.replace("Z", "+00:00") if "Z" in pub_at else pub_at)
                        pub_at = dt.replace(tzinfo=None)
                    except Exception:
                        pass # Let Pydantic handle or remain as string if valid
                
                project = OpenSourceProjectItem(
                    title=title,
                    description=item.get("description"),
                    url=url,
                    item_url=url, # Mapping for base compatibility if needed
                    tags=item.get("tags", []),
                    published_at=pub_at
                )
                transformed.append(project)
            except Exception as e:
                self.logger.warning(f"Error transforming item {item.get('title')}: {e}")
        return transformed

    def load(self, data: List[OpenSourceProjectItem]) -> None:
        if not data:
            self.logger.info("No new data to load.")
            return

        # Load existing current data (full dataset) to append/merge
        # We should merge with 'latest.json' to keep history since we successfully did incremental scraping
        
        final_data = []
        latest_file = self.output_dir / "latest.json"
        
        if latest_file.exists():
            try:
                with open(latest_file, "r", encoding="utf-8") as f:
                    old_data_json = json.load(f)
                    # Convert to models
                    for item in old_data_json:
                        final_data.append(OpenSourceProjectItem(**item))
            except Exception as e:
                self.logger.warning(f"Could not load existing latest.json for merging: {e}")

        # Prepend new data (newest first)
        final_data = data + final_data
        
        # Deduplicate by URL again to be safe (though extraction handled most)
        # Using a dictionary to filter duplicates by URL, keeping first (newest)
        unique_map = {}
        for item in final_data:
            if item.url not in unique_map:
                unique_map[item.url] = item
                
        final_list = list(unique_map.values())
        
        # Sort by timestamp/published_at desc
        final_list.sort(key=lambda x: x.published_at or x.created_at, reverse=True)

        # Save
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"opensource_projects_{timestamp}.json"
        
        json_data = [item.dict_without_none() for item in final_list]
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, default=str)
            
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, default=str)
            
        self.logger.info(f"Saved {len(final_list)} items to {output_file} and latest.json")

if __name__ == "__main__":
    etl = OpenSourceProjectsETL()
    etl.run()
