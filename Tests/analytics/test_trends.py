"""Test cases for trend analysis functionality."""

from datetime import datetime, timedelta

import pytest

from src.analytics.models import TrendDirection, TrendIndicator
from src.analytics.trends import TrendAnalyzer
from src.models.base import TimestampedModel


class TestContentModel(TimestampedModel):
    """Test model for content items with trend-related fields."""

    category: str = ""
    title: str = ""
    content: str = ""
    source: str = ""


class TestTrendAnalyzer:
    """Test cases for TrendAnalyzer class."""

    @pytest.fixture()
    def analyzer(self) -> TrendAnalyzer:
        """Create a TrendAnalyzer instance for testing."""
        return TrendAnalyzer(window_days=7, threshold_percentage=30.0, min_confidence=0.5)

    @pytest.fixture()
    def sample_content(self) -> list[TestContentModel]:
        """Create sample content for trend analysis."""
        now = datetime.utcnow()
        content = []

        # Create content with different patterns
        for i in range(100):
            # Spread items over the last 14 days
            days_ago = i * 0.14  # 14 days total
            timestamp = now - timedelta(days=days_ago)

            # Create model with trend-related fields
            if i < 40:  # 40% trending category (increasing frequency)
                item = TestContentModel(
                    id=f"item_{i}",
                    created_at=timestamp,
                    updated_at=timestamp,
                    category="machine-learning",
                    title=f"Machine Learning Paper {i}",
                    content=f"Deep learning neural network transformer model {i % 5}",
                    source="arxiv",
                )
            elif i < 70:  # 30% emerging category
                item = TestContentModel(
                    id=f"item_{i}",
                    created_at=timestamp,
                    updated_at=timestamp,
                    category="blockchain",
                    title=f"Blockchain Research {i}",
                    content=f"DeFi smart contract cryptocurrency {i % 3}",
                    source="conference",
                )
            else:  # 30% stable category
                item = TestContentModel(
                    id=f"item_{i}",
                    created_at=timestamp,
                    updated_at=timestamp,
                    category="classical-algorithms",
                    title=f"Algorithm Study {i}",
                    content=f"Sorting search optimization {i % 2}",
                    source="textbook",
                )

            content.append(item)

        return content

    def test_analyzer_initialization(self, analyzer: TrendAnalyzer) -> None:
        """Test TrendAnalyzer initialization."""
        assert analyzer.window_days == 7
        assert analyzer.threshold_percentage == 30.0
        assert analyzer.min_confidence == 0.5
        assert analyzer.min_data_points == 3

    def test_calculate_trends_basic(self, analyzer: TrendAnalyzer, sample_content: list[TestContentModel]) -> None:
        """Test basic trend calculation."""
        analysis = analyzer.calculate_trends(sample_content)

        assert analysis.total_items_analyzed == len(sample_content)
        assert analysis.window_days == analyzer.window_days
        assert analysis.threshold_percentage == analyzer.threshold_percentage
        assert isinstance(analysis.trending_items, list)

    def test_category_trend_detection(self, analyzer: TrendAnalyzer) -> None:
        """Test category-based trend detection."""
        now = datetime.utcnow()

        # Create content with clear category trends
        content = []

        # Recent period: high concentration of AI papers
        for i in range(20):
            item = TimestampedModel(
                id=f"recent_ai_{i}",
                created_at=now - timedelta(hours=i),
                category="artificial-intelligence",
                title=f"AI Paper {i}",
                content="machine learning deep learning",
                source="arxiv",
            )
            content.append(item)

        # Previous period: fewer AI papers
        for i in range(5):
            item = TimestampedModel(
                id=f"old_ai_{i}",
                created_at=now - timedelta(days=8, hours=i),
                category="artificial-intelligence",
                title=f"Old AI Paper {i}",
                content="machine learning",
                source="arxiv",
            )
            content.append(item)

        analysis = analyzer.calculate_trends(content)

        # Should detect rising trend for AI category
        ai_trends = [t for t in analysis.trending_items if t.item_name == "artificial-intelligence"]
        assert len(ai_trends) > 0
        assert ai_trends[0].trend_direction == TrendDirection.RISING

    def test_keyword_trend_detection(self, analyzer: TrendAnalyzer) -> None:
        """Test keyword-based trend detection."""
        now = datetime.utcnow()

        # Create content with trending keywords
        content = []

        # Recent content with "quantum computing" keyword
        for i in range(15):
            item = TimestampedModel(
                id=f"quantum_{i}",
                created_at=now - timedelta(hours=i),
                title=f"Quantum Computing Research {i}",
                content="quantum computing qubit entanglement",
                source="research",
            )
            content.append(item)

        # Older content without the keyword
        for i in range(3):
            item = TimestampedModel(
                id=f"classical_{i}",
                created_at=now - timedelta(days=8, hours=i),
                title=f"Classical Computing {i}",
                content="traditional algorithms",
                source="textbook",
            )
            content.append(item)

        analysis = analyzer.calculate_trends(content)

        # Should detect trending keywords
        keyword_trends = [t for t in analysis.trending_items if t.item_type == "keyword"]
        assert len(keyword_trends) > 0

    def test_source_trend_detection(self, analyzer: TrendAnalyzer) -> None:
        """Test source-based trend detection."""
        now = datetime.utcnow()

        content = []

        # Recent surge from "twitter" source
        for i in range(25):
            item = TimestampedModel(
                id=f"twitter_{i}",
                created_at=now - timedelta(hours=i),
                category="social-media",
                title=f"Tech News {i}",
                content="latest technology trends",
                source="twitter",
            )
            content.append(item)

        # Previous period: no twitter content
        for i in range(2):
            item = TimestampedModel(
                id=f"blog_{i}",
                created_at=now - timedelta(days=8, hours=i),
                category="tech",
                title=f"Blog Post {i}",
                content="technology discussion",
                source="blog",
            )
            content.append(item)

        analysis = analyzer.calculate_trends(content)

        # Should detect twitter as trending source
        source_trends = [t for t in analysis.trending_items if t.item_type == "source" and t.item_name == "twitter"]
        assert len(source_trends) > 0

    def test_confidence_scoring(self, analyzer: TrendAnalyzer) -> None:
        """Test confidence scoring for trends."""
        # Create content with high confidence trend (many data points)
        high_confidence_content = []
        now = datetime.utcnow()

        for i in range(50):  # Many data points = high confidence
            item = TimestampedModel(
                id=f"high_conf_{i}",
                created_at=now - timedelta(hours=i),
                category="high-confidence-topic",
                title=f"Research {i}",
                content="consistent topic content",
                source="journal",
            )
            high_confidence_content.append(item)

        analysis = analyzer.calculate_trends(high_confidence_content)

        # Check that confidence scores are reasonable
        for trend in analysis.trending_items:
            assert 0.0 <= trend.confidence_score <= 1.0
            if trend.confidence_score >= analyzer.min_confidence:
                assert trend.trend_direction in [
                    TrendDirection.RISING,
                    TrendDirection.FALLING,
                ]

    def test_trend_filtering(self, analyzer: TrendAnalyzer) -> None:
        """Test trend filtering functionality."""
        from src.analytics.models import TrendFilter

        # Create test trends
        trends = [
            TrendIndicator(
                item_id="test_1",
                item_type="category",
                item_name="rising-topic",
                previous_value=10.0,
                current_value=15.0,
                trend_direction=TrendDirection.RISING,
                percentage_change=50.0,
                confidence_score=0.8,
                window_days=7,
            ),
            TrendIndicator(
                item_id="test_2",
                item_type="category",
                item_name="low-confidence-topic",
                previous_value=5.0,
                current_value=7.0,
                trend_direction=TrendDirection.RISING,
                percentage_change=40.0,
                confidence_score=0.3,  # Below threshold
                window_days=7,
            ),
            TrendIndicator(
                item_id="test_3",
                item_type="source",
                item_name="falling-source",
                previous_value=20.0,
                current_value=15.0,
                trend_direction=TrendDirection.FALLING,
                percentage_change=-25.0,
                confidence_score=0.9,
                window_days=7,
            ),
        ]

        # Test filtering
        filter_config = TrendFilter(
            show_trending_only=True,
            min_confidence=0.5,
            include_rising=True,
            include_falling=False,
        )

        filtered_trends = analyzer.filter_trends(trends, filter_config)

        # Should only include high-confidence rising trends
        assert len(filtered_trends) == 1
        assert filtered_trends[0].item_name == "rising-topic"

    def test_empty_content_handling(self, analyzer: TrendAnalyzer) -> None:
        """Test handling of empty content."""
        analysis = analyzer.calculate_trends([])

        assert analysis.total_items_analyzed == 0
        assert len(analysis.trending_items) == 0
        assert analysis.rising_trends == 0
        assert analysis.falling_trends == 0
        assert analysis.stable_trends == 0
        assert analysis.average_confidence == 0.0

    def test_single_item_handling(self, analyzer: TrendAnalyzer) -> None:
        """Test handling of single content item."""
        content = [
            TestContentModel(
                id="single_item",
                created_at=datetime.utcnow(),
                category="test-category",
                title="Test Item",
                content="Test content",
                source="test-source",
            )
        ]

        analysis = analyzer.calculate_trends(content)

        assert analysis.total_items_analyzed == 1
        # Single item should not generate significant trends
        assert len(analysis.trending_items) == 0 or all(trend.confidence_score < analyzer.min_confidence for trend in analysis.trending_items)

    def test_trend_badge_creation(self, analyzer: TrendAnalyzer) -> None:
        """Test creation of trend badges."""
        trend = TrendIndicator(
            item_id="test_trend",
            item_type="category",
            item_name="test-category",
            previous_value=10.0,
            current_value=17.5,
            trend_direction=TrendDirection.RISING,
            percentage_change=75.0,
            confidence_score=0.85,
            window_days=7,
        )

        badge = analyzer.create_trend_badge(trend)

        assert badge.emoji == "🔥"
        assert badge.color_scheme == "danger"  # High percentage change
        assert "Trending" in badge.display_text
        assert badge.is_trending == True
        assert "+75.0%" in badge.tooltip


