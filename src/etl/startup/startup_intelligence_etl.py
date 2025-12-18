"""Startup Intelligence ETL Module.

This module aggregates data from TechCrunch (via RSS) and Product Hunt (via Playwright scraping),
normalizes it into a specific startup model, and applies AI enrichment.
"""

import time
import feedparser
import re
from datetime import datetime, timezone
from typing import Any, List, Dict

from playwright.sync_api import sync_playwright

from src.etl.base import BaseETL
from src.models.startup import StartupNewsItem


class ProductHuntScraper:
    """Scraper logic for Product Hunt using Playwright."""

    def __init__(self, logger):
        self.base_url = "https://www.producthunt.com"
        self.products = []
        self.seen_urls = set()
        self.logger = logger

    def scrape(self, max_products: int = 50) -> List[Dict[str, Any]]:
        """Main scraping method."""
        self.logger.info("Starting Product Hunt scraper with Playwright...")
        
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
                self.logger.info(f"Navigating to {self.base_url}")
                page.goto(self.base_url, timeout=60000, wait_until="domcontentloaded")
                time.sleep(5)  # Let dynamic content load
                
                # Scroll to load more
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 1000)")
                    time.sleep(2)

                self.logger.info("Extracting homepage products...")
                daily_products = self._extract_products_from_page(page, "featured")
                self._add_products(daily_products, max_products)

            except Exception as e:
                self.logger.error(f"Scraping session failed: {e}")
            finally:
                browser.close()

        self.logger.info(f"Total unique products scraped: {len(self.products)}")
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
        return page.evaluate("""
            (category) => {
                const products = [];
                const links = Array.from(document.querySelectorAll('a[href^="/products/"]'));
                const seenLinks = new Set();

                for (const link of links) {
                    const href = link.getAttribute('href');
                    if (seenLinks.has(href)) continue;
                    seenLinks.add(href);

                    if (href.includes('/comments') || href.includes('/reviews')) continue;

                    let container = link;
                    let bestContainer = null;
                    let curr = link;
                    
                    for(let i=0; i<5; i++) {
                        if (!curr) break;
                        const hasVote = curr.querySelector('[class*="vote"]') || curr.querySelector('[class*="count"]');
                        const hasImg = curr.querySelector('img');
                        if (hasVote && hasImg) {
                             bestContainer = curr;
                             break;
                        }
                        curr = curr.parentElement;
                    }
                    if (!bestContainer) bestContainer = link.parentElement.parentElement; 

                    const name = link.innerText.trim();
                    if (!name) continue;

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

                    let votes = 0;
                    const voteEl = bestContainer.querySelector('[class*="vote"], [class*="count"]');
                    if (voteEl) {
                         const vText = voteEl.innerText;
                         votes = parseInt(vText.replace(/\\D/g, '')) || 0;
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


class StartupIntelligenceETL(BaseETL[Dict[str, Any], StartupNewsItem]):
    """ETL process for Startup Intelligence (TechCrunch + Product Hunt)."""

    TECHCRUNCH_FEEDS = {
        "techcrunch_main": "https://techcrunch.com/feed/",
        "techcrunch_startups": "https://techcrunch.com/category/startups/feed/",
    }

    def __init__(self):
        super().__init__(
            name="startup_intelligence",
            description="Aggregates startup news from TechCrunch and Product Hunt",
            enable_enrichment=True,  # AI Enrichment Enabled
            title_similarity_threshold=0.85
        )

    def extract(self) -> List[Dict[str, Any]]:
        """Extract data from TechCrunch and Product Hunt."""
        extracted_data = []

        # 1. Fetch TechCrunch RSS
        self.logger.info("Fetching TechCrunch feeds...")
        for source, url in self.TECHCRUNCH_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    entry['source_type'] = 'techcrunch'  # Mark source
                    extracted_data.append(entry)
            except Exception as e:
                self.logger.error(f"Failed to fetch {source}: {e}")

        # 2. Scrape Product Hunt
        self.logger.info("Scraping Product Hunt...")
        try:
            scraper = ProductHuntScraper(self.logger)
            ph_products = scraper.scrape(max_products=30)
            for p in ph_products:
                p['source_type'] = 'product_hunt' # Mark source
                extracted_data.append(p)
        except Exception as e:
            self.logger.error(f"Product Hunt scrape failed: {e}")

        return extracted_data

    def transform(self, data: List[Dict[str, Any]]) -> List[StartupNewsItem]:
        """Transform raw data into StartupNewsItem models."""
        transformed = []
        
        for item in data:
            try:
                source_type = item.get('source_type')
                
                if source_type == 'techcrunch':
                    news_item = self._transform_techcrunch(item)
                    if news_item:
                        transformed.append(news_item)
                
                elif source_type == 'product_hunt':
                    news_item = self._transform_producthunt(item)
                    if news_item:
                        transformed.append(news_item)
                        
            except Exception as e:
                self.logger.warning(f"Failed to transform item: {e}")
                self.metrics.warnings_count += 1
                
        return transformed

    def _transform_techcrunch(self, entry: Any) -> StartupNewsItem:
        """Transform TechCrunch RSS entry."""
        # Date parsing logic
        published = datetime.now(timezone.utc)
        if hasattr(entry, "published_parsed") and entry.published_parsed:
             published = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)

        # Content extraction
        summary = ""
        if hasattr(entry, "summary"):
            summary = self._clean_html(entry.summary)
        
        # Heuristics
        full_text = f"{entry.title} {summary}"
        funding = self._check_funding_mentions(full_text)
        companies = self._extract_company_mentions(full_text)
        
        return StartupNewsItem(
            title=entry.title,
            url=entry.link,
            source="techcrunch",
            summary=summary,
            published_at=published,
            author=entry.author if hasattr(entry, "author") else None,
            funding_mentioned=funding,
            company_mentioned=companies,
            tags=[t.term for t in entry.tags] if hasattr(entry, "tags") else []
        )

    def _transform_producthunt(self, p: Dict[str, Any]) -> StartupNewsItem:
        """Transform Product Hunt dict."""
        # Clean name logic
        name = p["name"]
        if name and name[0].isdigit() and ". " in name[:4]:
             name = name.split(". ", 1)[1]

        return StartupNewsItem(
            title=name,
            url=p["url"],
            source="product_hunt",
            summary=p.get("tagline", ""),
            tagline=p.get("tagline", ""),
            published_at=datetime.now(timezone.utc), # PH scrape is "now"
            votes=p.get("votes", 0),
            comments=p.get("comments", 0),
            thumbnail_url=p.get("thumbnail"),
            tags=[p.get("category")] if p.get("category") else []
        )

    def load(self, data: List[StartupNewsItem]) -> None:
        """Load data using default JSON saver."""
        # We can implement custom logic here if needed, but BaseETL doesn't implement load default for list[OutputType] unless we use SimpleETL. 
        # BaseETL is abstract. We MUST implement validation and saving.
        
        # Save enriched data
        output_file = self.output_dir / f"startup_intelligence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert to dicts
        data_dicts = [item.model_dump(mode='json') for item in data]
        
        import json
        output_file.write_text(json.dumps(data_dicts, indent=2, ensure_ascii=False), encoding="utf-8")
        
        # Save latest
        latest_file = self.output_dir / "startup_intelligence_latest.json"
        latest_file.write_text(json.dumps(data_dicts, indent=2, ensure_ascii=False), encoding="utf-8")
        
        self.logger.info(f"Saved {len(data)} items to {latest_file}")


    # Heuristic Helpers
    def _clean_html(self, text: str) -> str:
        return re.sub(r"<[^>]+>", "", text).strip()

    def _check_funding_mentions(self, text: str) -> bool:
        keywords = ["funding", "investment", "raised", "series a", "seed", "venture", "vc", "valuation"]
        return any(k in text.lower() for k in keywords)

    def _extract_company_mentions(self, text: str) -> List[str]:
        # simplified for this implementation
        tech_companies = ["OpenAI", "Anthropic", "Google", "Microsoft", "Amazon", "Meta", "Tesla", "Stripe"]
        return [c for c in tech_companies if c.lower() in text.lower()]

if __name__ == "__main__":
    etl = StartupIntelligenceETL()
    etl.run()
