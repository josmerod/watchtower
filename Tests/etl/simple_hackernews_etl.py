#!/usr/bin/env python3
"""Simple HackerNews ETL test script."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import asyncio
    import json
    import time
    from datetime import datetime
    from typing import Dict, List, Any
    
    import aiohttp
    import feedparser
    
    from src.config.settings import get_settings
    from src.utils.logging import get_logger

    class SimpleHackerNewsETL:
        """Simple ETL for HackerNews RSS feed."""
        
        def __init__(self):
            self.settings = get_settings()
            self.logger = get_logger("simple_hn_etl")
            self.rss_url = "https://hnrss.org/frontpage"
            
        def extract(self) -> List[Dict[str, Any]]:
            """Extract data from HackerNews RSS feed."""
            self.logger.info(f"Extracting data from {self.rss_url}")
            
            feed = feedparser.parse(self.rss_url)
            
            if not feed.entries:
                raise Exception("No entries found in RSS feed")
            
            articles = []
            for entry in feed.entries[:10]:  # Limit to 10 for testing
                article = {
                    'title': entry.title,
                    'url': entry.link,
                    'published': entry.published,
                    'summary': getattr(entry, 'summary', ''),
                    'extracted_at': datetime.utcnow().isoformat()
                }
                articles.append(article)
            
            self.logger.info(f"Extracted {len(articles)} articles")
            return articles
        
        def transform(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """Transform the extracted articles."""
            self.logger.info("Transforming articles")
            
            transformed = []
            for article in articles:
                # Simple transformations
                transformed_article = {
                    'title': article['title'].strip(),
                    'url': article['url'],
                    'published_at': article['published'],
                    'summary': article['summary'][:200] + '...' if len(article['summary']) > 200 else article['summary'],
                    'source': 'hackernews',
                    'extracted_at': article['extracted_at']
                }
                transformed.append(transformed_article)
            
            self.logger.info(f"Transformed {len(transformed)} articles")
            return transformed
        
        def load(self, articles: List[Dict[str, Any]]) -> None:
            """Load articles to JSON file."""
            self.logger.info("Loading articles to file")
            
            # Ensure output directory exists
            output_dir = Path(self.settings.data_dir) / "simple_hackernews_etl" / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save as JSON
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_file = output_dir / f"hackernews_{timestamp}.json"
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Loaded {len(articles)} articles to {json_file}")
            print(f"Output saved to: {json_file}")
        
        def run(self) -> bool:
            """Run the ETL process."""
            start_time = time.time()
            
            try:
                print("Starting Simple HackerNews ETL...")
                
                # Extract
                articles = self.extract()
                print(f"Extracted: {len(articles)} articles")
                
                # Transform
                transformed = self.transform(articles)
                print(f"Transformed: {len(transformed)} articles")
                
                # Load
                self.load(transformed)
                print(f"Loaded: {len(transformed)} articles")
                
                duration = time.time() - start_time
                print(f"ETL completed in {duration:.2f} seconds")
                
                return True
                
            except Exception as e:
                self.logger.error(f"ETL failed: {e}")
                print(f"ETL failed: {e}")
                return False

    def main():
        """Main function."""
        etl = SimpleHackerNewsETL()
        success = etl.run()
        
        if success:
            print("Simple HackerNews ETL test PASSED")
        else:
            print("Simple HackerNews ETL test FAILED")
            sys.exit(1)

    if __name__ == "__main__":
        main()

except Exception as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 