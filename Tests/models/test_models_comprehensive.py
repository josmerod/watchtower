"""
Comprehensive unit tests for all Pydantic models.
Tests validation, serialization, and model behavior.
"""

import unittest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.models.base import (
    TimestampedModel, StatusModel, TaggedModel, 
    SourceModel, MetricsModel, ErrorModel
)
from src.models.arxiv import (
    ArxivPaperModel, ArxivCategory, ArxivCategoryEnum, 
    ArxivAuthor, ArxivLink, ArxivMetrics
)
from src.models.technology import (
    TechnologyModel, TrendDirection, AdoptionLevel, 
    TechnologyMetrics, TechnologyRating, TechnologyCategory
)
from src.models.news import (
    NewsArticleModel, NewsSource, NewsCategory, 
    NewsMetrics, NewsRating, NewsSentiment
)
from src.models.games import (
    GameModel, GamePlatform, GameGenre, GameRating, 
    GamePrice, GameMetrics, GameStatus
)
from src.models.events import (
    EventModel, EventStatus, EventType, EventLocation, 
    EventMetrics, EventRegistration, EventSpeaker
)
from src.models.ai_platforms import (
    AIModelModel, AIModelType, AIModelStatus, 
    AIModelMetrics, AIModelRating, AIModelProvider
)
from src.models.security import (
    SecurityVulnerabilityModel, SeverityLevel, VulnerabilityStatus,
    SecurityMetrics, SecurityRating, SecurityImpact
)
from src.models.ecommerce import (
    ProductModel, ProductCategory, ProductStatus, 
    ProductPrice, ProductMetrics
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
        
        # Test timezone awareness
        self.assertIsNotNone(model.created_at.tzinfo)
        self.assertIsNotNone(model.updated_at.tzinfo)

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

    def test_tagged_model_custom_tags(self):
        """Test TaggedModel with custom tags."""
        class TestModel(TaggedModel):
            name: str
        
        model = TestModel(name="test", tags=["tag1", "tag2", "tag3"])
        self.assertEqual(model.tags, ["tag1", "tag2", "tag3"])

    def test_source_model_validation(self):
        """Test SourceModel validation."""
        class TestModel(SourceModel):
            name: str
        
        model = TestModel(
            name="test",
            source_url="https://example.com",
            source_name="Example Source"
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

    def test_error_model_validation(self):
        """Test ErrorModel validation."""
        model = ErrorModel(
            error_type="ValidationError",
            error_message="Test error message",
            error_code="ERR_001"
        )
        
        self.assertEqual(model.error_type, "ValidationError")
        self.assertEqual(model.error_message, "Test error message")
        self.assertEqual(model.error_code, "ERR_001")
        self.assertIsInstance(model.timestamp, datetime)


class TestArxivModels(unittest.TestCase):
    """Test ArXiv-related models."""

    def test_arxiv_author_model(self):
        """Test ArxivAuthor model."""
        author = ArxivAuthor(
            name="John Doe",
            affiliation="MIT",
            email="john.doe@mit.edu"
        )
        
        self.assertEqual(author.name, "John Doe")
        self.assertEqual(author.affiliation, "MIT")
        self.assertEqual(author.email, "john.doe@mit.edu")

    def test_arxiv_link_model(self):
        """Test ArxivLink model."""
        link = ArxivLink(
            href="https://arxiv.org/pdf/2301.00001.pdf",
            title="Download PDF",
            type="application/pdf"
        )
        
        self.assertEqual(link.href, "https://arxiv.org/pdf/2301.00001.pdf")
        self.assertEqual(link.title, "Download PDF")
        self.assertEqual(link.type, "application/pdf")

    def test_arxiv_category_enum(self):
        """Test ArxivCategoryEnum values."""
        self.assertEqual(ArxivCategoryEnum.CS_AI.value, "cs.AI")
        self.assertEqual(ArxivCategoryEnum.CS_LG.value, "cs.LG")
        self.assertEqual(ArxivCategoryEnum.STAT_ML.value, "stat.ML")

    def test_arxiv_paper_model_complete(self):
        """Test complete ArxivPaperModel."""
        authors = [
            ArxivAuthor(name="Alice Smith", affiliation="Stanford"),
            ArxivAuthor(name="Bob Johnson", affiliation="MIT")
        ]
        
        categories = [
            ArxivCategory(term="cs.AI", scheme="http://arxiv.org/schemas/atom"),
            ArxivCategory(term="cs.LG", scheme="http://arxiv.org/schemas/atom")
        ]
        
        links = [
            ArxivLink(href="https://arxiv.org/pdf/2301.00001.pdf", type="application/pdf")
        ]
        
        paper = ArxivPaperModel(
            arxiv_id="2301.00001",
            title="Test Paper",
            abstract="Test abstract",
            authors=authors,
            categories=categories,
            links=links,
            published_date=datetime.now(timezone.utc),
            source_url="https://arxiv.org/abs/2301.00001",
            source_name="arXiv"
        )
        
        self.assertEqual(paper.arxiv_id, "2301.00001")
        self.assertEqual(paper.title, "Test Paper")
        self.assertEqual(len(paper.authors), 2)
        self.assertEqual(len(paper.categories), 2)
        self.assertEqual(len(paper.links), 1)

    def test_arxiv_metrics_model(self):
        """Test ArxivMetrics model."""
        metrics = ArxivMetrics(
            citation_count=150,
            download_count=1000,
            bookmark_count=25
        )
        
        self.assertEqual(metrics.citation_count, 150)
        self.assertEqual(metrics.download_count, 1000)
        self.assertEqual(metrics.bookmark_count, 25)


class TestTechnologyModels(unittest.TestCase):
    """Test technology-related models."""

    def test_trend_direction_enum(self):
        """Test TrendDirection enum values."""
        self.assertEqual(TrendDirection.RISING.value, "rising")
        self.assertEqual(TrendDirection.FALLING.value, "falling")
        self.assertEqual(TrendDirection.STABLE.value, "stable")

    def test_adoption_level_enum(self):
        """Test AdoptionLevel enum values."""
        self.assertEqual(AdoptionLevel.EARLY.value, "early")
        self.assertEqual(AdoptionLevel.MAINSTREAM.value, "mainstream")
        self.assertEqual(AdoptionLevel.MATURE.value, "mature")

    def test_technology_model_complete(self):
        """Test complete TechnologyModel."""
        metrics = TechnologyMetrics(
            github_stars=10000,
            npm_downloads=50000,
            stack_overflow_questions=1500
        )
        
        rating = TechnologyRating(
            overall_score=8.5,
            performance_score=9.0,
            ease_of_use_score=7.5,
            documentation_score=8.0,
            community_score=9.5
        )
        
        tech = TechnologyModel(
            name="React",
            description="A JavaScript library for building user interfaces",
            category=TechnologyCategory.FRONTEND,
            trend_direction=TrendDirection.RISING,
            adoption_level=AdoptionLevel.MAINSTREAM,
            metrics=metrics,
            rating=rating,
            source_url="https://reactjs.org",
            source_name="React Official"
        )
        
        self.assertEqual(tech.name, "React")
        self.assertEqual(tech.category, TechnologyCategory.FRONTEND)
        self.assertEqual(tech.trend_direction, TrendDirection.RISING)
        self.assertEqual(tech.adoption_level, AdoptionLevel.MAINSTREAM)
        self.assertEqual(tech.metrics.github_stars, 10000)
        self.assertEqual(tech.rating.overall_score, 8.5)

    def test_technology_model_validation_error(self):
        """Test TechnologyModel validation errors."""
        with self.assertRaises(ValidationError):
            TechnologyModel(
                name="",  # Empty name should fail
                description="Test description"
            )


class TestNewsModels(unittest.TestCase):
    """Test news-related models."""

    def test_news_source_model(self):
        """Test NewsSource model."""
        source = NewsSource(
            name="TechCrunch",
            url="https://techcrunch.com",
            category=NewsCategory.TECHNOLOGY,
            credibility_score=8.5
        )
        
        self.assertEqual(source.name, "TechCrunch")
        self.assertEqual(source.url, "https://techcrunch.com")
        self.assertEqual(source.category, NewsCategory.TECHNOLOGY)
        self.assertEqual(source.credibility_score, 8.5)

    def test_news_sentiment_enum(self):
        """Test NewsSentiment enum values."""
        self.assertEqual(NewsSentiment.POSITIVE.value, "positive")
        self.assertEqual(NewsSentiment.NEGATIVE.value, "negative")
        self.assertEqual(NewsSentiment.NEUTRAL.value, "neutral")

    def test_news_article_model_complete(self):
        """Test complete NewsArticleModel."""
        source = NewsSource(
            name="TechCrunch",
            url="https://techcrunch.com",
            category=NewsCategory.TECHNOLOGY
        )
        
        metrics = NewsMetrics(
            read_time_minutes=5,
            social_shares=250,
            comments_count=42
        )
        
        article = NewsArticleModel(
            title="AI Revolution in Tech",
            content="Content about AI revolution...",
            author="Jane Doe",
            published_date=datetime.now(timezone.utc),
            source=source,
            category=NewsCategory.TECHNOLOGY,
            sentiment=NewsSentiment.POSITIVE,
            metrics=metrics,
            source_url="https://techcrunch.com/ai-revolution",
            source_name="TechCrunch"
        )
        
        self.assertEqual(article.title, "AI Revolution in Tech")
        self.assertEqual(article.author, "Jane Doe")
        self.assertEqual(article.category, NewsCategory.TECHNOLOGY)
        self.assertEqual(article.sentiment, NewsSentiment.POSITIVE)
        self.assertEqual(article.metrics.read_time_minutes, 5)


class TestGameModels(unittest.TestCase):
    """Test game-related models."""

    def test_game_platform_enum(self):
        """Test GamePlatform enum values."""
        self.assertEqual(GamePlatform.PC.value, "pc")
        self.assertEqual(GamePlatform.PLAYSTATION.value, "playstation")
        self.assertEqual(GamePlatform.XBOX.value, "xbox")
        self.assertEqual(GamePlatform.NINTENDO_SWITCH.value, "nintendo_switch")

    def test_game_price_model(self):
        """Test GamePrice model."""
        price = GamePrice(
            current_price=29.99,
            original_price=59.99,
            discount_percentage=50.0,
            currency="USD"
        )
        
        self.assertEqual(price.current_price, 29.99)
        self.assertEqual(price.original_price, 59.99)
        self.assertEqual(price.discount_percentage, 50.0)
        self.assertEqual(price.currency, "USD")

    def test_game_model_complete(self):
        """Test complete GameModel."""
        price = GamePrice(
            current_price=29.99,
            original_price=59.99,
            currency="USD"
        )
        
        metrics = GameMetrics(
            player_count=1000000,
            rating_count=5000,
            review_count=2500
        )
        
        game = GameModel(
            title="Cyberpunk 2077",
            description="An open-world action-adventure game",
            developer="CD Projekt Red",
            publisher="CD Projekt",
            platforms=[GamePlatform.PC, GamePlatform.PLAYSTATION],
            genres=[GameGenre.ACTION, GameGenre.RPG],
            release_date=datetime(2020, 12, 10, tzinfo=timezone.utc),
            price=price,
            rating=GameRating.MATURE,
            status=GameStatus.RELEASED,
            metrics=metrics,
            source_url="https://store.steampowered.com/app/1091500",
            source_name="Steam"
        )
        
        self.assertEqual(game.title, "Cyberpunk 2077")
        self.assertEqual(game.developer, "CD Projekt Red")
        self.assertEqual(len(game.platforms), 2)
        self.assertEqual(len(game.genres), 2)
        self.assertEqual(game.price.current_price, 29.99)
        self.assertEqual(game.rating, GameRating.MATURE)


class TestEventModels(unittest.TestCase):
    """Test event-related models."""

    def test_event_location_model(self):
        """Test EventLocation model."""
        location = EventLocation(
            name="Convention Center",
            address="123 Main St",
            city="San Francisco",
            country="USA",
            latitude=37.7749,
            longitude=-122.4194
        )
        
        self.assertEqual(location.name, "Convention Center")
        self.assertEqual(location.city, "San Francisco")
        self.assertEqual(location.latitude, 37.7749)
        self.assertEqual(location.longitude, -122.4194)

    def test_event_speaker_model(self):
        """Test EventSpeaker model."""
        speaker = EventSpeaker(
            name="John Doe",
            title="Senior Engineer",
            company="Tech Corp",
            bio="Experienced software engineer...",
            avatar_url="https://example.com/avatar.jpg"
        )
        
        self.assertEqual(speaker.name, "John Doe")
        self.assertEqual(speaker.title, "Senior Engineer")
        self.assertEqual(speaker.company, "Tech Corp")

    def test_event_model_complete(self):
        """Test complete EventModel."""
        location = EventLocation(
            name="Convention Center",
            city="San Francisco",
            country="USA"
        )
        
        speakers = [
            EventSpeaker(name="Alice Smith", title="CTO", company="AI Corp"),
            EventSpeaker(name="Bob Johnson", title="ML Engineer", company="Data Inc")
        ]
        
        event = EventModel(
            title="AI Conference 2024",
            description="Annual AI conference",
            start_date=datetime(2024, 6, 15, tzinfo=timezone.utc),
            end_date=datetime(2024, 6, 17, tzinfo=timezone.utc),
            event_type=EventType.CONFERENCE,
            status=EventStatus.SCHEDULED,
            location=location,
            speakers=speakers,
            max_attendees=1000,
            ticket_price=299.99,
            source_url="https://aiconf2024.com",
            source_name="AI Conference"
        )
        
        self.assertEqual(event.title, "AI Conference 2024")
        self.assertEqual(event.event_type, EventType.CONFERENCE)
        self.assertEqual(event.status, EventStatus.SCHEDULED)
        self.assertEqual(len(event.speakers), 2)
        self.assertEqual(event.max_attendees, 1000)
        self.assertEqual(event.ticket_price, 299.99)


class TestAIPlatformModels(unittest.TestCase):
    """Test AI platform-related models."""

    def test_ai_model_type_enum(self):
        """Test AIModelType enum values."""
        self.assertEqual(AIModelType.LANGUAGE_MODEL.value, "language_model")
        self.assertEqual(AIModelType.IMAGE_GENERATION.value, "image_generation")
        self.assertEqual(AIModelType.SPEECH_RECOGNITION.value, "speech_recognition")

    def test_ai_model_provider_enum(self):
        """Test AIModelProvider enum values."""
        self.assertEqual(AIModelProvider.OPENAI.value, "openai")
        self.assertEqual(AIModelProvider.ANTHROPIC.value, "anthropic")
        self.assertEqual(AIModelProvider.GOOGLE.value, "google")

    def test_ai_model_complete(self):
        """Test complete AIModelModel."""
        metrics = AIModelMetrics(
            parameter_count=175_000_000_000,
            context_length=4096,
            tokens_per_second=50,
            accuracy_score=0.95
        )
        
        rating = AIModelRating(
            overall_score=9.0,
            performance_score=8.5,
            cost_effectiveness_score=7.5,
            ease_of_use_score=9.5
        )
        
        model = AIModelModel(
            name="GPT-4",
            description="Advanced language model",
            model_type=AIModelType.LANGUAGE_MODEL,
            provider=AIModelProvider.OPENAI,
            version="4.0",
            status=AIModelStatus.ACTIVE,
            metrics=metrics,
            rating=rating,
            pricing_model="per_token",
            cost_per_1k_tokens=0.03,
            source_url="https://openai.com/gpt-4",
            source_name="OpenAI"
        )
        
        self.assertEqual(model.name, "GPT-4")
        self.assertEqual(model.provider, AIModelProvider.OPENAI)
        self.assertEqual(model.model_type, AIModelType.LANGUAGE_MODEL)
        self.assertEqual(model.metrics.parameter_count, 175_000_000_000)
        self.assertEqual(model.rating.overall_score, 9.0)


class TestSecurityModels(unittest.TestCase):
    """Test security-related models."""

    def test_severity_level_enum(self):
        """Test SeverityLevel enum values."""
        self.assertEqual(SeverityLevel.CRITICAL.value, "critical")
        self.assertEqual(SeverityLevel.HIGH.value, "high")
        self.assertEqual(SeverityLevel.MEDIUM.value, "medium")
        self.assertEqual(SeverityLevel.LOW.value, "low")

    def test_security_vulnerability_model(self):
        """Test SecurityVulnerabilityModel."""
        vulnerability = SecurityVulnerabilityModel(
            cve_id="CVE-2024-0001",
            title="Buffer Overflow in Example App",
            description="A buffer overflow vulnerability...",
            severity=SeverityLevel.HIGH,
            cvss_score=7.5,
            affected_software="Example App",
            affected_versions=["1.0.0", "1.0.1"],
            status=VulnerabilityStatus.OPEN,
            published_date=datetime.now(timezone.utc),
            source_url="https://nvd.nist.gov/vuln/detail/CVE-2024-0001",
            source_name="NIST NVD"
        )
        
        self.assertEqual(vulnerability.cve_id, "CVE-2024-0001")
        self.assertEqual(vulnerability.severity, SeverityLevel.HIGH)
        self.assertEqual(vulnerability.cvss_score, 7.5)
        self.assertEqual(len(vulnerability.affected_versions), 2)


class TestEcommerceModels(unittest.TestCase):
    """Test ecommerce-related models."""

    def test_product_price_model(self):
        """Test ProductPrice model."""
        price = ProductPrice(
            current_price=99.99,
            original_price=149.99,
            currency="USD",
            discount_percentage=33.33
        )
        
        self.assertEqual(price.current_price, 99.99)
        self.assertEqual(price.original_price, 149.99)
        self.assertEqual(price.currency, "USD")
        self.assertEqual(price.discount_percentage, 33.33)

    def test_product_model_complete(self):
        """Test complete ProductModel."""
        price = ProductPrice(
            current_price=99.99,
            original_price=149.99,
            currency="USD"
        )
        
        metrics = ProductMetrics(
            sales_count=1500,
            rating_average=4.5,
            review_count=250
        )
        
        product = ProductModel(
            name="Wireless Headphones",
            description="High-quality wireless headphones",
            brand="AudioTech",
            sku="AT-WH-001",
            category=ProductCategory.ELECTRONICS,
            price=price,
            status=ProductStatus.AVAILABLE,
            metrics=metrics,
            source_url="https://shop.example.com/headphones",
            source_name="Example Shop"
        )
        
        self.assertEqual(product.name, "Wireless Headphones")
        self.assertEqual(product.brand, "AudioTech")
        self.assertEqual(product.category, ProductCategory.ELECTRONICS)
        self.assertEqual(product.price.current_price, 99.99)
        self.assertEqual(product.metrics.rating_average, 4.5)


class TestModelSerialization(unittest.TestCase):
    """Test model serialization and deserialization."""

    def test_model_to_dict(self):
        """Test model serialization to dictionary."""
        paper = ArxivPaperModel(
            arxiv_id="2301.00001",
            title="Test Paper",
            abstract="Test abstract",
            authors=[ArxivAuthor(name="Test Author")],
            published_date=datetime.now(timezone.utc),
            source_url="https://example.com",
            source_name="Test Source"
        )
        
        paper_dict = paper.model_dump()
        
        self.assertIsInstance(paper_dict, dict)
        self.assertEqual(paper_dict["arxiv_id"], "2301.00001")
        self.assertEqual(paper_dict["title"], "Test Paper")
        self.assertIn("authors", paper_dict)
        self.assertIn("published_date", paper_dict)

    def test_model_to_json(self):
        """Test model serialization to JSON."""
        tech = TechnologyModel(
            name="Python",
            description="Programming language",
            category=TechnologyCategory.PROGRAMMING_LANGUAGE,
            source_url="https://python.org",
            source_name="Python Official"
        )
        
        tech_json = tech.model_dump_json()
        
        self.assertIsInstance(tech_json, str)
        self.assertIn("Python", tech_json)
        self.assertIn("programming_language", tech_json)

    def test_model_from_dict(self):
        """Test model deserialization from dictionary."""
        game_data = {
            "title": "Test Game",
            "description": "A test game",
            "developer": "Test Studio",
            "platforms": ["pc", "playstation"],
            "genres": ["action"],
            "release_date": "2024-01-01T00:00:00Z",
            "rating": "teen",
            "status": "released",
            "source_url": "https://example.com",
            "source_name": "Test Source"
        }
        
        game = GameModel(**game_data)
        
        self.assertEqual(game.title, "Test Game")
        self.assertEqual(game.developer, "Test Studio")
        self.assertEqual(len(game.platforms), 2)
        self.assertEqual(len(game.genres), 1)


if __name__ == '__main__':
    unittest.main() 