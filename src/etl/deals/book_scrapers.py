"""Book Scrapers Module

This module contains scrapers for fetching book deals from various external sources.
Currently supports:
- Humble Bundle Books
"""

import asyncio
import os
import sys
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from urllib.parse import urlparse

from src.utils.logging import get_logger
from src.utils.file_system import get_project_root

logger = get_logger("BookScrapers")


class HumbleBookScraper:
    """Scraper for Humble Bundle Books section."""

    def __init__(self):
        self.base_url = "https://www.humblebundle.com/books"

    async def _scrape_async(self) -> List[Dict[str, Any]]:
        """Asynchronously scrape book bundles."""
        from playwright.async_api import async_playwright
        import logging
        
        # Suppress noisy playwright logs
        logging.getLogger("asyncio").setLevel(logging.WARNING)

        bundles = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                # Create context with a realistic user agent
                context = await browser.new_context(
                     user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                     viewport={"width": 1920, "height": 1080}
                )
                
                # Add init script to hide webdriver property
                await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                page = await context.new_page()
                
                logger.info(f"Navigating to {self.base_url}...")
                await page.goto(self.base_url, timeout=60000, wait_until="domcontentloaded")
                
                # Wait for the tiles to load
                try:
                    await page.wait_for_selector(".mosaic-tile, .generated-tile, .bundle-tile", timeout=10000)
                except Exception:
                    logger.warning("Timeout waiting for bundle tiles, proceeding with whatever loaded")

                # Extract data using page evaluation to run in browser context
                # This is often more robust for React/dynamic apps than pure HTML parsing
                scraped_data = await page.evaluate("""() => {
                    const items = [];
                    // Try different selectors that Humble might use
                    // 'a.bundle' and '.full-tile-view' added based on visual inspection
                    const tiles = document.querySelectorAll('.mosaic-tile, .generated-tile, .bundle-tile, .entity-block-container, a.bundle, .full-tile-view');
                    
                    tiles.forEach(tile => {
                        try {
                            // Extract basic info
                            const titleElem = tile.querySelector('.name, .heading, h3, h2, .tile-title, .heading-medium');
                            let linkElem = tile.tagName === 'A' ? tile : tile.querySelector('a');
                            const timerElem = tile.querySelector('.timer, .countdown, .expiration-text');
                            
                            let title = titleElem ? titleElem.innerText.trim() : '';
                            let link = linkElem ? linkElem.getAttribute('href') : '';
                            
                            // Fallback: if no specific title element, try to find any text block that looks like a title
                            if (!title && tile.innerText) {
                                // Split by newlines and take the first non-empty line that isn't a timer or "Pay what you want"
                                const lines = tile.innerText.split('\\n');
                                for (const line of lines) {
                                    const trimmed = line.trim();
                                    if (trimmed && !trimmed.includes('Days Left') && !trimmed.includes('Pay what you want') && trimmed.length > 5) {
                                        title = trimmed;
                                        break;
                                    }
                                }
                            }

                            // If no title in text, try to get from URL
                            if (!title && link) {
                                const parts = link.split('/');
                                const slug = parts[parts.length - 1] || parts[parts.length - 2];
                                if (slug) {
                                    title = slug.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                                }
                            }

                            // Normalize link
                            if (link && link.startsWith('/')) {
                                link = 'https://www.humblebundle.com' + link;
                            }
                            
                            // Extract machine name / details if available in data attributes
                            const machineName = tile.getAttribute('data-machine-name');
                            
                            if (title && link) {
                                items.push({
                                    title: title,
                                    url: link,
                                    time_remaining: timerElem ? timerElem.innerText.trim() : null,
                                    machine_name: machineName
                                });
                            }
                        } catch (err) {
                            console.error('Error parsing tile', err);
                        }
                    });
                    return items;
                }""")
                
                # Post-process data
                for item in scraped_data:
                    # Filter out non-book bundles if any specifically slipped through (though we start at /books)
                    if "humblebundle.com" not in item["url"]:
                         continue
                    
                    title = item["title"]
                    # Fix generic titles from Humble
                    if not title or "PAY WHAT YOU WANT" in title.upper():
                        # Extract from URL
                        try:
                            path = urlparse(item["url"]).path
                            slug = path.strip("/").split("/")[-1]
                            # Clean up slug
                            title = slug.replace("-", " ").title()
                            # Basic cleanup
                            title = title.replace("Bookbundle", "").strip()
                        except Exception:
                            title = item["title"] or "Unknown Bundle"

                    bundles.append({
                        "title": title,
                        "description": f"Humble Book Bundle: {title}",
                        "url": item["url"],
                        "platform": "Humble Bundle",
                        "category": "ebook_bundles",
                        "deal_type": "book_bundles",
                        "original_price": 0, # Not easily available on list page
                        "current_price": 1, # Usually starts at $1
                        "savings": 0,
                        "discount_percentage": 0,
                        "book_type": "bundle",
                        "genre": "various",
                        "format": ["PDF", "EPUB", "MOBI"],
                        "drm_protected": False, # Humble is known for DRM-free
                        "language": "english",
                        "avg_rating": 4.5, # Placeholder for bundles
                        "page_count": 0,
                        "publisher_type": "various",
                        "tags": ["humble bundle", "books", "drm-free"],
                        "created_date": datetime.now(timezone.utc).isoformat(),
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "source": "HumbleBookScraper",
                        "time_remaining": item.get("time_remaining")
                    })

                await browser.close()
                
        except Exception as e:
            logger.error(f"Error scraping Humble Bundle Books: {e}")
            
        logger.info(f"Scraped {len(bundles)} book bundles from Humble Bundle")
        return bundles

    def scrape(self) -> List[Dict[str, Any]]:
        """Synchronous entry point for scraping."""
        try:
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            return asyncio.run(self._scrape_async())
        except Exception as e:
            logger.error(f"Failed to run async scrape: {e}")
            return []
