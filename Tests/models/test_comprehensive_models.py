"""
Comprehensive unit tests for all Pydantic models.
Tests validation, serialization, and model behavior.
"""

import unittest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any

import pytest
from pydantic import ValidationError

from src.models.base import (
    TimestampedModel,
    StatusModel,
    TaggedModel,
    SourceModel,
    MetricsModel,
    ErrorModel,
)
from src.models.arxiv import (
    ArxivPaperModel,
    ArxivCategory,
    ArxivCategoryEnum,
    ArxivAuthor,
    ArxivLink,
    ArxivMetrics,
)
from src.models.technology import (
    TechnologyModel,
    TrendDirection,
    AdoptionLevel,
    TechnologyMetrics,
    TechnologyRating,
    TechnologyCategory,
)
from src.models.news import (
    NewsArticleModel,
    NewsSource,
    NewsCategory,
    NewsMetrics,
    NewsRating,
    NewsSentiment,
)
from src.models.games import (
    GameModel,
    GamePlatform,
    GameGenre,
    GameRating,
    GamePrice,
    GameMetrics,
    GameStatus,
)
from src.models.events import (
    EventModel,
    EventStatus,
    EventType,
    EventLocation,
    EventMetrics,
    EventRegistration,
    EventSpeaker,
)
from src.models.ai_platforms import (
    AIModelModel,
    AIModelType,
    AIModelStatus,
    AIModelMetrics,
    AIModelRating,
    AIModelProvider,
)
from src.models.security import (
    SecurityVulnerabilityModel,
    SeverityLevel,
    VulnerabilityStatus,
    SecurityMetrics,
    SecurityRating,
    SecurityImpact,
)
from src.models.ecommerce import (
    ProductModel,
    ProductCategory,
    ProductStatus,
    ProductPrice,
    ProductMetrics,
)


class TestBaseModels(unittest.TestCase):
    """Test base model classes."""

    def test_timestamped_model_auto_timestamps(self):
        """Test TimestampedModel automatically sets timestamps."""

        class TestModel(TimestampedModel):
            name: str

        model = TestModel(name="test")

        self.assertIsInstance(model.created_at, datetime)
        self.assertIsInstance(model.updated_at, datetime)
        self.assertEqual(model.created_at, model.updated_at)

    def test_status_model_default_active(self):
        """Test StatusModel defaults to active status."""

        class TestModel(StatusModel):
            name: str

        model = TestModel(name="test")
        self.assertEqual(model.status, "active")

    def test_tagged_model_empty_tags(self):
        """Test TaggedModel with empty tags list."""

        class TestModel(TaggedModel):
            name: str

        model = TestModel(name="test")
        self.assertEqual(model.tags, [])

    def test_source_model_validation(self):
        """Test SourceModel validation."""

        class TestModel(SourceModel):
            name: str

        model = TestModel(
            name="test", source_url="https://example.com", source_name="Example Source"
        )

        self.assertEqual(model.source_url, "https://example.com")
        self.assertEqual(model.source_name, "Example Source")

    def test_metrics_model_defaults(self):
        """Test MetricsModel with default values."""

        class TestModel(MetricsModel):
            name: str

        model = TestModel(name="test")

        self.assertEqual(model.view_count, 0)
        self.assertEqual(model.download_count, 0)
        self.assertEqual(model.like_count, 0)
        self.assertEqual(model.share_count, 0)
        self.assertEqual(model.comment_count, 0)


if __name__ == "__main__":
    unittest.main()
