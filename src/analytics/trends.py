from collections import Counter
from datetime import datetime, timedelta

from src.analytics.models import TrendAnalysis, TrendBadge, TrendIndicator


class TrendAnalyzer:
    """Analyzes content to identify trends."""

    def __init__(self, window_days: int = 7, trend_threshold: float = 0.3):
        self.window_days = window_days
        self.trend_threshold = trend_threshold

    def analyze_trends(self, items: list[dict]) -> list[TrendAnalysis]:
        """Analyzes a list of items to identify trends.

        Args:
            items: List of content items (dictionaries or objects)

        Returns:
            List of TrendAnalysis objects for trending items
        """
        # Group items by category/topic if possible, but for now we analyze individual items
        # or broad categories.
        # For this story (8.2), we focus on identifying trending *topics* or *categories*
        # based on item count increase.

        # 1. Filter items within the analysis window (last 2 * window_days)
        # We need 2 windows to compare: current vs previous
        cutoff_date = datetime.now() - timedelta(days=self.window_days * 2)
        recent_items = [item for item in items if self._get_date(item) >= cutoff_date]

        # 2. Split into current and previous periods
        mid_date = datetime.now() - timedelta(days=self.window_days)
        current_period_items = [item for item in recent_items if self._get_date(item) >= mid_date]
        previous_period_items = [item for item in recent_items if self._get_date(item) < mid_date]

        # 3. Analyze by Category
        current_counts = Counter(self._get_category(item) for item in current_period_items)
        previous_counts = Counter(self._get_category(item) for item in previous_period_items)

        trend_analyses = []

        # Analyze categories
        all_categories = set(current_counts.keys()) | set(previous_counts.keys())

        for category in all_categories:
            curr = current_counts.get(category, 0)
            prev = previous_counts.get(category, 0)

            # Avoid division by zero and ignore low volume
            if prev == 0:
                if curr >= 5:  # New breakout trend
                    pct_change = 1.0  # 100% (arbitrary cap for new)
                else:
                    continue
            else:
                pct_change = (curr - prev) / prev

            if pct_change >= self.trend_threshold:
                analysis = TrendAnalysis(
                    item_id=f"category:{category}",
                    is_trending=True,
                    trend_score=pct_change,
                    indicators={
                        "volume": TrendIndicator(
                            direction="up",
                            percentage_change=pct_change * 100,
                            period_days=self.window_days,
                        )
                    },
                    badge=TrendBadge(
                        label="🔥 Trending",
                        tooltip=f"Volume up {int(pct_change*100)}% this week",
                    ),
                )
                trend_analyses.append(analysis)

        return trend_analyses

    def _get_date(self, item) -> datetime:
        """Extracts date from item."""
        # Handle both dict and object access
        if isinstance(item, dict):
            val = item.get("created_at") or item.get("published_date") or item.get("date")
        else:
            val = getattr(item, "created_at", None) or getattr(item, "published_date", None)

        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            except ValueError:
                return datetime.now()  # Fallback
        elif isinstance(val, datetime):
            return val
        return datetime.now()

    def _get_category(self, item) -> str:
        """Extracts category from item."""
        if isinstance(item, dict):
            return item.get("source", "unknown")
        return getattr(item, "source", "unknown")
