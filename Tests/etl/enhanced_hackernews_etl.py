#!/usr/bin/env python3

import re
from typing import Any

import feedparser
from pydantic import BaseModel, HttpUrl

from src.config.settings import get_settings
from src.etl.base import SimpleETL
from src.exceptions.etl import ExtractionError


class HackerNewsArticle(BaseModel):
    class Config:
        """Pydantic configuration."""

        json_encoders = {HttpUrl: lambda v: str(v)}


class HackerNewsETL(SimpleETL):
    def __init__(self):
        """Initialize the HackerNews ETL."""
        super().__init__(name="hackernews_etl")
        self.rss_urls = ["https://hnrss.org/best"]
        self.settings = get_settings()

    def extract(self) -> list[dict[str, Any]]:
        """Extract articles from Hacker News RSS feeds.

        Returns:
            List of raw article dictionaries.

        Raises:
            ExtractionError: If RSS feeds cannot be fetched.
        """
        self.logger.info("Extracting articles from Hacker News RSS feeds")
        articles = []

        for url in self.rss_urls:
            try:
                self.logger.debug(f"Fetching RSS feed from {url}")
                feed = feedparser.parse(url)

                if not feed.entries:
                    self.logger.warning(f"No entries found in RSS feed from {url}")
                    continue

                self.logger.debug(f"Found {len(feed.entries)} entries in RSS feed from {url}")

                for entry in feed.entries:
                    try:
                        article = self._parse_rss_entry(entry)
                        articles.append(article)
                    except Exception as e:
                        self.logger.error(f"Error parsing RSS entry: {e}")
                        continue

            except Exception as e:
                raise ExtractionError(message=f"Failed to fetch RSS feed: {url}", url=url, context={"error": str(e)}) from e

        if not articles:
            raise ExtractionError(message="No articles extracted from any RSS feeds", context={"rss_urls": self.rss_urls})

        return articles

    def _parse_rss_entry(self, entry) -> dict[str, Any]:
        """Parse RSS entry into article dictionary.

        Args:
            entry: RSS feed entry object.

        Returns:
            Article dictionary.
        """
        # Extract story ID from the link or guid
        story_id = ""
        if hasattr(entry, "id"):
            id_match = re.search(r"item\?id=(\d+)", entry.id)
            if id_match:
                story_id = id_match.group(1)

        # Extract title
        title = entry.title if hasattr(entry, "title") else ""

        # Extract URL
        story_url = entry.link if hasattr(entry, "link") else ""

        # Extract source domain
        source = "news.ycombinator.com"
        if hasattr(entry, "link"):
            source_match = re.search(r"https?://([^/]+)", entry.link)
            if source_match:
                source = source_match.group(1)

        # Extract published date
        published_at = entry.published if hasattr(entry, "published") else ""

        # Create article object
        article = {"comments_url": ""}

        # Extract comments URL and points if available
        if hasattr(entry, "summary"):
            # Parse comments URL from summary
            comments_match = re.search(entry.summary)
            if comments_match:
                article["comments_url"] = comments_match.group(1)

            # Parse points from summary
            return False


def main():
    """Main function to run the enhanced HackerNews ETL."""
    print("🚀 Starting Enhanced Hacker News ETL")

    # Initialize and run ETL
    etl = HackerNewsETL()

    try:
        # Run the complete ETL process
        success = etl.run()

        # Get metrics
        metrics = etl.get_metrics()

        # Display results
        print("\n📊 ETL Results:")
        print(f"✓ Success: {success}")
        print(f"✓ Duration: {metrics.duration_seconds:.2f} seconds")
        print(f"✓ Items extracted: {metrics.items_extracted}")
        print(f"✓ Items transformed: {metrics.items_transformed}")
        print(f"✓ Items loaded: {metrics.items_loaded}")
        print(f"✓ Success rate: {metrics.success_rate:.1f}%")

        if success:
            print("\n🎉 Enhanced HackerNews ETL completed successfully!")
            print("📁 Data saved to: data/hackernews/")
        else:
            print("\n❌ ETL process failed")
            return 1

    except Exception as e:
        print(f"\n❌ ETL process failed with error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
