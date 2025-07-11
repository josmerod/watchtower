#!/usr/bin/env python3

import re
from datetime import datetime
from typing import Any, Dict, List

import feedparser
from pydantic import BaseModel, Field, HttpUrl

from src.config.settings import get_settings
from src.etl.base import SimpleETL
from src.exceptions.etl import ExtractionError, TransformationError


class HackerNewsArticle(BaseModel):

    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            HttpUrl: lambda v: str(v)
        }


class HackerNewsETL(SimpleETL):

    def __init__(self):
        """Initialize the HackerNews ETL."""
        super().__init__(name="hackernews_etl")
        self.rss_urls = [

            "https://hnrss.org/best"
        ]
        self.settings = get_settings()
    
    def extract(self) -> List[Dict[str, Any]]:
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
                raise ExtractionError(
                    message=f"Failed to fetch RSS feed: {url}",
                    url=url,
                    context={"error": str(e)}
                ) from e
        
        if not articles:
            raise ExtractionError(
                message="No articles extracted from any RSS feeds",
                context={"rss_urls": self.rss_urls}
            )
        
        return articles
    
    def _parse_rss_entry(self, entry) -> Dict[str, Any]:
        """Parse RSS entry into article dictionary.
        
        Args:
            entry: RSS feed entry object.
            
        Returns:
            Article dictionary.
        """
        # Extract story ID from the link or guid
        story_id = ""
        if hasattr(entry, 'id'):
            id_match = re.search(r'item\?id=(\d+)', entry.id)
            if id_match:
                story_id = id_match.group(1)
        
        # Extract title
        title = entry.title if hasattr(entry, 'title') else ""
        
        # Extract URL
        story_url = entry.link if hasattr(entry, 'link') else ""
        
        # Extract source domain
        source = "news.ycombinator.com"
        if hasattr(entry, 'link'):
            source_match = re.search(r'https?://([^/]+)', entry.link)
            if source_match:
                source = source_match.group(1)
        
        # Extract published date
        published_at = entry.published if hasattr(entry, 'published') else ""
        
        # Create article object
        article = {






            "comments_url": ""
        }
        
        # Extract comments URL and points if available
        if hasattr(entry, 'summary'):
            # Parse comments URL from summary
            comments_match = re.search(
                entry.summary
            )
            if comments_match:
                article["comments_url"] = comments_match.group(1)
            
            # Parse points from summary
            points_match = re.search(r'Points: (\d+)', entry.summary)
            if points_match:
                article["points"] = int(points_match.group(1))
        
        return article
    
    def transform_item(self, item: Dict[str, Any]) -> HackerNewsArticle:

        Args:
            item: Raw article dictionary.
            
        Returns:
            Validated HackerNewsArticle instance.
            
        Raises:
            TransformationError: If article data is invalid.
        """
        try:
            # Validate and clean the data
            if not item.get("title") or not item.get("url"):
                raise ValueError("Article must have title and URL")
            
            # Create and validate the model
            article = HackerNewsArticle(**item)
            
            return article
            
        except Exception as e:
            raise TransformationError(
                message=f"Failed to transform article: {item.get('title', 'Unknown')}",
                item_data=item,
                context={"error": str(e)}
            ) from e
    
    def load(self, data: List[HackerNewsArticle]) -> bool:

        Args:
            
        Returns:
            True if load was successful.
        """
        
        try:
            # Prepare output directory
            output_dir = self.settings.get_data_path("hackernews")
            self.settings.create_directories()
                        output_dir.mkdir(parents=True, exist_ok=True)                        # Convert to dictionaries for serialization            articles_data = []            for article in data:                if hasattr(article, 'model_dump'):                    articles_data.append(article.model_dump())                elif hasattr(article, 'dict'):                    articles_data.append(article.dict())                else:                    articles_data.append(dict(article))
            
            # Save as JSON
            import json
            json_file = output_dir / "hackernews_enhanced.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(articles_data, f, indent=2, default=str)
            
            
            # Save as CSV using pandas
            try:
                import pandas as pd
                csv_file = output_dir / "hackernews_enhanced.csv"
                
                # Flatten the data for CSV
                flattened_data = []
                for article in articles_data:
                    flat_article = article.copy()
                    # Convert URL to string for CSV
                    if 'url' in flat_article:
                        flat_article['url'] = str(flat_article['url'])
                    flattened_data.append(flat_article)
                
                df = pd.DataFrame(flattened_data)
                df.to_csv(csv_file, index=False)
                self.logger.info(f"Saved CSV to {csv_file}")
                
            except ImportError:
            except Exception as e:
                self.logger.error(f"Error saving CSV: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading articles: {e}")
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
        print(f"\n📊 ETL Results:")
        print(f"✓ Success: {success}")
        print(f"✓ Duration: {metrics.duration_seconds:.2f} seconds")
        print(f"✓ Items extracted: {metrics.items_extracted}")
        print(f"✓ Items transformed: {metrics.items_transformed}")
        print(f"✓ Items loaded: {metrics.items_loaded}")
        print(f"✓ Success rate: {metrics.success_rate:.1f}%")
        
        if success:
            print(f"\n🎉 Enhanced HackerNews ETL completed successfully!")
            print(f"📁 Data saved to: data/hackernews/")
        else:
            print(f"\n❌ ETL process failed")
            return 1
            
    except Exception as e:
        print(f"\n❌ ETL process failed with error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 