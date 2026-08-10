"""Tests for the trend analysis functionality.

Covers the live ``TrendAnalyzer.analyze_trends`` API and the
``TrendAnalysis`` / ``TrendIndicator`` / ``TrendBadge`` models in
``src.analytics.models``.
"""

from datetime import datetime, timedelta

import pytest

from src.analytics.models import TrendAnalysis, TrendBadge, TrendIndicator
from src.analytics.trends import TrendAnalyzer
from src.models.base import TimestampedModel


class SampleItem(TimestampedModel):
    """Minimal content item with a ``source`` attribute used as the category."""

    source: str = "unknown"


def _make_items(count: int, source: str, start: datetime, step: timedelta) -> list[SampleItem]:
    """Build ``count`` items from ``start`` spaced by ``step``."""
    return [SampleItem(created_at=start - step * i, source=source) for i in range(count)]


class TestTrendIndicatorModel:
    """Tests for the ``TrendIndicator`` model."""

    def test_defaults(self) -> None:
        """Confidence defaults to 1.0 and period_days to 7."""
        indicator = TrendIndicator(direction="up", percentage_change=42.0)
        assert indicator.confidence == 1.0
        assert indicator.period_days == 7

    def test_confidence_clamped(self) -> None:
        """Confidence is bounded to [0.0, 1.0]."""
        with pytest.raises(ValueError):
            TrendIndicator(direction="up", percentage_change=1.0, confidence=1.5)
        with pytest.raises(ValueError):
            TrendIndicator(direction="up", percentage_change=1.0, confidence=-0.1)


class TestTrendAnalyzer:
    """Tests for the ``TrendAnalyzer`` class."""

    @pytest.fixture()
    def analyzer(self) -> TrendAnalyzer:
        """Standard analyzer with a 7-day window and 0.3 threshold."""
        return TrendAnalyzer(window_days=7, trend_threshold=0.3)

    def test_init(self) -> None:
        """Constructor stores configuration."""
        analyzer = TrendAnalyzer(window_days=14, trend_threshold=0.5)
        assert analyzer.window_days == 14
        assert analyzer.trend_threshold == 0.5

    def test_empty_input_returns_empty(self, analyzer: TrendAnalyzer) -> None:
        """No items means no trends."""
        assert analyzer.analyze_trends([]) == []

    def test_detects_rising_category(self, analyzer: TrendAnalyzer) -> None:
        """A category with a recent surge is flagged as trending."""
        now = datetime.now()
        # 20 recent arxiv items vs only 2 in the previous window -> strong rise.
        recent = _make_items(20, "arxiv", now, timedelta(hours=1))
        previous = _make_items(2, "arxiv", now - timedelta(days=8), timedelta(hours=1))

        results = analyzer.analyze_trends(recent + previous)
        arxiv = [r for r in results if r.item_id == "category:arxiv"]
        assert len(arxiv) == 1
        assert arxiv[0].is_trending is True
        assert arxiv[0].trend_score >= analyzer.trend_threshold
        assert arxiv[0].badge is not None
        assert "Trending" in arxiv[0].badge.label

    def test_below_threshold_not_flagged(self, analyzer: TrendAnalyzer) -> None:
        """A category that grows but stays below threshold is not trending."""
        now = datetime.now()
        # 3 recent vs 2 previous -> 50% growth, above 0.3 -> trending.
        # Use a stricter analyzer to prove the boundary.
        strict = TrendAnalyzer(window_days=7, trend_threshold=0.9)
        recent = _make_items(3, "blog", now, timedelta(hours=1))
        previous = _make_items(2, "blog", now - timedelta(days=8), timedelta(hours=1))
        assert strict.analyze_trends(recent + previous) == []

    def test_new_breakout_category(self, analyzer: TrendAnalyzer) -> None:
        """A category with no prior items but >=5 recent items breaks out."""
        now = datetime.now()
        recent = _make_items(6, "emerging", now, timedelta(hours=1))
        results = analyzer.analyze_trends(recent)
        emerging = [r for r in results if r.item_id == "category:emerging"]
        assert len(emerging) == 1
        assert emerging[0].is_trending is True

    def test_low_volume_new_category_skipped(self, analyzer: TrendAnalyzer) -> None:
        """A brand-new category with fewer than 5 recent items is skipped."""
        now = datetime.now()
        recent = _make_items(3, "niche", now, timedelta(hours=1))
        results = analyzer.analyze_trends(recent)
        assert all("niche" not in r.item_id for r in results)

    def test_accepts_dict_items(self, analyzer: TrendAnalyzer) -> None:
        """The analyzer handles plain dicts (created_at as ISO string)."""
        now = datetime.now()
        items = [{"source": "feed", "created_at": (now - timedelta(hours=i)).isoformat()} for i in range(10)]
        results = analyzer.analyze_trends(items)
        assert any(r.item_id == "category:feed" for r in results)

    def test_indicator_metadata(self, analyzer: TrendAnalyzer) -> None:
        """A trending result carries a 'volume' indicator with metadata."""
        now = datetime.now()
        recent = _make_items(10, "news", now, timedelta(hours=1))
        results = analyzer.analyze_trends(recent)
        assert results, "expected at least one trend"
        volume = results[0].indicators.get("volume")
        assert volume is not None
        assert volume.direction == "up"
        assert volume.percentage_change > 0
        assert volume.period_days == analyzer.window_days


class TestTrendModels:
    """Tests for the ``TrendAnalysis`` and ``TrendBadge`` models."""

    def test_trend_analysis_defaults(self) -> None:
        """TrendAnalysis defaults: not trending, zero score, no badge."""
        analysis = TrendAnalysis(item_id="x")
        assert analysis.is_trending is False
        assert analysis.trend_score == 0.0
        assert analysis.indicators == {}
        assert analysis.badge is None

    def test_trend_badge_defaults(self) -> None:
        """TrendBadge color defaults to 'danger'."""
        badge = TrendBadge(label="🔥 Trending", tooltip="up")
        assert badge.color == "danger"
