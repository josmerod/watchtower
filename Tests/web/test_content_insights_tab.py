import pytest
from unittest.mock import MagicMock, patch
from dash import html
import dash_bootstrap_components as dbc

# Mock dependencies before importing the module under test
with patch("src.web.dashboard.components.recommendations_tab.recommendations_manager") as mock_rec_mgr, \
     patch("src.web.dashboard.trend_utils.load_latest_trends") as mock_load_trends:
    
    from src.web.dashboard.components.intelligence_tab import (
        render_intelligence_tab,
        create_recommendations_section,
        create_trending_section
    )

class TestContentInsightsTab:
    
    def test_render_intelligence_tab_structure(self):
        """Test that the main render function returns the expected structure."""
        # Setup mocks
        with patch("src.web.dashboard.components.intelligence_tab.create_recommendations_section") as mock_create_recs, \
             patch("src.web.dashboard.components.intelligence_tab.create_trending_section") as mock_create_trends:
            
            mock_create_recs.return_value = html.Div("Recs")
            mock_create_trends.return_value = html.Div("Trends")
            
            layout = render_intelligence_tab()
            
            # Verify structure
            assert isinstance(layout, html.Div)
            # Check for title
            title_found = False
            for child in layout.children:
                if isinstance(child, html.H2) and child.children == "Content Insights Dashboard":
                    title_found = True
                    break
            assert title_found, "Dashboard title not found"
            
            # Verify sections are called
            mock_create_recs.assert_called_once()
            mock_create_trends.assert_called_once()

    @patch("src.web.dashboard.components.recommendations_tab.recommendations_manager")
    def test_create_recommendations_section_with_data(self, mock_rec_mgr):
        """Test recommendations section creation with data."""
        # Mock recommendation data
        mock_rec = MagicMock()
        mock_rec.title = "Test Rec"
        mock_rec.description = "Test Desc"
        mock_rec.score = 0.9
        
        mock_user_recs = MagicMock()
        mock_user_recs.recommendations = [mock_rec]
        mock_rec_mgr.get_user_recommendations.return_value = mock_user_recs
        
        # Import the function again or use the one from module if not patched globally in a way that affects this
        # Since we imported at top level, we need to patch where it's used or rely on the mock passed to the test if we patched the import source
        # But we imported `recommendations_manager` in the module.
        # Let's patch the object in the module.
        with patch("src.web.dashboard.components.intelligence_tab.recommendations_manager", mock_rec_mgr):
            section = create_recommendations_section()
            
            assert isinstance(section, html.Div)
            # Should contain "Top Picks"
            assert "Top Picks for You" in str(section.children)

    @patch("src.web.dashboard.trend_utils.load_latest_trends")
    def test_create_trending_section_with_data(self, mock_load_trends):
        """Test trending section creation with data."""
        mock_load_trends.return_value = [
            {"title": "Trend 1", "trend_score": 10.0},
            {"title": "Trend 2", "trend_score": 5.0}
        ]
        
        with patch("src.web.dashboard.components.intelligence_tab.load_latest_trends", mock_load_trends):
            section = create_trending_section()
            
            assert isinstance(section, html.Div)
            # Should contain "Trending Now"
            assert "Trending Now" in str(section.children)
