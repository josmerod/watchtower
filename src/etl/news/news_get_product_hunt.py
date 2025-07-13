"""Product Hunt ETL Module.

Fetches latest launches from Product Hunt RSS feed.

Saves to JSON and CSV in data/product_hunt/.
"""

import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

import feedparser

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.etl.base import BaseETL
from src.models.news import ProductHuntModel  # Assume this exists

from playwright.sync_api import sync_playwright

logger = get_logger("ProductHuntETL")

RSS_URL = "https://www.producthunt.com/feed.atom"

class ProductHuntETL(BaseETL):
    URL = 'https://www.producthunt.com/'

    def __init__(self):
        super().__init__(name='product_hunt')

    def extract(self):
        launches = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.URL)
            products = page.query_selector_all('li[data-test="post-item"]')[:20]
            if not products:
                products = page.query_selector_all('div[class*="post"]')[:20]
            for prod in products:
                title_elem = prod.query_selector('h3')
                title = title_elem.inner_text().strip() if title_elem else 'No title'
                link_elem = prod.query_selector('a')
                href = link_elem.get_attribute('href') if link_elem else None
                link = f'https://www.producthunt.com{href}' if href else ''
                published = datetime.now().isoformat()  # Placeholder
                summary_elem = prod.query_selector('p')
                summary = summary_elem.inner_text().strip() if summary_elem else ''
                author_elem = prod.query_selector('div[class*="user"] span')
                author = author_elem.inner_text().strip() if author_elem else 'Anonymous'
                launches.append({
                    'title': title,
                    'link': link,
                    'published': published,
                    'summary': summary,
                    'author': author
                })
            browser.close()
        return launches

    def transform(self, data):
        return [ProductHuntModel(**entry) for entry in data]

    def load(self, data):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = self.output_dir / f'product_hunt_{timestamp}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump([m.dict() for m in data], f, indent=2)
        
        latest_json = self.output_dir / 'product_hunt_latest.json'
        if os.path.exists(latest_json):
            os.remove(latest_json)
        os.symlink(json_file, latest_json)
        
        # CSV (optional)
        import pandas as pd
        df = pd.DataFrame([m.dict() for m in data])
        csv_file = self.output_dir / f'product_hunt_{timestamp}.csv'
        df.to_csv(csv_file, index=False)

if __name__ == '__main__':
    etl = ProductHuntETL()
    etl.run() 