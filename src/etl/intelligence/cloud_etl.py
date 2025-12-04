"""Cloud Intelligence ETL pipeline."""

import feedparser
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.etl.intelligence.base_intelligence_etl import BaseIntelligenceETL
from src.models.cloud import (
    CloudUpdate,
    CloudProvider,
    UpdateCategory
)
from src.utils.logging import get_logger

logger = get_logger("CloudETL")

class CloudIntelligenceETL(BaseIntelligenceETL):
    """ETL for Cloud Computing Intelligence."""
    
    def __init__(self):
        """Initialize the Cloud ETL."""
        super().__init__(
            name="cloud"
        )
        
        # RSS Feeds
        self.feeds = [
            {
                "url": "https://aws.amazon.com/about-aws/whats-new/recent/feed/",
                "name": "AWS What's New",
                "provider": CloudProvider.AWS
            },
            {
                "url": "https://azurecomcdn.azureedge.net/en-us/updates/feed/",
                "name": "Azure Updates",
                "provider": CloudProvider.AZURE
            },
            {
                "url": "https://cloud.google.com/feeds/google-cloud-release-notes.xml",
                "name": "Google Cloud Release Notes",
                "provider": CloudProvider.GCP
            }
        ]
        
        # Keywords for categorization
        self.category_keywords = {
            UpdateCategory.SECURITY: ["security", "vulnerability", "patch", "compliance", "guardduty", "sentinel", "armor"],
            UpdateCategory.COST: ["price", "cost", "billing", "savings", "reduction", "free tier"],
            UpdateCategory.REGION: ["region", "availability zone", "location", "expansion"],
            UpdateCategory.COMPLIANCE: ["compliance", "certification", "gdpr", "hipaa", "soc"],
        }

    def extract(self) -> List[Dict[str, Any]]:
        """Extract cloud updates from sources.
        
        Returns:
            List of raw data dictionaries
        """
        raw_items = []
        
        for feed in self.feeds:
            try:
                logger.info(f"Fetching feed: {feed['name']}")
                parsed = feedparser.parse(feed["url"])
                
                for entry in parsed.entries:
                    item = {
                        "title": entry.title,
                        "link": entry.link,
                        "description": getattr(entry, "summary", "") or getattr(entry, "description", ""),
                        "published": getattr(entry, "published", str(datetime.now())),
                        "provider": feed["provider"],
                        "source_name": feed["name"]
                    }
                    raw_items.append(item)
                    
            except Exception as e:
                logger.error(f"Error fetching feed {feed['name']}: {e}")
                
        logger.info(f"Extracted {len(raw_items)} items")
        return raw_items

    def transform(self, raw_data: List[Dict[str, Any]]) -> List[CloudUpdate]:
        """Transform raw data into CloudUpdate models.
        
        Args:
            raw_data: List of raw item dictionaries
            
        Returns:
            List of CloudUpdate objects
        """
        updates = []
        
        for item in raw_data:
            try:
                # Determine category
                category = self._determine_category(item["title"], item["description"])
                
                # Check implications
                cost_impl = category == UpdateCategory.COST or "cost" in item["description"].lower()
                sec_impl = category == UpdateCategory.SECURITY or "security" in item["description"].lower()
                
                # Parse date (simplified)
                try:
                    # feedparser usually handles this, but we fallback to now if needed
                    # For now, just use current time if parsing fails or if it's a string
                    # In a real app, we'd use dateutil.parser
                    published_at = datetime.now() 
                except:
                    published_at = datetime.now()

                update = CloudUpdate(
                    update_id=self._generate_id(item["link"]),
                    title=item["title"],
                    provider=item["provider"],
                    description=item["description"][:500] + "..." if len(item["description"]) > 500 else item["description"],
                    summary=item["title"],
                    link=item["link"],
                    published_at=published_at,
                    category=category,
                    cost_implication=cost_impl,
                    security_implication=sec_impl,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                updates.append(update)
                
            except Exception as e:
                logger.error(f"Error transforming item {item.get('title', 'unknown')}: {e}")
                
        return updates

    def load(self, data: List[CloudUpdate]) -> None:
        """Load transformed data to storage.
        
        Args:
            data: List of CloudUpdate objects
        """
        output_file = self.output_dir / "cloud_updates.json"
        
        # Convert to dicts
        json_data = [p.model_dump(mode='json') for p in data]
        
        # Save
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved {len(data)} updates to {output_file}")

    def _determine_category(self, title: str, description: str) -> UpdateCategory:
        """Determine update category from text."""
        text = (title + " " + description).lower()
        
        for category, keywords in self.category_keywords.items():
            if any(k in text for k in keywords):
                return category
                
        return UpdateCategory.FEATURE  # Default

    def _generate_id(self, link: str) -> str:
        """Generate a unique ID from the link."""
        import hashlib
        return hashlib.md5(link.encode()).hexdigest()

if __name__ == "__main__":
    etl = CloudIntelligenceETL()
    etl.run()
