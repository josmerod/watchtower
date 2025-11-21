import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.utils.trend_scheduler import TrendScheduler

class TestTrendScheduler:
    
    @pytest.fixture
    def mock_settings(self):
        with patch("src.utils.trend_scheduler.get_settings") as mock:
            mock.return_value.data_dir = Path("/tmp/watchtower_test_data")
            yield mock
            
    @pytest.fixture
    def scheduler(self, mock_settings):
        return TrendScheduler()
        
    def test_run_daily_analysis(self, scheduler, tmp_path):
        # Mock analyzer and file system
        scheduler.trends_dir = tmp_path / "analytics" / "trends"
        scheduler.trends_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock _load_all_content to return some data
        with patch.object(scheduler, "_load_all_content") as mock_load:
            mock_load.return_value = [
                {"source": "test", "created_at": "2023-01-01T00:00:00"}
            ]
            
            # Mock analyzer to return a trend
            with patch.object(scheduler.analyzer, "analyze_trends") as mock_analyze:
                from src.analytics.models import TrendAnalysis
                mock_analyze.return_value = [
                    TrendAnalysis(item_id="test", is_trending=True)
                ]
                
                scheduler.run_daily_analysis()
                
                # Verify file creation
                files = list(scheduler.trends_dir.glob("*_trends.json"))
                assert len(files) >= 1
                assert (scheduler.trends_dir / "latest_trends.json").exists()
