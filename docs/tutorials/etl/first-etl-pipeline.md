# Building Your First ETL Pipeline

Learn how to create a complete ETL pipeline with Watchtower by building a real-world news aggregation system. This tutorial takes you step-by-step through extracting data from multiple sources, transforming it, and loading it into a structured format.

## 🎯 What You'll Build

By the end of this tutorial, you'll have created:
- **Multi-source news aggregator** that combines data from RSS feeds and APIs
- **Data cleaning and enrichment pipeline** with sentiment analysis
- **Flexible output formats** (JSON, CSV, database)
- **Error handling and recovery** for robust operation
- **Performance monitoring** with metrics and logging

## 📋 Prerequisites

- Completed the [Complete Beginner's Guide](../getting-started/complete-beginners-guide.md)
- Basic understanding of Python
- Familiarity with JSON and CSV formats
- About 45 minutes

## 🏗️ Architecture Overview

Our ETL pipeline will follow this pattern:

```
[RSS Feeds] ──┐
              ├─► [Extract] ──► [Transform] ──► [Load] ──► [Files/DB]
[APIs] ───────┘
```

**Components:**
- **Extract**: Fetch from RSS feeds and APIs
- **Transform**: Clean, validate, and enrich data
- **Load**: Save to multiple formats with error handling

---

## 🚀 Step 1: Understanding BaseETL

Watchtower's `BaseETL` class provides a robust foundation for ETL pipelines with built-in features:

- **Error handling** with automatic retries
- **Checkpointing** for recovery from failures
- **Performance metrics** tracking
- **Structured logging** for debugging
- **Batch processing** for large datasets

### Basic ETL Structure

```python
from src.etl.base import BaseETL
from typing import List, Dict, Any

class MyETL(BaseETL):
    def extract(self) -> List[Dict[str, Any]]:
        """Fetch raw data from sources"""
        pass
    
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean and process the data"""
        pass
    
    def load(self, data: List[Dict[str, Any]]) -> None:
        """Save processed data"""
        pass
```

---

## 📰 Step 2: Creating the News Aggregator ETL

Let's build a comprehensive news aggregation system that demonstrates real-world ETL patterns.

### Create the Main ETL File

Create `news_aggregator_etl.py`:

```python
#!/usr/bin/env python3
"""
News Aggregator ETL - A comprehensive example of multi-source data aggregation
"""

from src.etl.base import SimpleETL
from typing import List, Dict, Any, Optional
import requests
import feedparser
from datetime import datetime, timedelta
import hashlib
import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import time
import json

class NewsAggregatorETL(SimpleETL):
    """
    Advanced ETL pipeline that aggregates news from multiple sources
    including RSS feeds, APIs, and web scraping.
    """
    
    def __init__(self):
        super().__init__(
            name="news_aggregator",
            description="Multi-source news aggregation with enrichment",
            batch_size=50  # Process in batches of 50 articles
        )
        
        # Configuration for news sources
        self.rss_sources = [
            {
                "name": "Hacker News",
                "url": "https://hnrss.org/frontpage",
                "category": "tech"
            },
            {
                "name": "TechCrunch",
                "url": "https://feeds.feedburner.com/TechCrunch",
                "category": "tech"
            },
            {
                "name": "BBC World",
                "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
                "category": "world"
            }
        ]
        
        self.api_sources = [
            {
                "name": "NewsAPI",
                "url": "https://newsapi.org/v2/top-headlines",
                "params": {
                    "country": "us",
                    "category": "technology",
                    "apiKey": "demo"  # Replace with real API key
                },
                "category": "tech"
            }
        ]
        
        # Data enrichment settings
        self.min_content_length = 100
        self.max_title_length = 200
        self.extract_summary_length = 300
    
    def extract(self) -> List[Dict[str, Any]]:
        """Extract articles from all configured sources"""
        self.logger.info("Starting extraction from multiple news sources...")
        
        all_articles = []
        
        # Extract from RSS feeds
        for source in self.rss_sources:
            try:
                articles = self._extract_from_rss(source)
                all_articles.extend(articles)
                self.logger.info(f"Extracted {len(articles)} articles from {source['name']}")
                time.sleep(1)  # Rate limiting
            except Exception as e:
                self.logger.error(f"Failed to extract from {source['name']}: {e}")
        
        # Extract from APIs
        for source in self.api_sources:
            try:
                articles = self._extract_from_api(source)
                all_articles.extend(articles)
                self.logger.info(f"Extracted {len(articles)} articles from {source['name']}")
                time.sleep(1)  # Rate limiting
            except Exception as e:
                self.logger.error(f"Failed to extract from {source['name']}: {e}")
        
        self.logger.info(f"Total articles extracted: {len(all_articles)}")
        return all_articles
    
    def _extract_from_rss(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract articles from an RSS feed"""
        feed = feedparser.parse(source["url"])
        articles = []
        
        for entry in feed.entries:
            article = {
                "title": getattr(entry, 'title', ''),
                "url": getattr(entry, 'link', ''),
                "description": getattr(entry, 'summary', ''),
                "published": self._parse_date(getattr(entry, 'published', '')),
                "source": source["name"],
                "category": source["category"],
                "extraction_method": "rss",
                "raw_data": {
                    "tags": [tag.term for tag in getattr(entry, 'tags', [])],
                    "author": getattr(entry, 'author', ''),
                }
            }
            articles.append(article)
        
        return articles
    
    def _extract_from_api(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract articles from a REST API"""
        try:
            response = requests.get(source["url"], params=source["params"], timeout=30)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for item in data.get("articles", []):
                article = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "published": self._parse_date(item.get("publishedAt", "")),
                    "source": source["name"],
                    "category": source["category"],
                    "extraction_method": "api",
                    "raw_data": {
                        "author": item.get("author", ""),
                        "source_name": item.get("source", {}).get("name", ""),
                        "url_to_image": item.get("urlToImage", "")
                    }
                }
                articles.append(article)
            
            return articles
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return []
    
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform and enrich the extracted articles"""
        self.logger.info(f"Transforming {len(data)} articles...")
        
        transformed_articles = []
        seen_urls = set()
        
        for article in data:
            try:
                # Remove duplicates based on URL
                if article["url"] in seen_urls:
                    continue
                seen_urls.add(article["url"])
                
                # Clean and validate the article
                cleaned_article = self._clean_article(article)
                
                # Skip articles that don't meet quality criteria
                if not self._is_valid_article(cleaned_article):
                    continue
                
                # Enrich the article with additional data
                enriched_article = self._enrich_article(cleaned_article)
                
                transformed_articles.append(enriched_article)
                
            except Exception as e:
                self.logger.warning(f"Failed to transform article {article.get('url', 'unknown')}: {e}")
                continue
        
        self.logger.info(f"Transformation complete: {len(transformed_articles)} valid articles")
        return transformed_articles
    
    def _clean_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and standardize article data"""
        cleaned = article.copy()
        
        # Clean title
        cleaned["title"] = self._clean_text(article.get("title", ""))
        if len(cleaned["title"]) > self.max_title_length:
            cleaned["title"] = cleaned["title"][:self.max_title_length] + "..."
        
        # Clean description
        cleaned["description"] = self._clean_text(article.get("description", ""))
        
        # Standardize URL
        cleaned["url"] = article.get("url", "").strip()
        
        # Generate article ID
        cleaned["article_id"] = self._generate_article_id(cleaned["url"], cleaned["title"])
        
        # Standardize timestamps
        cleaned["published"] = self._standardize_timestamp(article.get("published"))
        cleaned["extracted_at"] = datetime.now().isoformat()
        
        # Extract domain from URL
        cleaned["domain"] = self._extract_domain(cleaned["url"])
        
        return cleaned
    
    def _enrich_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Add enrichment data to the article"""
        enriched = article.copy()
        
        # Add text analysis
        enriched["text_analysis"] = {
            "title_word_count": len(article["title"].split()),
            "description_word_count": len(article["description"].split()),
            "estimated_read_time": self._estimate_read_time(article["description"]),
            "contains_numbers": bool(re.search(r'\d+', article["title"])),
            "contains_keywords": self._contains_tech_keywords(article["title"] + " " + article["description"])
        }
        
        # Add metadata
        enriched["metadata"] = {
            "processing_version": "1.0",
            "quality_score": self._calculate_quality_score(article),
            "freshness_hours": self._calculate_freshness(article["published"]),
            "is_breaking_news": self._is_breaking_news(article),
            "language_detected": "en"  # Could use langdetect library
        }
        
        # Add categorization
        enriched["categorization"] = {
            "primary_category": article["category"],
            "tags": self._extract_tags(article),
            "confidence": 0.8  # Would be from ML model in real implementation
        }
        
        return enriched
    
    def load(self, data: List[Dict[str, Any]]) -> None:
        """Load the processed articles to multiple destinations"""
        self.logger.info(f"Loading {len(data)} articles...")
        
        # Save full dataset as JSON
        self.save_as_json(data, "news_articles_full.json")
        
        # Save summarized version as CSV
        summary_data = self._create_summary_data(data)
        self.save_as_csv(summary_data, "news_articles_summary.csv")
        
        # Save by category
        self._save_by_category(data)
        
        # Save metrics report
        self._save_metrics_report(data)
        
        self.logger.info("Loading complete - data saved to multiple formats")
    
    def _save_by_category(self, data: List[Dict[str, Any]]) -> None:
        """Save articles grouped by category"""
        categories = {}
        
        for article in data:
            category = article.get("category", "unknown")
            if category not in categories:
                categories[category] = []
            categories[category].append(article)
        
        for category, articles in categories.items():
            filename = f"news_articles_{category}.json"
            self.save_as_json(articles, filename)
            self.logger.info(f"Saved {len(articles)} {category} articles")
    
    def _save_metrics_report(self, data: List[Dict[str, Any]]) -> None:
        """Generate and save processing metrics"""
        metrics = {
            "processing_summary": {
                "total_articles": len(data),
                "processing_date": datetime.now().isoformat(),
                "sources_processed": len(set(article["source"] for article in data)),
                "categories": list(set(article["category"] for article in data))
            },
            "quality_metrics": {
                "average_quality_score": sum(article["metadata"]["quality_score"] for article in data) / len(data),
                "high_quality_articles": len([a for a in data if a["metadata"]["quality_score"] > 0.7]),
                "breaking_news_count": len([a for a in data if a["metadata"]["is_breaking_news"]])
            },
            "content_analysis": {
                "average_title_length": sum(len(article["title"]) for article in data) / len(data),
                "articles_with_keywords": len([a for a in data if a["text_analysis"]["contains_keywords"]]),
                "total_estimated_read_time": sum(article["text_analysis"]["estimated_read_time"] for article in data)
            }
        }
        
        self.save_as_json(metrics, "processing_metrics.json")
    
    # Utility methods
    def _clean_text(self, text: str) -> str:
        """Clean text by removing HTML, extra whitespace, etc."""
        if not text:
            return ""
        
        # Remove HTML tags
        text = BeautifulSoup(text, "html.parser").get_text()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse various date formats into ISO format"""
        if not date_str:
            return None
        
        try:
            # Try common formats
            for fmt in ["%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            # Fallback to feedparser's parsing
            import email.utils
            parsed = email.utils.parsedate_to_datetime(date_str)
            return parsed.isoformat()
            
        except Exception:
            return None
    
    def _standardize_timestamp(self, timestamp: Optional[str]) -> str:
        """Ensure timestamp is in standard ISO format"""
        if not timestamp:
            return datetime.now().isoformat()
        
        try:
            # If already ISO format, validate it
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return timestamp
        except ValueError:
            return datetime.now().isoformat()
    
    def _generate_article_id(self, url: str, title: str) -> str:
        """Generate unique ID for article"""
        content = f"{url}:{title}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.replace('www.', '')
        except Exception:
            return "unknown"
    
    def _is_valid_article(self, article: Dict[str, Any]) -> bool:
        """Check if article meets quality criteria"""
        # Must have title and URL
        if not article.get("title") or not article.get("url"):
            return False
        
        # Title must be reasonable length
        if len(article["title"]) < 10:
            return False
        
        # Must have some description
        if len(article.get("description", "")) < self.min_content_length:
            return False
        
        # URL must be valid
        if not article["url"].startswith(("http://", "https://")):
            return False
        
        return True
    
    def _estimate_read_time(self, text: str) -> int:
        """Estimate reading time in minutes (assumes 200 words per minute)"""
        word_count = len(text.split())
        return max(1, word_count // 200)
    
    def _contains_tech_keywords(self, text: str) -> bool:
        """Check if text contains technology-related keywords"""
        keywords = [
            "AI", "artificial intelligence", "machine learning", "ML", "technology",
            "software", "programming", "developer", "startup", "innovation",
            "digital", "cyber", "cloud", "data", "algorithm", "API"
        ]
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)
    
    def _calculate_quality_score(self, article: Dict[str, Any]) -> float:
        """Calculate quality score based on various factors"""
        score = 0.5  # Base score
        
        # Title quality
        if 20 <= len(article["title"]) <= 100:
            score += 0.1
        
        # Description quality
        if len(article["description"]) >= 200:
            score += 0.2
        
        # Recency bonus
        freshness_hours = self._calculate_freshness(article["published"])
        if freshness_hours <= 24:
            score += 0.1
        elif freshness_hours <= 72:
            score += 0.05
        
        # Source credibility (simplified)
        trusted_sources = ["BBC", "Reuters", "TechCrunch", "Hacker News"]
        if any(source.lower() in article["source"].lower() for source in trusted_sources):
            score += 0.1
        
        return min(1.0, score)
    
    def _calculate_freshness(self, published: Optional[str]) -> float:
        """Calculate how many hours ago the article was published"""
        if not published:
            return 9999  # Very old
        
        try:
            pub_date = datetime.fromisoformat(published.replace('Z', '+00:00'))
            now = datetime.now()
            delta = now - pub_date.replace(tzinfo=None)
            return delta.total_seconds() / 3600
        except Exception:
            return 9999
    
    def _is_breaking_news(self, article: Dict[str, Any]) -> bool:
        """Determine if this is breaking news"""
        breaking_keywords = ["breaking", "urgent", "alert", "just in", "developing"]
        title_lower = article["title"].lower()
        return any(keyword in title_lower for keyword in breaking_keywords)
    
    def _extract_tags(self, article: Dict[str, Any]) -> List[str]:
        """Extract relevant tags from article content"""
        tags = []
        
        # Add category as tag
        tags.append(article["category"])
        
        # Add source type
        tags.append(article["extraction_method"])
        
        # Add content-based tags
        content = f"{article['title']} {article['description']}".lower()
        
        if any(word in content for word in ["startup", "funding", "investment"]):
            tags.append("business")
        
        if any(word in content for word in ["python", "javascript", "programming", "code"]):
            tags.append("programming")
        
        if "security" in content or "hack" in content:
            tags.append("security")
        
        return list(set(tags))  # Remove duplicates
    
    def _create_summary_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create simplified version for CSV export"""
        summary = []
        
        for article in data:
            summary_item = {
                "id": article["article_id"],
                "title": article["title"],
                "url": article["url"],
                "source": article["source"],
                "category": article["category"],
                "published": article["published"],
                "quality_score": article["metadata"]["quality_score"],
                "is_breaking_news": article["metadata"]["is_breaking_news"],
                "read_time_minutes": article["text_analysis"]["estimated_read_time"],
                "word_count": article["text_analysis"]["description_word_count"],
                "domain": article["domain"]
            }
            summary.append(summary_item)
        
        return summary


def main():
    """Run the news aggregation ETL pipeline"""
    print("🚀 Starting News Aggregator ETL Pipeline")
    print("=" * 60)
    
    # Create and run the ETL
    etl = NewsAggregatorETL()
    
    print("📊 ETL Configuration:")
    print(f"   - RSS Sources: {len(etl.rss_sources)}")
    print(f"   - API Sources: {len(etl.api_sources)}")
    print(f"   - Batch Size: {etl.batch_size}")
    print()
    
    # Run the pipeline
    metrics = etl.run()
    
    # Display results
    print(f"\n✅ News Aggregation Complete!")
    print(f"📊 Articles processed: {metrics.records_loaded}")
    print(f"⏱️  Total duration: {metrics.duration_seconds:.2f} seconds")
    print(f"📈 Success rate: {metrics.success_rate:.1f}%")
    print(f"⚠️  Errors encountered: {metrics.error_count}")
    
    # Show output files
    data_dir = etl.get_data_dir()
    print(f"\n📁 Output files saved to: {data_dir}")
    print("   📋 Generated files:")
    print("   - news_articles_full.json      (Complete dataset)")
    print("   - news_articles_summary.csv    (Summary for analysis)")
    print("   - news_articles_tech.json      (Tech articles only)")
    print("   - news_articles_world.json     (World news only)")
    print("   - processing_metrics.json      (Pipeline metrics)")
    
    print(f"\n🎯 Next Steps:")
    print("   1. Explore the generated data files")
    print("   2. Customize the sources in the ETL configuration")
    print("   3. Add your own data enrichment logic")
    print("   4. Set up scheduling for regular execution")


if __name__ == "__main__":
    main()
```

---

## 🎯 Step 3: Running and Testing Your ETL

### Run the Complete Pipeline

```bash
python news_aggregator_etl.py
```

**Expected Output:**
```
🚀 Starting News Aggregator ETL Pipeline
============================================================
📊 ETL Configuration:
   - RSS Sources: 3
   - API Sources: 1
   - Batch Size: 50

[INFO] Starting extraction from multiple news sources...
[INFO] Extracted 30 articles from Hacker News
[INFO] Extracted 25 articles from TechCrunch
[INFO] Extracted 20 articles from BBC World
[INFO] Total articles extracted: 75
[INFO] Transforming 75 articles...
[INFO] Transformation complete: 68 valid articles
[INFO] Loading 68 articles...
[INFO] Saved 45 tech articles
[INFO] Saved 15 world articles
[INFO] Loading complete - data saved to multiple formats

✅ News Aggregation Complete!
📊 Articles processed: 68
⏱️  Total duration: 12.34 seconds
📈 Success rate: 90.7%
⚠️  Errors encountered: 7
```

### Explore the Generated Data

```bash
# Check the output directory
ls -la data/news_aggregator/

# Preview the full dataset
head -50 data/news_aggregator/news_articles_full.json

# Check the summary CSV
head -10 data/news_aggregator/news_articles_summary.csv

# Review processing metrics
cat data/news_aggregator/processing_metrics.json
```

---

## 🔧 Step 4: Customizing Your ETL

### Adding New Data Sources

To add your own news source, modify the source configuration:

```python
# Add to rss_sources
self.rss_sources.append({
    "name": "Your News Site",
    "url": "https://yournewssite.com/rss",
    "category": "custom"
})

# Add to api_sources  
self.api_sources.append({
    "name": "Your API",
    "url": "https://yourapi.com/news",
    "params": {"key": "your_api_key"},
    "category": "custom"
})
```

### Custom Data Enrichment

Add your own enrichment logic:

```python
def _enrich_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
    enriched = super()._enrich_article(article)
    
    # Your custom enrichment
    enriched["custom_analysis"] = {
        "sentiment_score": self._analyze_sentiment(article["description"]),
        "topic_classification": self._classify_topic(article["title"]),
        "spam_probability": self._detect_spam(article)
    }
    
    return enriched
```

### Advanced Error Handling

Add custom error recovery:

```python
def extract(self) -> List[Dict[str, Any]]:
    try:
        return super().extract()
    except Exception as e:
        # Custom error handling
        self.logger.error(f"Extraction failed: {e}")
        
        # Try fallback sources
        return self._extract_from_fallback_sources()
```

---

## 📊 Step 5: Performance Optimization

### Batch Processing

For large datasets, optimize batch processing:

```python
def __init__(self):
    super().__init__(
        name="news_aggregator",
        batch_size=100,  # Process 100 articles at once
        enable_checkpointing=True  # Enable recovery
    )

def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Process in smaller sub-batches for memory efficiency
    return self.process_in_batches(
        data, 
        self._transform_batch, 
        batch_size=25
    )
```

### Parallel Processing

Add concurrent processing for multiple sources:

```python
import asyncio
import aiohttp

async def extract_async(self) -> List[Dict[str, Any]]:
    """Async extraction for better performance"""
    tasks = []
    
    # Create tasks for all sources
    for source in self.rss_sources:
        tasks.append(self._extract_from_rss_async(source))
    
    # Execute concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Combine results
    all_articles = []
    for result in results:
        if not isinstance(result, Exception):
            all_articles.extend(result)
    
    return all_articles
```

### Caching and Rate Limiting

Add intelligent caching:

```python
import time
from functools import lru_cache

class NewsAggregatorETL(SimpleETL):
    def __init__(self):
        super().__init__()
        self.last_request_time = {}
        self.min_request_interval = 1  # 1 second between requests
    
    @lru_cache(maxsize=100)
    def _fetch_with_cache(self, url: str) -> str:
        """Cache responses to avoid redundant requests"""
        return self._fetch_url(url)
    
    def _rate_limit(self, source_name: str):
        """Implement rate limiting per source"""
        last_time = self.last_request_time.get(source_name, 0)
        current_time = time.time()
        
        if current_time - last_time < self.min_request_interval:
            time.sleep(self.min_request_interval - (current_time - last_time))
        
        self.last_request_time[source_name] = time.time()
```

---

## 🧪 Step 6: Testing and Validation

### Create Test Cases

Create `test_news_etl.py`:

```python
import unittest
from news_aggregator_etl import NewsAggregatorETL

class TestNewsAggregatorETL(unittest.TestCase):
    def setUp(self):
        self.etl = NewsAggregatorETL()
    
    def test_article_cleaning(self):
        """Test article cleaning functionality"""
        dirty_article = {
            "title": "  Test Article  <script>alert('xss')</script>  ",
            "url": "https://example.com/test",
            "description": "Test description"
        }
        
        cleaned = self.etl._clean_article(dirty_article)
        
        self.assertEqual(cleaned["title"], "Test Article")
        self.assertIn("article_id", cleaned)
        self.assertEqual(cleaned["domain"], "example.com")
    
    def test_validation(self):
        """Test article validation"""
        valid_article = {
            "title": "Valid Test Article Title",
            "url": "https://example.com/valid",
            "description": "This is a valid description that is long enough to pass validation criteria and contains meaningful content."
        }
        
        invalid_article = {
            "title": "Bad",
            "url": "invalid-url",
            "description": "Too short"
        }
        
        self.assertTrue(self.etl._is_valid_article(valid_article))
        self.assertFalse(self.etl._is_valid_article(invalid_article))

if __name__ == "__main__":
    unittest.main()
```

### Run Tests

```bash
python test_news_etl.py
```

### Validate Output Data

Create validation scripts:

```python
def validate_etl_output():
    """Validate the ETL pipeline output"""
    import json
    
    # Load the output data
    with open("data/news_aggregator/news_articles_full.json") as f:
        articles = json.load(f)
    
    print(f"📊 Validation Report")
    print(f"=" * 40)
    print(f"Total articles: {len(articles)}")
    
    # Check required fields
    required_fields = ["article_id", "title", "url", "source", "category"]
    missing_fields = []
    
    for article in articles:
        for field in required_fields:
            if field not in article:
                missing_fields.append(f"Article {article.get('article_id', 'unknown')} missing {field}")
    
    if missing_fields:
        print(f"❌ Validation failed: {len(missing_fields)} issues found")
        for issue in missing_fields[:5]:  # Show first 5
            print(f"   - {issue}")
    else:
        print(f"✅ All articles have required fields")
    
    # Check data quality
    quality_scores = [a["metadata"]["quality_score"] for a in articles]
    avg_quality = sum(quality_scores) / len(quality_scores)
    print(f"📈 Average quality score: {avg_quality:.2f}")
    
    # Check categories
    categories = set(a["category"] for a in articles)
    print(f"📂 Categories found: {', '.join(categories)}")

if __name__ == "__main__":
    validate_etl_output()
```

---

## 🚀 Step 7: Next Steps and Advanced Features

### Scheduling Your ETL

Set up regular execution with cron or Windows Task Scheduler:

```bash
# Run every hour
0 * * * * cd /path/to/watchtower && python news_aggregator_etl.py

# Run every 6 hours
0 */6 * * * cd /path/to/watchtower && python news_aggregator_etl.py
```

### Database Integration

Extend the ETL to save to a database:

```python
def load(self, data: List[Dict[str, Any]]) -> None:
    # Save to files (existing functionality)
    super().load(data)
    
    # Also save to database
    self._save_to_database(data)

def _save_to_database(self, data: List[Dict[str, Any]]) -> None:
    """Save articles to a database"""
    # Implementation depends on your database choice
    # SQLite, PostgreSQL, MongoDB, etc.
    pass
```

### Real-time Processing

Convert to a streaming ETL:

```python
def run_streaming(self):
    """Run ETL in streaming mode"""
    while True:
        try:
            # Extract new data
            new_data = self.extract_incremental()
            
            if new_data:
                # Process immediately
                transformed = self.transform(new_data)
                self.load(transformed)
            
            # Wait before next check
            time.sleep(300)  # 5 minutes
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            self.logger.error(f"Streaming error: {e}")
            time.sleep(60)  # Wait 1 minute before retry
```

### Monitoring and Alerting

Add comprehensive monitoring:

```python
def run(self) -> ETLMetrics:
    metrics = super().run()
    
    # Send alerts based on metrics
    if metrics.error_count > 5:
        self._send_alert(f"High error count: {metrics.error_count}")
    
    if metrics.success_rate < 0.8:
        self._send_alert(f"Low success rate: {metrics.success_rate:.1%}")
    
    return metrics
```

---

## 🎯 Completion Checklist

You've successfully built a comprehensive ETL pipeline! Check off what you've accomplished:

- [ ] ✅ Created a multi-source news aggregation ETL
- [ ] ✅ Implemented robust error handling and logging
- [ ] ✅ Added data validation and quality scoring
- [ ] ✅ Created multiple output formats (JSON, CSV)
- [ ] ✅ Added performance metrics and monitoring
- [ ] ✅ Implemented data enrichment and analysis
- [ ] ✅ Created test cases for validation
- [ ] ✅ Learned optimization techniques

### What You've Learned

1. **ETL Architecture**: How to structure complex data pipelines
2. **Error Handling**: Building resilient data processing systems
3. **Data Quality**: Implementing validation and quality scoring
4. **Performance**: Optimizing for speed and memory efficiency
5. **Testing**: Validating ETL pipeline functionality
6. **Real-world Patterns**: Professional ETL development practices

---

## 📚 Further Reading

Ready to take your ETL skills to the next level?

- **[Advanced ETL Patterns](advanced-etl-patterns.md)**: Complex transformation techniques
- **[ETL Performance Optimization](etl-performance-optimization.md)**: Scale your pipelines
- **[Error Handling and Recovery](error-handling-recovery.md)**: Build bulletproof ETL systems
- **[Production Deployment](../operations/production-deployment.md)**: Deploy ETL to production
- **[Custom Component Development](../architecture/custom-component-development.md)**: Extend Watchtower

**Congratulations!** You now have the skills to build production-ready ETL pipelines with Watchtower. 🎉