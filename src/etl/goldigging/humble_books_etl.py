import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel

from src.etl.base import BaseETL
from src.utils.logging import get_logger

logger = get_logger("HumbleBooksETL")

class HumbleBundleRaw(BaseModel):
    title: str
    url: str
    fetched_at: datetime
    
class HumbleBook(BaseModel):
    title: str
    bundle_name: str
    url: str
    fetched_at: datetime

class HumbleBooksETL(BaseETL[HumbleBundleRaw, HumbleBook]):
    """Scrapes humble.dadand.dev for active bundles and their contents."""

    def __init__(self):
        super().__init__(
            name="humble_books",
            description="Scrapes active Humble Book Bundles and their books",
            enable_checkpointing=False,
            max_retries=3,
        )

    def extract(self) -> list[HumbleBundleRaw]:
        self.logger.info("Fetching main page of humble.dadand.dev")
        url = "https://humble.dadand.dev/"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        active_section = soup.find(lambda tag: tag.name == "h2" and "Active Bundles" in tag.text)
        if not active_section:
            self.logger.error("Could not find Active Bundles section.")
            return []

        bundles = []
        for sibling in active_section.find_next_siblings():
            if sibling.name == "h2" and "Past Bundles" in sibling.text:
                break
            for link in sibling.find_all("a"):
                href = link.get("href")
                if href and "/bundles/" in href:
                    title = link.text.strip()
                    if href.startswith("/"):
                        href = "https://humble.dadand.dev" + href
                    bundles.append(HumbleBundleRaw(title=title, url=href, fetched_at=datetime.utcnow()))
                    
        # Remove duplicates based on URL
        unique_bundles = {b.url: b for b in bundles}.values()
        self.logger.info(f"Extracted {len(unique_bundles)} unique active bundles.")
        return list(unique_bundles)

    def transform(self, raw_data: list[HumbleBundleRaw]) -> list[HumbleBook]:
        books = []
        for bundle in raw_data:
            self.logger.info(f"Extracting books from bundle: {bundle.title}")
            try:
                b_resp = requests.get(bundle.url, timeout=30)
                b_resp.raise_for_status()
                b_soup = BeautifulSoup(b_resp.text, "html.parser")
                
                # The books are nested in <h4> tags inside the bundle pages
                for h4 in b_soup.find_all("h4"):
                    title = h4.text.strip()
                    if title:
                        books.append(
                            HumbleBook(
                                title=title,
                                bundle_name=bundle.title,
                                url=bundle.url,
                                fetched_at=datetime.utcnow(),
                            )
                        )
            except Exception as e:
                self.logger.error(f"Failed to fetch bundle {bundle.url}: {e}")
                
        self.logger.info(f"Transformed to {len(books)} books across all bundles.")
        return books

    def load(self, structured_data: list[HumbleBook]) -> None:
        """Saves data into the scavenging format automatically picked up by the dashboard."""
        if not structured_data:
            self.logger.warning("No hooks found to load. Returning early.")
            return
            
        output_dir = Path("data/scavenging")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save in the native format expected by the DB/Dashboard
        scavenging_data = []
        for book in structured_data:
            scavenging_data.append({
                "title": book.title,
                "link": book.url,
                "published": book.fetched_at.isoformat(),
                "summary": f"Included in bundle: {book.bundle_name}",
                "category": "humble_books",
                "source": "humble_scraper",
                "price": "Bundle Pricing",
            })
            
        output_file = output_dir / "humble_books.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(scavenging_data, f, indent=2, ensure_ascii=False, default=str)
            
        self.logger.info(f"Saved {len(scavenging_data)} books to {output_file}")


if __name__ == "__main__":
    import argparse
    import logging
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
    etl = HumbleBooksETL()
    etl.run()
