"""Data models for news articles and feed sources."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from urllib.parse import urlparse

from pydantic import Field, HttpUrl, field_validator, model_validator

from src.models.base import TimestampedModel


class FeedType(str, Enum):
    """Feed type enumeration."""
    
    RSS = "rss"
    ATOM = "atom"
    JSON = "json"
    HTML = "html"
    API = "api"


class ArticleStatus(str, Enum):
    """Article status enumeration."""
    
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ContentLanguage(str, Enum):
    """Content language enumeration."""
    
    EN = "en"
    ES = "es"
    FR = "fr"
    DE = "de"
    IT = "it"
    PT = "pt"
    RU = "ru"
    ZH = "zh"
    JA = "ja"
    KO = "ko"


class FeedSourceModel(TimestampedModel):
    """Model for news feed sources."""
    
    name: str = Field(description="Feed source name")
    description: Optional[str] = Field(default=None, description="Feed description")
    url: HttpUrl = Field(description="Feed URL")
    feed_type: FeedType = Field(description="Type of feed")
    category: str = Field(description="Feed category")
    language: ContentLanguage = Field(default=ContentLanguage.EN, description="Content language")
    
    # Configuration
    active: bool = Field(default=True, description="Whether feed is active")
    fetch_interval: int = Field(
        default=3600, 
        ge=300, 
        le=86400, 
        description="Fetch interval in seconds"
    )
    max_articles: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum articles to fetch per run"
    )
    
    # Metadata
    last_fetched_at: Optional[datetime] = Field(
        default=None,
        description="Last successful fetch timestamp"
    )
    last_error: Optional[str] = Field(
        default=None,
        description="Last error message"
    )
    total_articles_fetched: int = Field(
        default=0,
        ge=0,
        description="Total articles fetched from this source"
    )
    
    # Source-specific settings    user_agent: Optional[str] = Field(default=None, description="Custom user agent")    headers: Optional[Dict[str, str]] = Field(default=None, description="Custom headers")    timeout: int = Field(default=30, ge=5, le=300, description="Request timeout")        @field_validator("url")    @classmethod    def validate_url(cls, v: HttpUrl) -> HttpUrl:
        """Validate that URL is accessible.
        
        Args:
            v: URL to validate.
            
        Returns:
            Validated URL.
        """
        parsed = urlparse(str(v))
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
        return v
    
    class Config:
        """Pydantic configuration."""
        
        schema_extra = {
            "examples": [
                {
                    "name": "Hacker News",
                    "description": "Tech news and discussion",
                    "url": "https://hnrss.org/frontpage",
                    "feed_type": "rss",
                    "category": "technology",
                    "language": "en",
                    "fetch_interval": 3600,
                    "max_articles": 50
                }
            ]
        }


class NewsArticleModel(TimestampedModel):
    """Model for news articles."""
    
    # Core content
    title: str = Field(description="Article title")
    url: HttpUrl = Field(description="Article URL")
    content: Optional[str] = Field(default=None, description="Article content/summary")
    excerpt: Optional[str] = Field(default=None, description="Article excerpt")
    
    # Publication info
    published_at: Optional[datetime] = Field(
        default=None,
        description="Original publication timestamp"
    )
    author: Optional[str] = Field(default=None, description="Article author")
    source_name: str = Field(description="Source name")
    source_id: Optional[str] = Field(default=None, description="Source feed ID")
    
    # Categorization
    category: Optional[str] = Field(default=None, description="Article category")
    tags: List[str] = Field(default=[], description="Article tags")
    language: ContentLanguage = Field(
        default=ContentLanguage.EN,
        description="Article language"
    )
    
    # Metadata
    status: ArticleStatus = Field(
        default=ArticleStatus.PUBLISHED,
        description="Article status"
    )
    word_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Word count"
    )
    reading_time_minutes: Optional[int] = Field(
        default=None,
        ge=0,
        description="Estimated reading time in minutes"
    )
    
    # Social/engagement metrics
    comments_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of comments"
    )
    likes_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of likes/upvotes"
    )
    shares_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of shares"
    )
    
    # Technical metadata
    original_id: Optional[str] = Field(
        default=None,
        description="Original ID from source"
    )
    checksum: Optional[str] = Field(
        default=None,
        description="Content checksum for deduplication"
    )
    scraped_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When article was scraped"
    )
    
    # Processing metadata
    processed: bool = Field(default=False, description="Whether article has been processed")
    processing_notes: Optional[str] = Field(
        default=None,
        description="Processing notes or errors"
    )
    
    # Additional data
    metadata: Optional[Dict[str, any]] = Field(
        default=None,
        description="Additional metadata from source"
    )
    
    @validator("title")
    def validate_title(cls, v: str) -> str:
        """Validate and clean title.
        
        Args:
            v: Title to validate.
            
        Returns:
            Cleaned title.
        """
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()
    
    @validator("content")
    def validate_content(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean content.
        
        Args:
            v: Content to validate.
            
        Returns:
            Cleaned content.
        """
        if v:
            return v.strip()
        return v
    
    @validator("word_count", pre=True, always=True)
    def calculate_word_count(cls, v: Optional[int], values: Dict) -> Optional[int]:
        """Calculate word count from content if not provided.
        
        Args:
            v: Current word count value.
            values: Other field values.
            
        Returns:
            Word count.
        """
        if v is not None:
            return v
            
        content = values.get("content")
        if content:
            return len(content.split())
        return None
    
    @validator("reading_time_minutes", pre=True, always=True)
    def calculate_reading_time(cls, v: Optional[int], values: Dict) -> Optional[int]:
        """Calculate reading time based on word count.
        
        Args:
            v: Current reading time value.
            values: Other field values.
            
        Returns:
            Estimated reading time in minutes.
        """
        if v is not None:
            return v
            
        word_count = values.get("word_count")
        if word_count:
            # Average reading speed: 200 words per minute
            return max(1, word_count // 200)
        return None
    
    def is_recent(self, hours: int = 24) -> bool:
        """Check if article was published recently.
        
        Args:
            hours: Number of hours to consider as recent.
            
        Returns:
            True if article is recent.
        """
        if not self.published_at:
            return False
            
        delta = datetime.utcnow() - self.published_at
        return delta.total_seconds() < (hours * 3600)
    
    def get_domain(self) -> str:
        """Get the domain from the article URL.
        
        Returns:
            Domain name.
        """
        parsed = urlparse(str(self.url))
        return parsed.netloc
    
    class Config:
        """Pydantic configuration."""
        
        schema_extra = {
            "examples": [
                {
                    "title": "New AI Model Achieves Breakthrough in Natural Language",
                    "url": "https://example.com/ai-breakthrough",
                    "content": "Researchers have developed a new AI model...",
                    "published_at": "2024-01-15T10:30:00Z",
                    "author": "Jane Doe",
                    "source_name": "Tech News",
                    "category": "artificial-intelligence",
                    "tags": ["ai", "machine-learning", "nlp"],
                    "language": "en",
                    "word_count": 500,
                    "comments_count": 42
                }
            ]
        } 