import pytest
from datetime import datetime, timedelta
from src.analytics.trends import TrendAnalyzer
from src.analytics.models import TrendAnalysis

class TestTrendAnalyzer:
    
    @pytest.fixture
    def analyzer(self):
        return TrendAnalyzer(window_days=7, trend_threshold=0.3)
        
    def test_analyze_trends_empty(self, analyzer):
        assert analyzer.analyze_trends([]) == []
        
    def test_analyze_trends_volume_increase(self, analyzer):
        # Create data for 2 periods
        # Previous period: 10 items
        # Current period: 20 items (100% increase)
        
        now = datetime.now()
        prev_date = now - timedelta(days=10)
        curr_date = now - timedelta(days=2)
        
        items = []
        # Previous items
        for i in range(10):
            items.append({
                "id": f"prev_{i}",
                "source": "test_source",
                "created_at": prev_date.isoformat()
            })
            
        # Current items
        for i in range(20):
            items.append({
                "id": f"curr_{i}",
                "source": "test_source",
                "created_at": curr_date.isoformat()
            })
            
        trends = analyzer.analyze_trends(items)
        
        assert len(trends) == 1
        trend = trends[0]
        assert trend.item_id == "category:test_source"
        assert trend.is_trending is True
        assert trend.trend_score == 1.0 # 100% increase
        assert trend.indicators["volume"].percentage_change == 100.0
        assert trend.badge.label == "🔥 Trending"
        
    def test_analyze_trends_no_trend(self, analyzer):
        # Stable volume
        now = datetime.now()
        prev_date = now - timedelta(days=10)
        curr_date = now - timedelta(days=2)
        
        items = []
        for i in range(10):
            items.append({"source": "test_source", "created_at": prev_date.isoformat()})
        for i in range(10):
            items.append({"source": "test_source", "created_at": curr_date.isoformat()})
            
        trends = analyzer.analyze_trends(items)
        assert len(trends) == 0
        
    def test_analyze_trends_new_breakout(self, analyzer):
        # No previous items, 5 current items
        now = datetime.now()
        curr_date = now - timedelta(days=2)
        
        items = []
        for i in range(5):
            items.append({"source": "new_source", "created_at": curr_date.isoformat()})
            
        trends = analyzer.analyze_trends(items)
        assert len(trends) == 1
        assert trends[0].trend_score == 1.0
