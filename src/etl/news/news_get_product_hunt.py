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
            page.wait_for_timeout(3000)  # Wait for JS to load
            
            # Find products using the correct selector
            products = page.query_selector_all('[data-test*="post"]')[:20]
            
            for prod in products:
                try:
                    # Extract title using the correct selector
                    title_elem = prod.query_selector('[data-test*="name"]')
                    title = title_elem.inner_text().strip() if title_elem else None
                    
                    # Skip if no title found
                    if not title:
                        continue
                    
                    # Extract link
                    link_elem = prod.query_selector('a[href]')
                    href = link_elem.get_attribute('href') if link_elem else None
                    link = f'https://www.producthunt.com{href}' if href else ''
                    
                    # Extract description/tagline (usually the next text after title)
                    full_text = prod.inner_text()
                    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                    
                    # Find title line and get the next line as summary
                    summary = ''
                    title_clean = title.split('. ', 1)[-1] if '. ' in title else title
                    for i, line in enumerate(lines):
                        if title_clean in line and i + 1 < len(lines):
                            summary = lines[i + 1]
                            break
                    
                    # Extract vote count (look for numbers)
                    vote_text = full_text
                    votes = 0
                    import re
                    vote_matches = re.findall(r'\b(\d+)\b', vote_text)
                    if vote_matches:
                        # Usually the last number is votes
                        try:
                            votes = int(vote_matches[-1]) 
                        except:
                            votes = 0
                    
                    launches.append({
                        'title': title_clean,
                        'link': link,
                        'published': datetime.now().isoformat(),
                        'summary': summary,
                        'author': 'Product Hunt',
                        'votes': votes,
                        'source': 'Product Hunt'
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing product: {e}")
                    continue
                    
            browser.close()
        return launches

    def transform(self, data):
        return [ProductHuntModel(**entry) for entry in data]

    def load(self, data):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = self.output_dir / f'product_hunt_{timestamp}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump([m.model_dump() for m in data], f, indent=2)
        
        latest_json = self.output_dir / 'product_hunt_latest.json'
        # Use copy instead of symlink on Windows
        import shutil
        shutil.copy2(json_file, latest_json)
        
        # CSV (optional)
        import pandas as pd
        df = pd.DataFrame([m.model_dump() for m in data])
        csv_file = self.output_dir / f'product_hunt_{timestamp}.csv'
        df.to_csv(csv_file, index=False)

if __name__ == '__main__':
    etl = ProductHuntETL()
    etl.run() 