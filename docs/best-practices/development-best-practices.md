# Best Practices Guide for Watchtower Development

This comprehensive guide outlines proven best practices for developing, deploying, and maintaining Watchtower-based applications. Follow these guidelines to build robust, scalable, and maintainable data monitoring solutions.

## 📋 Table of Contents

1. [Project Structure & Organization](#project-structure--organization)
2. [Code Quality & Standards](#code-quality--standards)
3. [ETL Pipeline Best Practices](#etl-pipeline-best-practices)
4. [Watcher System Best Practices](#watcher-system-best-practices)
5. [Configuration Management](#configuration-management)
6. [Error Handling & Logging](#error-handling--logging)
7. [Testing Strategies](#testing-strategies)
8. [Performance Optimization](#performance-optimization)
9. [Security Best Practices](#security-best-practices)
10. [Deployment & Operations](#deployment--operations)
11. [Monitoring & Alerting](#monitoring--alerting)
12. [Documentation Standards](#documentation-standards)

---

## 🏗️ Project Structure & Organization

### Recommended Project Layout

```
watchtower-project/
├── src/
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── news/
│   │   ├── finance/
│   │   └── social/
│   ├── watchers/
│   │   ├── __init__.py
│   │   ├── base_watcher.py
│   │   ├── price_watchers/
│   │   └── content_watchers/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── models.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logging.py
│   │   ├── file_system.py
│   │   └── network.py
│   └── web/
│       ├── __init__.py
│       └── dashboard/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── data/
│   ├── etl/
│   ├── watchers/
│   └── exports/
├── logs/
├── config/
│   ├── development.env
│   ├── staging.env
│   └── production.env
├── scripts/
│   ├── deploy.sh
│   ├── backup.sh
│   └── health_check.py
├── docs/
│   ├── api/
│   ├── deployment/
│   └── user_guides/
├── pyproject.toml
├── requirements.txt
├── .env.template
├── .gitignore
├── README.md
├── CHANGELOG.md
└── LICENSE
```

### Module Organization Best Practices

```python
# Good: Clear module structure
from src.etl.news.hacker_news import HackerNewsETL
from src.etl.finance.stock_prices import StockPriceETL
from src.watchers.content.website_monitor import WebsiteMonitor

# Bad: Everything in one module
from src.etl import NewsETL, StockETL, WebsiteWatcher
```

### Naming Conventions

```python
# Classes: PascalCase
class NewsAggregatorETL(BaseETL):
    pass

class PriceWatcher(BaseWatcher):
    pass

# Functions and variables: snake_case
def extract_articles_from_feed(feed_url: str) -> List[Dict[str, Any]]:
    pass

current_price = get_current_price()

# Constants: UPPER_SNAKE_CASE
DEFAULT_TIMEOUT = 30
MAX_RETRY_ATTEMPTS = 3

# Private methods: Leading underscore
def _validate_article_data(self, article: Dict[str, Any]) -> bool:
    pass
```

---

## 💎 Code Quality & Standards

### Type Hints and Documentation

```python
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

class NewsETL(BaseETL):
    """
    ETL pipeline for aggregating news articles from multiple sources.
    
    This class handles extraction from RSS feeds and APIs, data cleaning,
    deduplication, and storage in multiple formats.
    
    Attributes:
        sources: List of configured news sources
        batch_size: Number of articles to process per batch
        
    Example:
        >>> etl = NewsETL()
        >>> metrics = etl.run()
        >>> print(f"Processed {metrics.records_loaded} articles")
    """
    
    def __init__(
        self, 
        sources: Optional[List[Dict[str, str]]] = None,
        batch_size: int = 100,
        enable_caching: bool = True
    ) -> None:
        """
        Initialize the NewsETL pipeline.
        
        Args:
            sources: List of news source configurations
            batch_size: Number of articles to process in each batch
            enable_caching: Whether to enable response caching
            
        Raises:
            ValueError: If batch_size is less than 1
            ConfigurationError: If sources configuration is invalid
        """
        super().__init__(name="news_etl", batch_size=batch_size)
        self.sources = sources or self._get_default_sources()
        self.enable_caching = enable_caching
        
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
    
    def extract(self) -> List[Dict[str, Any]]:
        """
        Extract articles from all configured sources.
        
        Returns:
            List of raw article data dictionaries
            
        Raises:
            ExtractionError: If no sources are available or all sources fail
        """
        # Implementation
        pass
```

### Error Handling Patterns

```python
from src.exceptions.base import WatchtowerError, ExtractionError
from typing import Dict, Any, Optional
import logging

class RobustETL(BaseETL):
    """ETL with comprehensive error handling patterns"""
    
    def extract_with_fallback(self) -> List[Dict[str, Any]]:
        """Extract data with multiple fallback strategies"""
        
        # Primary extraction strategy
        try:
            return self._extract_primary_sources()
        except ExtractionError as e:
            self.logger.warning(f"Primary extraction failed: {e}")
            
            # Fallback to secondary sources
            try:
                return self._extract_secondary_sources()
            except ExtractionError as e:
                self.logger.error(f"Secondary extraction failed: {e}")
                
                # Last resort: cached data
                cached_data = self._get_cached_data()
                if cached_data:
                    self.logger.info("Using cached data as fallback")
                    return cached_data
                
                # If all else fails, raise with context
                raise ExtractionError(
                    "All extraction methods failed",
                    error_code="EXTRACTION_TOTAL_FAILURE",
                    context={
                        "primary_error": str(e),
                        "sources_attempted": len(self.sources),
                        "cache_available": False
                    }
                )
    
    def _safe_transform_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform single item with error isolation"""
        try:
            # Validate required fields
            required_fields = ['title', 'url', 'source']
            missing_fields = [field for field in required_fields if not item.get(field)]
            
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            # Transform the item
            transformed = self._transform_item(item)
            
            # Validate output
            if not self._validate_transformed_item(transformed):
                raise ValueError("Transformed item failed validation")
            
            return transformed
            
        except Exception as e:
            # Log the error with context but don't fail the entire batch
            self.logger.warning(
                f"Failed to transform item: {e}",
                extra={
                    "item_id": item.get("id", "unknown"),
                    "item_url": item.get("url", "unknown"),
                    "error_type": type(e).__name__
                }
            )
            return None
```

### Configuration-Driven Development

```python
from pydantic import BaseSettings, Field
from typing import List, Dict, Any, Optional

class ETLConfig(BaseSettings):
    """Configuration model for ETL pipelines"""
    
    # Data source configuration
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    max_sources: int = Field(default=10, ge=1, le=100)
    
    # Processing configuration
    batch_size: int = Field(default=100, ge=1, le=10000)
    max_workers: int = Field(default=4, ge=1, le=20)
    timeout_seconds: int = Field(default=300, ge=30, le=3600)
    
    # Retry configuration
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay: float = Field(default=1.0, ge=0.1, le=60.0)
    
    # Quality control
    min_quality_score: float = Field(default=0.5, ge=0.0, le=1.0)
    enable_validation: bool = Field(default=True)
    
    class Config:
        env_prefix = "ETL_"
        env_file = ".env"

class ConfigurableETL(BaseETL):
    """ETL that reads configuration from environment/files"""
    
    def __init__(self, config: Optional[ETLConfig] = None):
        self.config = config or ETLConfig()
        
        super().__init__(
            name="configurable_etl",
            batch_size=self.config.batch_size,
            max_retries=self.config.max_retries
        )
    
    def extract(self) -> List[Dict[str, Any]]:
        """Extract using configured sources"""
        sources = self.config.sources[:self.config.max_sources]
        
        all_data = []
        for source in sources:
            try:
                with timeout(self.config.timeout_seconds):
                    source_data = self._extract_from_source(source)
                    all_data.extend(source_data)
            except TimeoutError:
                self.logger.warning(f"Source {source} timed out")
        
        return all_data
```

---

## 📊 ETL Pipeline Best Practices

### Idempotent ETL Design

```python
import hashlib
from datetime import datetime
from typing import List, Dict, Any

class IdempotentETL(BaseETL):
    """ETL pipeline that produces consistent results on repeated runs"""
    
    def __init__(self):
        super().__init__(name="idempotent_etl")
        self.run_id = self._generate_run_id()
    
    def _generate_run_id(self) -> str:
        """Generate deterministic run ID based on timestamp and configuration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H")  # Hour-level granularity
        config_hash = hashlib.md5(str(self.config).encode()).hexdigest()[:8]
        return f"{timestamp}_{config_hash}"
    
    def extract(self) -> List[Dict[str, Any]]:
        """Extract with deduplication"""
        # Check if this run already exists
        checkpoint_file = self.get_data_path("checkpoints", f"{self.run_id}.json")
        if checkpoint_file.exists():
            self.logger.info(f"Run {self.run_id} already completed, skipping extraction")
            return self._load_from_checkpoint(checkpoint_file)
        
        # Extract fresh data
        data = self._extract_fresh_data()
        
        # Save checkpoint
        self._save_checkpoint(checkpoint_file, data)
        
        return data
    
    def load(self, data: List[Dict[str, Any]]) -> None:
        """Load with atomic operations"""
        # Write to temporary file first
        temp_file = self.get_data_path("temp", f"{self.run_id}_output.json")
        final_file = self.get_data_path("output", "latest.json")
        
        # Atomic write
        self.save_as_json(data, temp_file)
        
        # Atomic move (on same filesystem)
        temp_file.rename(final_file)
        
        self.logger.info(f"Successfully loaded {len(data)} records")
```

### Incremental ETL Processing

```python
from datetime import datetime, timedelta
from typing import Optional

class IncrementalETL(BaseETL):
    """ETL that processes only new/changed data"""
    
    def __init__(self):
        super().__init__(name="incremental_etl")
        self.last_processed_timestamp = self._get_last_processed_timestamp()
    
    def _get_last_processed_timestamp(self) -> Optional[datetime]:
        """Get timestamp of last successful run"""
        state_file = self.get_data_path("state", "last_run.json")
        
        if not state_file.exists():
            return None
        
        try:
            with open(state_file) as f:
                state = json.load(f)
                timestamp_str = state.get("last_processed_timestamp")
                if timestamp_str:
                    return datetime.fromisoformat(timestamp_str)
        except Exception as e:
            self.logger.warning(f"Failed to load last run state: {e}")
        
        return None
    
    def extract(self) -> List[Dict[str, Any]]:
        """Extract only new data since last run"""
        # Determine the cutoff time
        if self.last_processed_timestamp:
            cutoff_time = self.last_processed_timestamp
            self.logger.info(f"Extracting data since {cutoff_time}")
        else:
            # First run - get data from last 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.logger.info(f"First run - extracting data since {cutoff_time}")
        
        # Extract incremental data
        data = []
        for source in self.sources:
            source_data = self._extract_incremental_from_source(source, cutoff_time)
            data.extend(source_data)
        
        return data
    
    def load(self, data: List[Dict[str, Any]]) -> None:
        """Load data and update state"""
        # Load the data
        super().load(data)
        
        # Update last processed timestamp
        current_time = datetime.now()
        state = {
            "last_processed_timestamp": current_time.isoformat(),
            "records_processed": len(data),
            "run_date": current_time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        state_file = self.get_data_path("state", "last_run.json")
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        self.logger.info(f"Updated state file with timestamp {current_time}")
```

### Data Validation and Quality Assurance

```python
from pydantic import BaseModel, validator
from typing import List, Dict, Any, Optional
from datetime import datetime

class ArticleModel(BaseModel):
    """Pydantic model for article validation"""
    
    id: str
    title: str
    url: str
    content: Optional[str] = None
    published_date: Optional[datetime] = None
    source: str
    category: Optional[str] = None
    quality_score: float = 0.0
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    @validator('quality_score')
    def validate_quality_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Quality score must be between 0 and 1')
        return v
    
    @validator('title')
    def validate_title(cls, v):
        if len(v.strip()) < 5:
            raise ValueError('Title must be at least 5 characters')
        return v.strip()

class ValidatedETL(BaseETL):
    """ETL with comprehensive data validation"""
    
    def __init__(self):
        super().__init__(name="validated_etl")
        self.validation_stats = {
            "total_items": 0,
            "valid_items": 0,
            "validation_errors": {},
            "quality_distribution": {"high": 0, "medium": 0, "low": 0}
        }
    
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform with validation and quality scoring"""
        validated_data = []
        
        self.validation_stats["total_items"] = len(data)
        
        for item in data:
            try:
                # Add quality score
                item["quality_score"] = self._calculate_quality_score(item)
                
                # Validate using Pydantic model
                validated_item = ArticleModel(**item)
                validated_data.append(validated_item.dict())
                
                self.validation_stats["valid_items"] += 1
                
                # Track quality distribution
                score = validated_item.quality_score
                if score >= 0.8:
                    self.validation_stats["quality_distribution"]["high"] += 1
                elif score >= 0.5:
                    self.validation_stats["quality_distribution"]["medium"] += 1
                else:
                    self.validation_stats["quality_distribution"]["low"] += 1
                
            except Exception as e:
                error_type = type(e).__name__
                if error_type not in self.validation_stats["validation_errors"]:
                    self.validation_stats["validation_errors"][error_type] = 0
                self.validation_stats["validation_errors"][error_type] += 1
                
                self.logger.warning(f"Validation failed for item {item.get('id', 'unknown')}: {e}")
        
        # Log validation summary
        valid_pct = (self.validation_stats["valid_items"] / self.validation_stats["total_items"]) * 100
        self.logger.info(f"Validation complete: {valid_pct:.1f}% valid ({self.validation_stats['valid_items']}/{self.validation_stats['total_items']})")
        
        return validated_data
    
    def _calculate_quality_score(self, item: Dict[str, Any]) -> float:
        """Calculate quality score based on multiple factors"""
        score = 0.0
        
        # Content length scoring
        content_length = len(item.get("content", ""))
        if content_length > 1000:
            score += 0.3
        elif content_length > 500:
            score += 0.2
        elif content_length > 100:
            score += 0.1
        
        # Title quality
        title = item.get("title", "")
        if 20 <= len(title) <= 100:
            score += 0.2
        
        # URL quality
        url = item.get("url", "")
        if url and not any(spam_word in url.lower() for spam_word in ["click", "amazing", "shocking"]):
            score += 0.1
        
        # Source credibility (simplified)
        source = item.get("source", "").lower()
        trusted_sources = ["reuters", "bbc", "associated press", "npr"]
        if any(trusted in source for trusted in trusted_sources):
            score += 0.2
        
        # Recency bonus
        published = item.get("published_date")
        if published:
            try:
                pub_date = datetime.fromisoformat(published.replace('Z', '+00:00'))
                hours_old = (datetime.now() - pub_date.replace(tzinfo=None)).total_seconds() / 3600
                if hours_old <= 24:
                    score += 0.2
                elif hours_old <= 72:
                    score += 0.1
            except:
                pass
        
        return min(1.0, score)
```

---

## 👁️ Watcher System Best Practices

### Robust Change Detection

```python
import hashlib
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

class RobustWatcher(BaseWatcher):
    """Watcher with advanced change detection and noise filtering"""
    
    def __init__(self, name: str, url: str, check_interval: int = 300):
        super().__init__(name, url, check_interval)
        self.change_threshold = 0.1  # 10% change threshold
        self.stability_period = 60   # Require 60 seconds of stability
        self.recent_values = []      # Store recent values for trend analysis
    
    def extract_value(self, html_content: str) -> Any:
        """Extract value with error handling and normalization"""
        try:
            # Your extraction logic here
            raw_value = self._extract_raw_value(html_content)
            
            # Normalize the value
            normalized_value = self._normalize_value(raw_value)
            
            # Add metadata
            return {
                "value": normalized_value,
                "raw_value": raw_value,
                "extracted_at": datetime.now().isoformat(),
                "content_hash": hashlib.md5(html_content.encode()).hexdigest(),
                "content_length": len(html_content)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to extract value: {e}")
            return None
    
    def has_changed(self, old_value: Any, new_value: Any) -> bool:
        """Sophisticated change detection with noise filtering"""
        
        # Handle None values
        if old_value is None or new_value is None:
            return new_value is not None and old_value is None
        
        # Extract actual values
        old_val = old_value.get("value") if isinstance(old_value, dict) else old_value
        new_val = new_value.get("value") if isinstance(new_value, dict) else new_value
        
        # Check for significant change
        if self._is_significant_change(old_val, new_val):
            # Confirm the change is stable
            return self._confirm_stable_change(new_val)
        
        return False
    
    def _is_significant_change(self, old_val: Any, new_val: Any) -> bool:
        """Determine if change is significant enough to care about"""
        
        # For numeric values, use percentage threshold
        if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
            if old_val == 0:
                return new_val != 0
            
            change_percentage = abs((new_val - old_val) / old_val)
            return change_percentage >= self.change_threshold
        
        # For strings, use similarity threshold
        if isinstance(old_val, str) and isinstance(new_val, str):
            # Use Levenshtein distance or similar
            similarity = self._calculate_similarity(old_val, new_val)
            return similarity < (1 - self.change_threshold)
        
        # For other types, use direct comparison
        return old_val != new_val
    
    def _confirm_stable_change(self, new_value: Any) -> bool:
        """Confirm that the change is stable (not just noise)"""
        
        # Add to recent values
        self.recent_values.append({
            "value": new_value,
            "timestamp": datetime.now()
        })
        
        # Keep only recent values (last 5 minutes)
        cutoff_time = datetime.now() - timedelta(seconds=300)
        self.recent_values = [
            v for v in self.recent_values 
            if v["timestamp"] > cutoff_time
        ]
        
        # Need at least 2 consecutive readings of the same value
        if len(self.recent_values) < 2:
            return False
        
        # Check if recent values are consistent
        recent_vals = [v["value"] for v in self.recent_values[-3:]]  # Last 3 values
        return len(set(recent_vals)) == 1  # All the same
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings (simplified)"""
        # This is a simple implementation - consider using difflib or similar
        if not str1 and not str2:
            return 1.0
        if not str1 or not str2:
            return 0.0
        
        # Use longest common subsequence or similar algorithm
        # For simplicity, using character overlap
        set1, set2 = set(str1.lower()), set(str2.lower())
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
```

### Rate Limiting and Politeness

```python
import time
from typing import Dict, Any
from datetime import datetime, timedelta

class PolitWatcher(BaseWatcher):
    """Watcher that respects website resources and rate limits"""
    
    def __init__(self, name: str, url: str, check_interval: int = 300):
        super().__init__(name, url, check_interval)
        
        # Rate limiting settings
        self.min_request_interval = 10  # Minimum 10 seconds between requests
        self.last_request_time = None
        self.domain_request_history = {}
        
        # Politeness settings
        self.user_agent = f"Watchtower/{self.version} (automated monitoring; +https://github.com/josmerod/watchtower)"
        self.respect_robots_txt = True
        self.max_concurrent_requests = 1
    
    def fetch_page(self) -> str:
        """Fetch page with rate limiting and politeness"""
        
        # Rate limiting
        self._enforce_rate_limit()
        
        # Check robots.txt if required
        if self.respect_robots_txt and not self._robots_txt_allows():
            raise Exception(f"robots.txt disallows access to {self.url}")
        
        # Make request with polite headers
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
        }
        
        try:
            response = requests.get(
                self.url,
                headers=headers,
                timeout=(10, 30),  # (connect, read) timeout
                allow_redirects=True,
                max_redirects=5
            )
            
            response.raise_for_status()
            
            # Update request history
            self._update_request_history()
            
            return response.text
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch {self.url}: {e}")
            raise
    
    def _enforce_rate_limit(self):
        """Enforce minimum time between requests"""
        if self.last_request_time:
            time_since_last = time.time() - self.last_request_time
            if time_since_last < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last
                self.logger.debug(f"Rate limiting: sleeping {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _robots_txt_allows(self) -> bool:
        """Check if robots.txt allows access (simplified implementation)"""
        try:
            from urllib.parse import urljoin, urlparse
            
            domain = urlparse(self.url).netloc
            robots_url = f"https://{domain}/robots.txt"
            
            # Simple check - in production, use urllib.robotparser
            response = requests.get(robots_url, timeout=10)
            robots_content = response.text.lower()
            
            # Very basic check for User-agent: * and Disallow
            if "disallow: /" in robots_content:
                return False
            
            return True
            
        except Exception:
            # If we can't check robots.txt, assume it's allowed
            return True
    
    def _update_request_history(self):
        """Update request history for monitoring"""
        domain = urlparse(self.url).netloc
        
        if domain not in self.domain_request_history:
            self.domain_request_history[domain] = []
        
        self.domain_request_history[domain].append(datetime.now())
        
        # Keep only last 24 hours of history
        cutoff = datetime.now() - timedelta(hours=24)
        self.domain_request_history[domain] = [
            req_time for req_time in self.domain_request_history[domain]
            if req_time > cutoff
        ]
```

---

## ⚙️ Configuration Management

### Environment-Based Configuration

```python
from pydantic import BaseSettings, Field, validator
from typing import Dict, Any, List, Optional
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

class DatabaseConfig(BaseSettings):
    url: str = Field(default="sqlite:///data/watchtower.db")
    pool_size: int = Field(default=5, ge=1, le=50)
    max_overflow: int = Field(default=10, ge=0, le=50)
    echo: bool = Field(default=False)
    
    class Config:
        env_prefix = "DATABASE_"

class LoggingConfig(BaseSettings):
    level: str = Field(default="INFO")
    structured: bool = Field(default=False)
    file_enabled: bool = Field(default=True)
    file_max_size: int = Field(default=10485760)  # 10MB
    file_backup_count: int = Field(default=5)
    
    @validator('level')
    def validate_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Invalid log level. Must be one of {valid_levels}')
        return v.upper()
    
    class Config:
        env_prefix = "LOGGING_"

class WatchtowerSettings(BaseSettings):
    """Main configuration class with environment-specific settings"""
    
    # Environment configuration
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)
    testing: bool = Field(default=False)
    
    # Application settings
    app_name: str = Field(default="Watchtower")
    app_version: str = Field(default="1.0.0")
    secret_key: str = Field(default="dev-secret-key")
    
    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Feature flags
    enable_api: bool = Field(default=True)
    enable_dashboard: bool = Field(default=True)
    enable_monitoring: bool = Field(default=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        case_sensitive = False
    
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT
    
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION
    
    def is_testing(self) -> bool:
        return self.environment == Environment.TESTING
    
    @validator('secret_key')
    def validate_secret_key(cls, v, values):
        env = values.get('environment')
        if env == Environment.PRODUCTION and v == "dev-secret-key":
            raise ValueError('Must set a secure secret key for production')
        return v

# Environment-specific configurations
def get_development_settings() -> WatchtowerSettings:
    """Get development-specific settings"""
    return WatchtowerSettings(
        environment=Environment.DEVELOPMENT,
        debug=True,
        database__echo=True,
        logging__level="DEBUG",
        logging__structured=False
    )

def get_production_settings() -> WatchtowerSettings:
    """Get production-specific settings"""
    return WatchtowerSettings(
        environment=Environment.PRODUCTION,
        debug=False,
        database__echo=False,
        logging__level="INFO",
        logging__structured=True,
        logging__file_enabled=True
    )

# Configuration factory
def get_settings() -> WatchtowerSettings:
    """Get settings based on environment"""
    import os
    
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return get_production_settings()
    elif env == "testing":
        return WatchtowerSettings(environment=Environment.TESTING, testing=True)
    else:
        return get_development_settings()
```

### Configuration Validation

```python
def validate_configuration(settings: WatchtowerSettings) -> List[str]:
    """Validate configuration and return list of issues"""
    issues = []
    
    # Database validation
    if settings.database.url.startswith("sqlite://") and settings.is_production():
        issues.append("SQLite database not recommended for production")
    
    # Security validation
    if settings.is_production():
        if settings.debug:
            issues.append("Debug mode should be disabled in production")
        
        if len(settings.secret_key) < 32:
            issues.append("Secret key should be at least 32 characters in production")
    
    # Resource validation
    if settings.database.pool_size > 20 and not settings.is_production():
        issues.append("Large database pool size not needed for development")
    
    # Feature validation
    required_features = ["enable_api", "enable_dashboard"]
    disabled_features = [f for f in required_features if not getattr(settings, f)]
    if disabled_features:
        issues.append(f"Required features disabled: {disabled_features}")
    
    return issues

# Usage in application startup
def startup_configuration_check():
    """Check configuration on startup"""
    settings = get_settings()
    issues = validate_configuration(settings)
    
    if issues:
        logger = get_logger("config")
        for issue in issues:
            if settings.is_production():
                logger.error(f"Configuration issue: {issue}")
            else:
                logger.warning(f"Configuration issue: {issue}")
        
        if settings.is_production() and issues:
            raise ConfigurationError(f"Configuration validation failed: {issues}")
```

---

## 📝 Error Handling & Logging

### Structured Logging

```python
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar

# Context variables for request tracking
request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add context if available
        if request_id.get():
            log_data["request_id"] = request_id.get()
        
        if user_id.get():
            log_data["user_id"] = user_id.get()
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields from log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info'}:
                extra_fields[key] = value
        
        if extra_fields:
            log_data["extra"] = extra_fields
        
        return json.dumps(log_data, default=str)

class ContextualLogger:
    """Logger with automatic context injection"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log with automatic context injection"""
        extra = kwargs.get('extra', {})
        
        # Add performance metrics if available
        if hasattr(self, '_start_time'):
            extra['duration_ms'] = (time.time() - self._start_time) * 1000
        
        # Add memory usage if available
        try:
            import psutil
            process = psutil.Process()
            extra['memory_mb'] = process.memory_info().rss / 1024 / 1024
        except ImportError:
            pass
        
        kwargs['extra'] = extra
        self.logger.log(level, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log_with_context(logging.DEBUG, message, **kwargs)

# Performance logging decorator
def log_performance(logger: Optional[ContextualLogger] = None):
    """Decorator to log function performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            _logger = logger or ContextualLogger(func.__module__)
            
            start_time = time.time()
            _logger.info(f"Starting {func.__name__}", extra={
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_count": len(kwargs)
            })
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                _logger.info(f"Completed {func.__name__}", extra={
                    "function": func.__name__,
                    "duration_seconds": duration,
                    "success": True
                })
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                _logger.error(f"Failed {func.__name__}", extra={
                    "function": func.__name__,
                    "duration_seconds": duration,
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                })
                
                raise
        
        return wrapper
    return decorator
```

### Circuit Breaker Pattern

```python
import time
from enum import Enum
from typing import Callable, Any, Optional
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        
        self.logger = ContextualLogger(f"circuit_breaker.{id(self)}")
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator implementation"""
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.logger.info("Circuit breaker moving to HALF_OPEN state")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Last failure: {self.last_failure_time}"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self.last_failure_time:
            return True
        
        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.reset_timeout
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.logger.info("Circuit breaker reset to CLOSED state")
        
        self.failure_count = 0
        self.last_failure_time = None
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.error(
                f"Circuit breaker opened after {self.failure_count} failures"
            )

class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    pass

# Usage in ETL
class ResilientETL(BaseETL):
    """ETL with circuit breaker protection"""
    
    def __init__(self):
        super().__init__()
        
        # Circuit breakers for different components
        self.extraction_breaker = CircuitBreaker(
            failure_threshold=3,
            reset_timeout=300,  # 5 minutes
            expected_exception=requests.exceptions.RequestException
        )
        
        self.database_breaker = CircuitBreaker(
            failure_threshold=5,
            reset_timeout=60,  # 1 minute
            expected_exception=DatabaseError
        )
    
    @log_performance()
    def extract(self) -> List[Dict[str, Any]]:
        """Extract with circuit breaker protection"""
        try:
            return self.extraction_breaker.call(self._extract_data)
        except CircuitBreakerOpenError:
            self.logger.warning("Extraction circuit breaker open, using cached data")
            return self._get_cached_data()
    
    @log_performance()
    def load(self, data: List[Dict[str, Any]]) -> None:
        """Load with circuit breaker protection"""
        try:
            self.database_breaker.call(self._load_to_database, data)
        except CircuitBreakerOpenError:
            self.logger.warning("Database circuit breaker open, saving to file")
            self._load_to_file(data)
```

---

This is a comprehensive best practices guide that covers the essential areas for building robust Watchtower applications. The guide emphasizes:

1. **Code Quality**: Type hints, documentation, error handling
2. **Configuration Management**: Environment-based settings, validation
3. **ETL Best Practices**: Idempotent design, incremental processing, validation
4. **Watcher Reliability**: Change detection, rate limiting, politeness
5. **Error Handling**: Structured logging, circuit breakers, fault tolerance

Following these practices will help you build maintainable, scalable, and reliable data monitoring solutions with Watchtower. Each section provides practical examples that you can adapt to your specific use cases.