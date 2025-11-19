"""Trend analysis service for detecting emerging content trends.

This module provides comprehensive trend analysis including:
- 7-day rolling window trend detection
- Item count increase analysis per category
- Keyword frequency change detection
- Confidence scoring and statistical analysis
"""

from __future__ import annotations

import json
import logging
import statistics
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.models.base import TimestampedModel
from src.web.dashboard.utils import get_data_path
from src.utils.logging import get_logger

from .models import (
    TrendAnalysis,
    TrendBadge,
    TrendDirection,
    TrendFilter,
    TrendIndicator,
    TrendIndicators,
)

logger = get_logger(__name__)


class TrendAnalyzer:
    """Service for analyzing content trends across multiple dimensions.

    Detects trending topics, categories, and keywords using
    statistical analysis and confidence scoring.
    """

    def __init__(
        self,
        window_days: int = 7,
        threshold_percentage: float = 30.0,
        min_confidence: float = 0.5,
        min_data_points: int = 3,
    ):
        """Initialize the TrendAnalyzer.

        Args:
            window_days: Number of days for rolling window analysis
            threshold_percentage: Minimum percentage change for trend detection
            min_confidence: Minimum confidence score for trend validation
            min_data_points: Minimum data points required for analysis
        """
        self.window_days = window_days
        self.threshold_percentage = threshold_percentage
        self.min_confidence = min_confidence
        self.min_data_points = min_data_points

        # Cache for historical data
        self._historical_cache: Dict[str, List[Dict[str, Any]]] = {}

    def calculate_trends(self, content: List[TimestampedModel]) -> TrendAnalysis:
        """Calculate comprehensive trend analysis for content.

        Args:
            content: List of content items with timestamps

        Returns:
            Complete trend analysis with indicators and statistics
        """
        logger.info(f"Starting trend analysis for {len(content)} items")

        if not content:
            logger.warning("No content provided for trend analysis")
            return self._create_empty_analysis()

        # Prepare data for analysis
        now = datetime.utcnow()
        window_start = now - timedelta(days=self.window_days)

        # Filter content by time window
        recent_content = self._filter_by_time_window(content, window_start)

        # Load historical data for comparison
        historical_data = self._load_historical_data(now)
        previous_content = self._filter_by_time_window(
            historical_data,
            window_start - timedelta(days=self.window_days),
            window_start
        )

        # Calculate different types of trends
        category_trends = self._analyze_category_trends(recent_content, previous_content)
        keyword_trends = self._analyze_keyword_trends(recent_content, previous_content)
        source_trends = self._analyze_source_trends(recent_content, previous_content)

        # Combine all trend indicators
        all_trends = category_trends + keyword_trends + source_trends

        # Apply confidence scoring and filtering
        filtered_trends = self._apply_confidence_filtering(all_trends)
        validated_trends = self._validate_trends(filtered_trends)

        # Create comprehensive analysis
        analysis = TrendAnalysis(
            total_items_analyzed=len(content),
            trending_items=validated_trends,
            rising_trends=len([t for t in validated_trends if t.trend_direction == TrendDirection.RISING]),
            falling_trends=len([t for t in validated_trends if t.trend_direction == TrendDirection.FALLING]),
            stable_trends=len([t for t in validated_trends if t.trend_direction == TrendDirection.STABLE]),
            average_confidence=self._calculate_average_confidence(validated_trends),
            significant_trends=len([t for t in validated_trends if t.confidence_score >= 0.7]),
            window_days=self.window_days,
            threshold_percentage=self.threshold_percentage,
            min_data_points=self.min_data_points,
        )

        logger.info(
            f"Trend analysis completed: {len(validated_trends)} trends detected "
            f"({analysis.rising_trends} rising, {analysis.falling_trends} falling)"
        )

        return analysis

    def create_trend_badge(self, trend: TrendIndicator, show_percentage: bool = True) -> TrendBadge:
        """Create a UI badge for displaying trend information.

        Args:
            trend: Trend indicator to create badge for
            show_percentage: Whether to show percentage change

        Returns:
            TrendBadge with UI display information
        """
        if trend.trend_direction == TrendDirection.RISING:
            emoji = "🔥"
            color_scheme = "danger" if trend.percentage_change > 50 else "warning"
            display_text = "Trending" if show_percentage else f"Trending {trend.percentage_change:+.0f}%"
        elif trend.trend_direction == TrendDirection.FALLING:
            emoji = "📉"
            color_scheme = "secondary"
            display_text = "Declining" if show_percentage else f"Declining {trend.percentage_change:+.0f}%"
        else:
            emoji = "📊"
            color_scheme = "info"
            display_text = "Stable"

        # Create tooltip
        tooltip_parts = []
        if trend.trend_direction == TrendDirection.RISING:
            tooltip_parts.append(f"Trending upward: {trend.percentage_change:+.1f}%")
        elif trend.trend_direction == TrendDirection.FALLING:
            tooltip_parts.append(f"Trending downward: {trend.percentage_change:+.1f}%")
        else:
            tooltip_parts.append("Trend: stable")

        tooltip_parts.append(f"Confidence: {trend.confidence_score:.1%}")
        tooltip_parts.append(f"Window: {trend.window_days} days")

        return TrendBadge(
            display_text=display_text,
            emoji=emoji,
            color_scheme=color_scheme,
            tooltip=" | ".join(tooltip_parts),
            percentage_change=trend.percentage_change,
            is_trending=(
                trend.trend_direction == TrendDirection.RISING and
                trend.confidence_score >= self.min_confidence and
                abs(trend.percentage_change) >= self.threshold_percentage
            ),
            confidence_display=f"{trend.confidence_score:.0%}" if trend.confidence_score < 1.0 else None,
            time_period=f"last {trend.window_days} days",
        )

    def filter_trends(self, trends: List[TrendIndicator], filter_config: TrendFilter) -> List[TrendIndicator]:
        """Filter trends based on configuration.

        Args:
            trends: List of trends to filter
            filter_config: Filter configuration

        Returns:
            Filtered list of trends
        """
        filtered_trends = []

        for trend in trends:
            # Apply trending-only filter
            if filter_config.show_trending_only and not (
                trend.trend_direction == TrendDirection.RISING and
                trend.confidence_score >= filter_config.min_confidence and
                abs(trend.percentage_change) >= filter_config.min_percentage_change
            ):
                continue

            # Apply percentage change filter
            if abs(trend.percentage_change) < filter_config.min_percentage_change:
                continue

            # Apply confidence filter
            if trend.confidence_score < filter_config.min_confidence:
                continue

            # Apply direction filters
            if (
                (trend.trend_direction == TrendDirection.RISING and not filter_config.include_rising) or
                (trend.trend_direction == TrendDirection.FALLING and not filter_config.include_falling) or
                (trend.trend_direction == TrendDirection.STABLE and not filter_config.include_stable)
            ):
                continue

            # Apply category filters
            if filter_config.allowed_categories and trend.category not in filter_config.allowed_categories:
                continue
            if trend.category in filter_config.blocked_categories:
                continue

            filtered_trends.append(trend)

        return filtered_trends

    def _filter_by_time_window(
        self,
        content: List[TimestampedModel],
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> List[TimestampedModel]:
        """Filter content items by time window.

        Args:
            content: Content items to filter
            start_date: Start of time window
            end_date: End of time window (default: now)

        Returns:
            Filtered content items within time window
        """
        if end_date is None:
            end_date = datetime.utcnow()

        return [
            item for item in content
            if start_date <= item.created_at.replace(tzinfo=None) < end_date
        ]

    def _analyze_category_trends(
        self,
        recent_content: List[TimestampedModel],
        previous_content: List[TimestampedModel],
    ) -> TrendIndicators:
        """Analyze trends by content categories.

        Args:
            recent_content: Recent content items
            previous_content: Previous period content items

        Returns:
            List of category trend indicators
        """
        recent_categories = self._extract_categories(recent_content)
        previous_categories = self._extract_categories(previous_content)

        trends = []
        all_categories = set(recent_categories.keys()) | set(previous_categories.keys())

        for category in all_categories:
            recent_count = recent_categories.get(category, 0)
            previous_count = previous_categories.get(category, 0)

            if previous_count == 0 and recent_count > 0:
                # New category - treat as rising trend
                trend_indicator = self._create_trend_indicator(
                    item_id=category,
                    item_type="category",
                    item_name=category,
                    previous_value=previous_count,
                    current_value=recent_count,
                    trend_direction=TrendDirection.RISING,
                    percentage_change=100.0,  # Infinite growth for new items
                    category=category,
                )
                trends.append(trend_indicator)
            elif previous_count > 0:
                percentage_change = ((recent_count - previous_count) / previous_count) * 100
                trend_direction = self._determine_trend_direction(percentage_change)
                confidence = self._calculate_confidence(recent_count, previous_count)

                trend_indicator = self._create_trend_indicator(
                    item_id=category,
                    item_type="category",
                    item_name=category,
                    previous_value=previous_count,
                    current_value=recent_count,
                    trend_direction=trend_direction,
                    percentage_change=percentage_change,
                    confidence_score=confidence,
                    category=category,
                )
                trends.append(trend_indicator)

        return trends

    def _analyze_keyword_trends(
        self,
        recent_content: List[TimestampedModel],
        previous_content: List[TimestampedModel],
    ) -> TrendIndicators:
        """Analyze trends by keyword frequency.

        Args:
            recent_content: Recent content items
            previous_content: Previous period content items

        Returns:
            List of keyword trend indicators
        """
        recent_keywords = self._extract_keywords(recent_content)
        previous_keywords = self._extract_keywords(previous_content)

        trends = []
        all_keywords = set(recent_keywords.keys()) | set(previous_keywords.keys())

        # Focus on significant keywords (appearing multiple times)
        significant_keywords = {
            k: v for k, v in all_keywords.items()
            if (recent_keywords.get(k, 0) + previous_keywords.get(k, 0)) >= 2
        }

        for keyword in significant_keywords:
            recent_count = recent_keywords.get(keyword, 0)
            previous_count = previous_keywords.get(keyword, 0)

            if previous_count > 0:
                percentage_change = ((recent_count - previous_count) / previous_count) * 100
                trend_direction = self._determine_trend_direction(percentage_change)
                confidence = self._calculate_confidence(recent_count, previous_count)

                trend_indicator = self._create_trend_indicator(
                    item_id=keyword,
                    item_type="keyword",
                    item_name=keyword,
                    previous_value=previous_count,
                    current_value=recent_count,
                    trend_direction=trend_direction,
                    percentage_change=percentage_change,
                    confidence_score=confidence,
                    metadata={"keyword_type": "extracted"},
                )
                trends.append(trend_indicator)

        return trends

    def _analyze_source_trends(
        self,
        recent_content: List[TimestampedModel],
        previous_content: List[TimestampedModel],
    ) -> TrendIndicators:
        """Analyze trends by data sources.

        Args:
            recent_content: Recent content items
            previous_content: Previous period content items

        Returns:
            List of source trend indicators
        """
        recent_sources = self._extract_sources(recent_content)
        previous_sources = self._extract_sources(previous_content)

        trends = []
        all_sources = set(recent_sources.keys()) | set(previous_sources.keys())

        for source in all_sources:
            recent_count = recent_sources.get(source, 0)
            previous_count = previous_sources.get(source, 0)

            if previous_count > 0:
                percentage_change = ((recent_count - previous_count) / previous_count) * 100
                trend_direction = self._determine_trend_direction(percentage_change)
                confidence = self._calculate_confidence(recent_count, previous_count)

                trend_indicator = self._create_trend_indicator(
                    item_id=source,
                    item_type="source",
                    item_name=source,
                    previous_value=previous_count,
                    current_value=recent_count,
                    trend_direction=trend_direction,
                    percentage_change=percentage_change,
                    confidence_score=confidence,
                    source=source,
                )
                trends.append(trend_indicator)

        return trends

    def _extract_categories(self, content: List[TimestampedModel]) -> Dict[str, int]:
        """Extract and count categories from content.

        Args:
            content: Content items to analyze

        Returns:
            Dictionary of category counts
        """
        categories = defaultdict(int)
        for item in content:
            # Try multiple fields that might contain category information
            for field in ['category', 'primary_category', 'type', 'source_type']:
                category = getattr(item, field, None)
                if category and isinstance(category, str):
                    categories[category.lower()] += 1
                    break
        return dict(categories)

    def _extract_keywords(self, content: List[TimestampedModel]) -> Dict[str, int]:
        """Extract and count keywords from content.

        Args:
            content: Content items to analyze

        Returns:
            Dictionary of keyword counts
        """
        keywords = defaultdict(int)

        for item in content:
            # Extract from titles
            title = getattr(item, 'title', '')
            if title and isinstance(title, str):
                title_words = [w.lower() for w in title.split() if len(w) > 3]
                for word in title_words:
                    keywords[word] += 1

            # Extract from descriptions/summaries
            for field in ['description', 'summary', 'content']:
                text = getattr(item, field, '')
                if text and isinstance(text, str):
                    words = [w.lower() for w in text.split() if len(w) > 4]
                    for word in words:
                        keywords[word] += 1

        return dict(keywords)

    def _extract_sources(self, content: List[TimestampedModel]) -> Dict[str, int]:
        """Extract and count sources from content.

        Args:
            content: Content items to analyze

        Returns:
            Dictionary of source counts
        """
        sources = defaultdict(int)
        for item in content:
            # Try multiple fields that might contain source information
            for field in ['source', 'source_name', 'provider', 'origin']:
                source = getattr(item, field, None)
                if source and isinstance(source, str):
                    sources[source.lower()] += 1
                    break
            else:
                # If no explicit source, try to extract from URL
                url = getattr(item, 'url', '')
                if url and isinstance(url, str):
                    domain = url.split('/')[2] if '://' in url and len(url.split('/')) > 2 else 'unknown'
                    sources[domain] += 1

        return dict(sources)

    def _determine_trend_direction(self, percentage_change: float) -> TrendDirection:
        """Determine trend direction from percentage change.

        Args:
            percentage_change: Percentage change value

        Returns:
            TrendDirection enum value
        """
        if percentage_change > self.threshold_percentage:
            return TrendDirection.RISING
        elif percentage_change < -self.threshold_percentage:
            return TrendDirection.FALLING
        else:
            return TrendDirection.STABLE

    def _calculate_confidence(self, recent_count: int, previous_count: int) -> float:
        """Calculate confidence score for trend detection.

        Args:
            recent_count: Recent period count
            previous_count: Previous period count

        Returns:
            Confidence score between 0 and 1
        """
        total_count = recent_count + previous_count

        # Base confidence from data volume
        if total_count >= 50:
            volume_confidence = 0.9
        elif total_count >= 20:
            volume_confidence = 0.7
        elif total_count >= 10:
            volume_confidence = 0.5
        else:
            volume_confidence = 0.3

        # Consistency confidence (both periods have data)
        if recent_count > 0 and previous_count > 0:
            consistency_confidence = 0.8
        elif recent_count > 0 or previous_count > 0:
            consistency_confidence = 0.6
        else:
            consistency_confidence = 0.2

        # Combined confidence
        combined_confidence = (volume_confidence + consistency_confidence) / 2

        return max(0.0, min(1.0, combined_confidence))

    def _create_trend_indicator(
        self,
        item_id: str,
        item_type: str,
        item_name: str,
        previous_value: float,
        current_value: float,
        trend_direction: TrendDirection,
        percentage_change: float,
        confidence_score: float = 0.5,
        category: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TrendIndicator:
        """Create a TrendIndicator with calculated values.

        Args:
            item_id: Unique identifier
            item_type: Type of item
            item_name: Display name
            previous_value: Previous period value
            current_value: Current period value
            trend_direction: Trend direction
            percentage_change: Percentage change
            confidence_score: Confidence score
            category: Optional category
            source: Optional source
            metadata: Additional metadata

        Returns:
            Configured TrendIndicator
        """
        return TrendIndicator(
            trend_direction=trend_direction,
            percentage_change=percentage_change,
            confidence_score=confidence_score,
            item_id=item_id,
            item_type=item_type,
            item_name=item_name,
            previous_value=previous_value,
            current_value=current_value,
            window_days=self.window_days,
            category=category,
            source=source,
            metadata=metadata or {},
        )

    def _apply_confidence_filtering(self, trends: List[TrendIndicator]) -> List[TrendIndicator]:
        """Apply confidence-based filtering to trends.

        Args:
            trends: List of trends to filter

        Returns:
            Filtered list of trends
        """
        return [
            trend for trend in trends
            if trend.confidence_score >= self.min_confidence
        ]

    def _validate_trends(self, trends: List[TrendIndicator]) -> List[TrendIndicator]:
        """Validate trends and ensure data quality.

        Args:
            trends: List of trends to validate

        Returns:
            Validated list of trends
        """
        validated_trends = []

        for trend in trends:
            # Check for valid percentage change
            if not (-100 <= trend.percentage_change <= 1000):
                logger.warning(f"Invalid percentage change for trend {trend.item_id}: {trend.percentage_change}")
                continue

            # Check for valid confidence score
            if not (0 <= trend.confidence_score <= 1):
                logger.warning(f"Invalid confidence score for trend {trend.item_id}: {trend.confidence_score}")
                continue

            validated_trends.append(trend)

        return validated_trends

    def _calculate_average_confidence(self, trends: List[TrendIndicator]) -> float:
        """Calculate average confidence score across trends.

        Args:
            trends: List of trends

        Returns:
            Average confidence score
        """
        if not trends:
            return 0.0

        return sum(trend.confidence_score for trend in trends) / len(trends)

    def _load_historical_data(self, current_date: datetime) -> List[TimestampedModel]:
        """Load historical data for trend comparison.

        Args:
            current_date: Current date for loading appropriate historical data

        Returns:
            List of historical content items
        """
        try:
            # Try to load from stored trend data files
            historical_data = []

            # Look for data files in the data directory
            data_path = get_data_path("analytics", "trends")
            if data_path.exists():
                # Load recent historical data files
                for days_back in range(1, 30):  # Look back up to 30 days
                    file_date = current_date - timedelta(days=days_back)
                    filename = f"{file_date.strftime('%Y-%m-%d')}_trends.json"
                    file_path = data_path / filename

                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            try:
                                trend_data = json.load(f)
                                # Extract content items from trend data
                                if 'content_snapshot' in trend_data:
                                    historical_data.extend(trend_data['content_snapshot'])
                            except json.JSONDecodeError as e:
                                logger.warning(f"Error loading trend file {filename}: {e}")

            # Convert to TimestampedModel objects (simplified)
            return historical_data

        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            return []

    def _create_empty_analysis(self) -> TrendAnalysis:
        """Create an empty trend analysis result.

        Returns:
            Empty TrendAnalysis with zero values
        """
        return TrendAnalysis(
            total_items_analyzed=0,
            trending_items=[],
            rising_trends=0,
            falling_trends=0,
            stable_trends=0,
            average_confidence=0.0,
            significant_trends=0,
            window_days=self.window_days,
            threshold_percentage=self.threshold_percentage,
            min_data_points=self.min_data_points,
        )