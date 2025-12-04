"""Architecture Intelligence ETL pipeline."""

import feedparser
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.etl.intelligence.base_intelligence_etl import BaseIntelligenceETL
from src.models.architecture_pattern_model import (
    ArchitecturePattern,
    ArchitecturalStyle,
    ComplexityLevel,
    TeamSize
)
from src.utils.logging import get_logger

logger = get_logger("ArchitectureETL")

class ArchitectureIntelligenceETL(BaseIntelligenceETL):
    """ETL for Software Architecture Patterns Intelligence."""
    
    def __init__(self):
        """Initialize the Architecture ETL."""
        super().__init__(
            name="architecture"
        )
        
        # RSS Feeds
        self.feeds = [
            {
                "url": "http://feeds.feedburner.com/HighScalability",
                "name": "High Scalability",
                "style_hint": ArchitecturalStyle.MICROSERVICES  # Default hint
            },
            {
                "url": "https://aws.amazon.com/architecture/blog/feed/",
                "name": "AWS Architecture Blog",
                "style_hint": ArchitecturalStyle.SERVERLESS
            }
        ]
        
        # Keywords for pattern recognition
        self.style_keywords = {
            ArchitecturalStyle.MICROSERVICES: ["microservices", "service mesh", "containers", "kubernetes"],
            ArchitecturalStyle.EVENT_DRIVEN: ["event-driven", "kafka", "pub/sub", "messaging", "event sourcing"],
            ArchitecturalStyle.SERVERLESS: ["serverless", "lambda", "functions", "faas"],
            ArchitecturalStyle.MONOLITH: ["monolith", "legacy", "single deployment"],
            ArchitecturalStyle.LAYERED: ["layered", "n-tier", "presentation layer"],
            ArchitecturalStyle.HEXAGONAL: ["hexagonal", "ports and adapters", "clean architecture"],
            ArchitecturalStyle.CQRS: ["cqrs", "command query", "event sourcing"],
        }
        
        self.anti_pattern_keywords = [
            "bottleneck", "spaghetti", "coupling", "monolithic hell", "dependency hell",
            "over-engineering", "premature optimization"
        ]

    def extract(self) -> List[Dict[str, Any]]:
        """Extract architecture patterns from sources.
        
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
                        "source": feed["name"],
                        "style_hint": feed.get("style_hint")
                    }
                    raw_items.append(item)
                    
            except Exception as e:
                logger.error(f"Error fetching feed {feed['name']}: {e}")
                
        logger.info(f"Extracted {len(raw_items)} items")
        return raw_items

    def transform(self, raw_data: List[Dict[str, Any]]) -> List[ArchitecturePattern]:
        """Transform raw data into ArchitecturePattern models.
        
        Args:
            raw_data: List of raw item dictionaries
            
        Returns:
            List of ArchitecturePattern objects
        """
        patterns = []
        
        for item in raw_data:
            try:
                # Determine style
                style = self._determine_style(item["title"], item["description"], item.get("style_hint"))
                
                # Determine complexity
                complexity = self._determine_complexity(item["description"])
                
                # Extract tags
                tags = self._extract_tags(item["description"])
                
                # Check for anti-patterns
                pitfalls = self._detect_pitfalls(item["description"])
                
                pattern = ArchitecturePattern(
                    pattern_id=self._generate_id(item["link"]),
                    name=item["title"],
                    style=style,
                    description=item["description"][:500] + "..." if len(item["description"]) > 500 else item["description"],
                    summary=item["title"],
                    reference_urls=[item["link"]],
                    complexity=complexity,
                    tags=tags,
                    common_pitfalls=pitfalls,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                patterns.append(pattern)
                
            except Exception as e:
                logger.error(f"Error transforming item {item.get('title', 'unknown')}: {e}")
                
        return patterns

    def load(self, data: List[ArchitecturePattern]) -> None:
        """Load transformed data to storage.
        
        Args:
            data: List of ArchitecturePattern objects
        """
        output_file = self.output_dir / "architecture_patterns.json"
        
        # Convert to dicts
        json_data = [p.model_dump(mode='json') for p in data]
        
        # Save
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved {len(data)} patterns to {output_file}")

    def _determine_style(self, title: str, description: str, hint: Optional[ArchitecturalStyle]) -> ArchitecturalStyle:
        """Determine architectural style from text."""
        text = (title + " " + description).lower()
        
        for style, keywords in self.style_keywords.items():
            if any(k in text for k in keywords):
                return style
                
        return hint or ArchitecturalStyle.LAYERED  # Default fallback

    def _determine_complexity(self, text: str) -> ComplexityLevel:
        """Estimate complexity based on text length and keywords."""
        if len(text) > 2000 or "complex" in text.lower() or "distributed" in text.lower():
            return ComplexityLevel.HIGH
        return ComplexityLevel.MEDIUM

    def _extract_tags(self, text: str) -> List[str]:
        """Extract tags from text."""
        common_tags = ["cloud", "security", "performance", "scalability", "database", "api"]
        return [tag for tag in common_tags if tag in text.lower()]

    def _detect_pitfalls(self, text: str) -> List[str]:
        """Detect potential pitfalls/anti-patterns."""
        found = []
        for keyword in self.anti_pattern_keywords:
            if keyword in text.lower():
                found.append(f"Potential risk: {keyword}")
        return found

    def _generate_id(self, link: str) -> str:
        """Generate a unique ID from the link."""
        import hashlib
        return hashlib.md5(link.encode()).hexdigest()

if __name__ == "__main__":
    etl = ArchitectureIntelligenceETL()
    etl.run()