class TestTrendIntegration:
    """Integration tests for trend analysis system."""

    def test_end_to_end_trend_analysis(self) -> None:
        """Test complete trend analysis workflow."""
        analyzer = TrendAnalyzer(window_days=7, threshold_percentage=20.0, min_confidence=0.3)

        # Simulate realistic content data
        now = datetime.utcnow()
        content = []

        # Simulate trending topic: "transformer models"
        for i in range(30):
            days_ago = i * 0.1  # Recent surge
            item = TimestampedModel(
                id=f"transformer_{i}",
                created_at=now - timedelta(days=days_ago),
                category="nlp",
                title=f"Transformer Model Analysis {i}",
                content="attention mechanism transformer architecture neural networks",
                source="arxiv",
            )
            content.append(item)

        # Simulate declining topic: "cnn"
        for i in range(5):
            days_ago = 8 + i * 0.5  # Older, less frequent
            item = TimestampedModel(
                id=f"cnn_{i}",
                created_at=now - timedelta(days=days_ago),
                category="computer-vision",
                title=f"CNN Research {i}",
                content="convolutional neural network image classification",
                source="arxiv",
            )
            content.append(item)

        # Run analysis
        analysis = analyzer.calculate_trends(content)

        # Verify results
        assert analysis.total_items_analyzed == len(content)
        assert analysis.rising_trends > 0

        # Check for specific trends
        nlp_trends = [t for t in analysis.trending_items if t.item_name == "nlp"]
        transformer_keywords = [t for t in analysis.trending_items if "transformer" in t.item_name.lower()]

        # Should detect trends in NLP/transformer content
        assert len(nlp_trends) > 0 or len(transformer_keywords) > 0
