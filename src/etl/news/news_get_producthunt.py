"""Product Hunt ETL Module

This module fetches and processes product launches using Playwright to bypass protections.

Usage:
    python src/etl/news/news_get_producthunt.py
"""

import csv
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, List, Dict, Optional

from playwright.sync_api import sync_playwright
from src.models.news import ProductHuntModel
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger("ProductHuntETL")

class ProductHuntScraper:
    def __init__(self):
        self.base_url = "https://www.producthunt.com"
        self.products = []
        self.seen_urls = set()

    def scrape(self, max_products: int = 50) -> List[Dict[str, Any]]:
        """Main scraping method."""
        logger.info("Starting Product Hunt scraper with Playwright...")
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                # 1. Scrape Homepage (Daily Launches)
                logger.info(f"Navigating to {self.base_url}")
                page.goto(self.base_url, timeout=60000, wait_until="domcontentloaded")
                time.sleep(5)  # Let dynamic content load
                
                # Scroll to load more
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 1000)")
                    time.sleep(2)

                logger.info("Extracting homepage products...")
                daily_products = self._extract_products_from_page(page, "featured")
                self._add_products(daily_products, max_products)

            except Exception as e:
                logger.error(f"Scraping session failed: {e}")
            finally:
                browser.close()

        logger.info(f"Total unique products scraped: {len(self.products)}")
        return self.products

    def _add_products(self, new_products: List[Dict[str, Any]], max_products: int):
        """Add new products to the list if not already seen."""
        for p in new_products:
            if len(self.products) >= max_products:
                return
            if p["url"] not in self.seen_urls:
                self.products.append(p)
                self.seen_urls.add(p["url"])

    def _extract_products_from_page(self, page, category: str) -> List[Dict[str, Any]]:
        """Extract product data from the current page using JS evaluation."""
        # We pass category as an argument to avoid f-string issues in JS
        return page.evaluate("""
            (category) => {
                const products = [];
                // Target links that look like products (NEW URL STRUCTURE)
                const links = Array.from(document.querySelectorAll('a[href^="/products/"]'));
                
                const seenLinks = new Set();
                
                // Track processed containers to avoid duplicates
                // Since we can't pass Sets back easily or compare complex objects in strict sets sometimes, 
                // we'll just be careful.
                const processedIndices = new Set();

                for (const link of links) {
                    const href = link.getAttribute('href');
                    if (seenLinks.has(href)) continue;
                    seenLinks.add(href);

                    if (href.includes('/comments') || href.includes('/reviews')) continue;

                    let container = link;
                    let bestContainer = null;
                    let curr = link;
                    
                    // Walk up to find the card container
                    for(let i=0; i<5; i++) {
                        if (!curr) break;
                        const hasVote = curr.querySelector('[class*="vote"]') || curr.querySelector('[class*="count"]');
                        const hasImg = curr.querySelector('img');
                        
                        // Heuristic: A container with an image and a vote button is likely the card
                        if (hasVote && hasImg) {
                             bestContainer = curr;
                             break;
                        }
                        curr = curr.parentElement;
                    }
                    
                    if (!bestContainer) bestContainer = link.parentElement.parentElement; 
                    
                    // Basic duplicate check by text content length or something simple
                    // (Skipping strict container dedup for now to avoid errors)

                    // Extract Data
                    const name = link.innerText.trim();
                    if (!name) continue;

                    // Tagline
                    let tagline = "";
                    const taglineEl = bestContainer.querySelector('[class*="tagline"]');
                    if (taglineEl) {
                        tagline = taglineEl.innerText;
                    } else {
                         const texts = bestContainer.innerText.split('\\n');
                         if (texts.length > 1 && texts[0].includes(name)) {
                             tagline = texts[1];
                         }
                    }

                    // Votes
                    let votes = 0;
                    const voteEl = bestContainer.querySelector('[class*="vote"], [class*="count"]');
                    if (voteEl) {
                         const vText = voteEl.innerText;
                         votes = parseInt(vText.replace(/\\D/g, '')) || 0;
                         // Sometimes the vote count is inside a button text like "Upvote 123"
                    } else {
                        // Look for any button with numbers
                        const buttons = bestContainer.querySelectorAll('button');
                        for (const btn of buttons) {
                            if (btn.innerText.match(/\\d+/)) {
                                votes = parseInt(btn.innerText.replace(/\\D/g, '')) || 0;
                                break; 
                            }
                        }
                    }

                    const img = bestContainer.querySelector('img');
                    const thumbnail = img ? img.src : "";

                    if (name.length > 1) {
                        products.push({
                            name: name,
                            tagline: tagline,
                            url: "https://www.producthunt.com" + href,
                            votes: votes,
                            comments: 0,
                            thumbnail: thumbnail,
                            category: category
                        });
                    }
                }
                return products;
            }
        """, category)

def process_data(raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process raw scraped data into final format."""
    processed = []
    current_time = datetime.now(timezone.utc).isoformat()
    
    for i, p in enumerate(raw_products):
        try:
            # Clean name
            name = p["name"]
            if name and name[0].isdigit() and ". " in name[:4]:
                 name = name.split(". ", 1)[1]

            processed.append({
                "id": f"ph_product_{i}",
                "name": name,
                "tagline": p["tagline"],
                "description": p["tagline"],
                "url": p["url"],
                "website": p["url"],
                "slug": p["url"].split("/products/")[-1] if "/products/" in p["url"] else "unknown",
                "votes_count": p["votes"],
                "comments_count": p["comments"],
                "reviews_count": 0,
                "reviews_rating": 0.0,
                "featured_at": current_time,
                "created_at": current_time,
                "updated_at": current_time,
                "thumbnail_url": p["thumbnail"],
                "gallery_images": [],
                "topics": [p["category"]],
                "makers": [],
                "hunters": [],
                "product_links": [{"type": "website", "url": p["url"]}],
                "category": p["category"],
                "mock_data": False,
                "fetched_at": current_time,
                "platform": "product_hunt",
                "days_since_launch": 0,
                "engagement_score": p["votes"],
                "launch_success_score": p["votes"],
                "potential_score": p["votes"] * 0.5,
                "freshness_factor": 1.0,
                "popularity_category": "viral" if p["votes"] > 1000 else "high" if p["votes"] > 500 else "medium",
                "launch_phase": "launch_day",
                "primary_category": p["category"],
                "innovation_level": "standard",
                "data_source": "product_hunt_scrape_playwright"
            })
        except Exception as e:
            logger.warning(f"Error processing item {i}: {e}")
            continue
            
    return processed

def main():
    try:
        scraper = ProductHuntScraper()
        raw_products = scraper.scrape(max_products=60)
        
        if not raw_products:
            logger.warning("No products scraped.")
            return

        processed_data = process_data(raw_products)
        
        # Save
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "product_hunt")
        ensure_directories([output_dir])
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        latest_json = os.path.join(output_dir, "product_hunt_latest.json")
        archive_json = os.path.join(output_dir, f"product_hunt_{timestamp}.json")
        
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
