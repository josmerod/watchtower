import pytest
from unittest.mock import MagicMock, patch
import dash
from dash import html
import json

from src.web.dashboard.components import news_tab

def test_related_content_callback_registration():
    """Test that the related content callback is registered correctly."""
    app = dash.Dash(__name__)
    
    # Mock the layout to avoid errors during registration if it checks layout
    app.layout = html.Div()
    
    # Register callbacks
    news_tab.register_news_search_callbacks(app)
    
    # Check if callback is registered
    # Dash stores callbacks in app.callback_map
    # Keys are output IDs. We look for related-modal.is_open
    
    found = False
    callback_func = None
    
    for output_id, callback in app.callback_map.items():
        if "related-modal.is_open" in output_id and "related-content.children" in output_id:
            found = True
            callback_func = callback["callback"]
            break
            
    assert found, "Related content callback not found in registry"

