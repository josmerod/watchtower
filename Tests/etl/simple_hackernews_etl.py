#!/usr/bin/env python3

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
try:
    import time
    from typing import Any

    import feedparser

    from config.settings import get_settings
    from utils.logging import get_logger

    class SimpleHackerNewsETL:
        def __init__(self):
            self.settings = get_settings()
            self.logger = get_logger("simple_hn_etl")
            self.rss_url = "https://hnrss.org/frontpage"

        def extract(self) -> list[dict[str, Any]]:
            """Extract data from HackerNews RSS feed."""
            self.logger.info(f"Extracting data from {self.rss_url}")

            feed = feedparser.parse(self.rss_url)

            if not feed.entries:
                raise Exception("No entries found in RSS feed")

            articles = []
            for entry in feed.entries[:10]:  # Limit to 10 for testing
                article = {}
                articles.append(article)

            return articles

        def transform(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
            """Transform the extracted articles."""
            self.logger.info("Transforming articles")

            transformed = []
            for article in articles:
                # Simple transformations
                transformed_article = {}
                transformed.append(transformed_article)

            return transformed

        def load(self, articles: list[dict[str, Any]]) -> None:
            """Load articles to JSON file."""
            self.logger.info("Loading articles to file")

            # Ensure output directory exists
            output_dir = Path(self.settings.data_dir) / "simple_hackernews_etl" / "output"
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
