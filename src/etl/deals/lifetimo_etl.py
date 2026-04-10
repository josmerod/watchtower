import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib

import requests
from bs4 import BeautifulSoup

from src.etl.base import BaseETL
from src.utils.file_system import ensure_directories
from src.utils.logging import get_logger
from src.models.ecommerce import LifetimeDeal

logger = get_logger("LifetimoETL")

class LifetimoETL(BaseETL[dict[str, Any], dict[str, Any]]):
    """ETL to scrape Lifetimo Deals and format them for the Deals tab."""

    def __init__(self):
        super().__init__(
            name="lifetimo_deals",
            description="Scrapes Lifetimo Lifetime Deals for productivity, AI, and automation",
            enable_checkpointing=True,
            max_retries=3,
            retry_delay=5
        )
        self.base_url = "https://lifetimo.com/dealbox/?_deal_categories=productivity%2Cai%2Cbundles%2Cself-hosted%2Cbackup%2Clearning%2Cautomation%2Cscheduling"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        }

    def extract(self) -> list[dict[str, Any]]:
        """Extract deals from the Lifetimo dealbox."""
        self.logger.info(f"Scraping Lifetimo deals from {self.base_url}")
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
        except Exception as e:
            self.logger.error(f"Failed to fetch Lifetimo page: {e}")
            return []

        articles = soup.find_all('article', class_='elementor-post')
        self.logger.info(f"Found {len(articles)} deal articles.")

        extracted_data = []
        for art in articles:
            try:
                title_tag = art.find('h3', class_='elementor-post__title')
                if not title_tag:
                    continue
                a_tag = title_tag.find('a')
                title = a_tag.text.strip() if a_tag else title_tag.text.strip()
                url = a_tag['href'] if a_tag and 'href' in a_tag.attrs else ""

                excerpt_tag = art.find('div', class_='elementor-post__excerpt')
                description = excerpt_tag.text.strip() if excerpt_tag else ""

                date_tag = art.find('span', class_='elementor-post-date')
                date_str = date_tag.text.strip() if date_tag else ""

                # Categories from classes (e.g. platform-ai, platform-productivity)
                classes = art.get('class', [])
                categories = [c.replace('platform-', '') for c in classes if c.startswith('platform-')]

                # Deduce deal_id from URL or Title
                deal_id = hashlib.md5(url.encode()).hexdigest() if url else hashlib.md5(title.encode()).hexdigest()

                extracted_data.append({
                    "deal_id": deal_id,
                    "title": title,
                    "url": url,
                    "description": description,
                    "date_str": date_str,
                    "categories": categories
                })
            except Exception as e:
                self.logger.warning(f"Error parsing deal article: {e}")

        return extracted_data

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform raw extracted data into LifetimeDeal format."""
        transformed = []
        for item in data:
            try:
                # Attempt to parse date (DD/MM/YYYY)
                published_at = None
                if item.get("date_str"):
                    try:
                        # Common format on Lifetimo seems to be DD/MM/YYYY
                        day, month, year = item["date_str"].split("/")
                        published_at = datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
                    except:
                        pass

                deal = LifetimeDeal(
                    deal_id=item["deal_id"],
                    title=item["title"],
                    url=item["url"],
                    description=item["description"],
                    categories=item["categories"],
                    published_at=published_at,
                    last_checked_at=datetime.now(timezone.utc),
                    source="lifetimo"
                )
                deal_dict = deal.model_dump()
                # Convert datetime to string for JSON serialization
                if deal_dict.get("published_at"):
                    deal_dict["published_at"] = deal_dict["published_at"].isoformat()
                if deal_dict.get("last_checked_at"):
                    deal_dict["last_checked_at"] = deal_dict["last_checked_at"].isoformat()
                
                transformed.append(deal_dict)
            except Exception as e:
                self.logger.warning(f"Transformation error for deal {item.get('title')}: {e}")

        return transformed

    def load(self, data: list[dict[str, Any]]) -> None:
        """Save results to data/deals/lifetimo_deals.json."""
        if not data:
            self.logger.warning("No data to load.")
            return

        output_path = Path(self.data_dir).parent.parent / "data" / "deals" / "lifetimo_deals.json"
        ensure_directories([str(output_path.parent)])

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Loaded {len(data)} deals to {output_path}")

if __name__ == "__main__":
    LifetimoETL().run()
