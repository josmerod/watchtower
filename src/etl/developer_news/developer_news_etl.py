"""ETL pipeline for Developer News & Tips Aggregator."""

import logging
import os
import json
from datetime import datetime
from typing import List, Dict, Any

import requests
from pydantic import ValidationError

from src.etl.base import BaseETL
from src.models.developer_news_model import DeveloperNewsItem, NewsSourceType
from src.intelligence.news_intelligence import NewsSummarizer, RelevanceScorer, TrendDetector

logger = logging.getLogger(__name__)


class DeveloperNewsETL(BaseETL):
    """ETL pipeline for aggregating developer news."""

    def __init__(self):
        super().__init__(
            name="developer_news",
            description="Aggregates developer news from HackerNews, Dev.to, and NewsAPI",
            enable_enrichment=True
        )
        self.summarizer = NewsSummarizer()
        self.relevance_scorer = RelevanceScorer() # Uses default stack for now
        # API Keys
        self.news_api_key = os.getenv("NEWS_API_KEY")

    def extract(self) -> List[Dict[str, Any]]:
        """Extract news from configured sources."""
        raw_items = []
        
        # 1. Hacker News (Top Stories)
        try:
            hn_ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()[:30] # Limit to top 30
            for item_id in hn_ids:
                item_details = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json").json()
                if item_details and "url" in item_details:
                    raw_items.append({
                        "source": NewsSourceType.HACKERNEWS,
                        "data": item_details
                    })
        except Exception as e:
            logger.error(f"Failed to fetch HackerNews: {e}")

        # 2. Dev.to (Articles)
        try:
            devto_articles = requests.get("https://dev.to/api/articles?top=1").json()
            for article in devto_articles[:20]:
                raw_items.append({
                    "source": NewsSourceType.DEVTO,
                    "data": article
                })
        except Exception as e:
            logger.error(f"Failed to fetch Dev.to: {e}")
            
        # 3. NewsAPI (Technology) if key exists
        if self.news_api_key:
            try:
                url = f"https://newsapi.org/v2/top-headlines?category=technology&language=en&apiKey={self.news_api_key}"
                response = requests.get(url).json()
                if response.get("status") == "ok":
                    for article in response.get("articles", [])[:20]:
                        raw_items.append({
                            "source": NewsSourceType.NEWSAPI,
                            "data": article
                        })
            except Exception as e:
                logger.error(f"Failed to fetch NewsAPI: {e}")

        logger.info(f"Extracted {len(raw_items)} raw news items")
        return raw_items

    def transform(self, data: List[Dict[str, Any]]) -> List[DeveloperNewsItem]:
        """Transform raw data into standardized news items."""
        transformed_items = []
        
        for raw in data:
            try:
                source_type = raw["source"]
                item_data = raw["data"]
                
                news_item = None
                
                if source_type == NewsSourceType.HACKERNEWS:
                    news_item = DeveloperNewsItem(
                        id=str(item_data.get("id")),
                        title=item_data.get("title", "No Title"),
                        url=item_data.get("url", "https://news.ycombinator.com"),
                        source=NewsSourceType.HACKERNEWS,
                        author=item_data.get("by"),
                        published_at=datetime.fromtimestamp(item_data.get("time", datetime.now().timestamp())),
                        original_score=item_data.get("score"),
                        comments_count=item_data.get("descendants"),
                        tags=["tech", "hackernews"] # Basic tags
                    )
                    
                elif source_type == NewsSourceType.DEVTO:
                    news_item = DeveloperNewsItem(
                        id=str(item_data.get("id")),
                        title=item_data.get("title", "No Title"),
                        url=item_data.get("url"),
                        source=NewsSourceType.DEVTO,
                        author=item_data.get("user", {}).get("name"),
                        published_at=datetime.fromisoformat(item_data.get("published_at").replace("Z", "+00:00")),
                        summary=self.summarizer.summarize(item_data.get("description") or ""),
                        tags=item_data.get("tag_list", []),
                        original_score=item_data.get("positive_reactions_count"),
                        comments_count=item_data.get("comments_count")
                    )

                elif source_type == NewsSourceType.NEWSAPI:
                    news_item = DeveloperNewsItem(
                        id=item_data.get("url"), # URL as ID
                        title=item_data.get("title", "No Title"),
                        url=item_data.get("url"),
                        source=NewsSourceType.NEWSAPI,
                        author=item_data.get("author"),
                        published_at=datetime.fromisoformat(item_data.get("publishedAt").replace("Z", "+00:00")),
                        summary=self.summarizer.summarize(item_data.get("description") or ""),
                        tags=["news", "general"]
                    )

                if news_item:
                    # Apply Relevance Scoring
                    news_item.relevance_score = self.relevance_scorer.score(news_item)
                    transformed_items.append(news_item)
                    
            except ValidationError as e:
                logger.warning(f"Skipping invalid item: {e}")
            except Exception as e:
                logger.warning(f"Error transforming item: {e}")

        # Post-transformation: Calculate Trends
        trend_detector = TrendDetector()
        trends = trend_detector.detect_trends(transformed_items)
        
        # We could save trends separately, but for now let's just log them or attach to metadata if we had a container
        # Since BaseETL saves the list of items, we'll need a mechanism to save trends too. 
        # For simplicity in this iteration, we won't modify the return signature, but ideally we should save trends file separately.
        
        logger.info(f"Transformed {len(transformed_items)} items. Detected {len(trends)} trends.")
        return transformed_items

    def load(self, data: List[DeveloperNewsItem]):
        """Load data to JSON file."""
        if not data:
            self.logger.info("No data to load")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"news_batch_{timestamp}.json"
        output_path = self.output_dir / filename
        
        try:
            # Save items
            with open(output_path, "w", encoding="utf-8") as f:
                json_data = [item.dict() for item in data]
                json.dump(json_data, f, indent=2, default=str)
                
            self.logger.info(f"Saved {len(data)} items to {output_path}")
            
            # Save "latest" pointer for easy dashboard access
            latest_path = self.output_dir / "latest_news.json"
            with open(latest_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Failed to save output: {e}")
            raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    etl = DeveloperNewsETL()
    etl.run()
