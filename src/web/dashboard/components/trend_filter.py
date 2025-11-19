"""Trend filter component for dashboard trend filtering.

This module provides reusable trend filtering functionality for
dashboard tabs with single-callback pattern compliance.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, html

# Import shared utilities
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.web.dashboard.utils import get_data_path
from src.analytics.models import TrendBadge, TrendFilter, TrendIndicator
from src.utils.logging import get_logger

logger = get_logger(__name__)


# --- Constants ---

TRENDS_DATA_PATH = get_data_path("analytics", "trends") / "latest_trends.json"


# --- Data Loading ---

def load_latest_trends() -> Dict[str, Any]:
    """Load the latest trend analysis data.

    Returns:
        Dictionary containing latest trend data
    """
    try:
        if not TRENDS_DATA_PATH.exists():
            logger.warning(f"Trends data file not found: {TRENDS_DATA_PATH}")
            return {}

        with open(TRENDS_DATA_PATH, encoding='utf-8') as f:
            trends_data = json.load(f)

        logger.info(f"Loaded {len(trends_data.get('trending_items', []))} trend indicators")
        return trends_data

    except Exception as e:
        logger.error(f"Error loading trends data: {e}")
        return {}


def get_trending_items_map(trends_data: Dict[str, Any]) -> Dict[str, TrendIndicator]:
    """Convert trend data to a mapping of item IDs to TrendIndicators.

    Args:
        trends_data: Loaded trend data dictionary

    Returns:
        Dictionary mapping item IDs to TrendIndicator objects
    """
    trending_map = {}

    try:
        for item_data in trends_data.get('trending_items', []):
            # Create TrendIndicator object
            trend_indicator = TrendIndicator(**item_data)

            # Store by different possible identifiers
            trending_map[trend_indicator.item_id] = trend_indicator

            # Also store by item name for easier lookup
            trending_map[trend_indicator.item_name.lower()] = trend_indicator

    except Exception as e:
        logger.error(f"Error processing trends data: {e}")

    return trending_map


# --- UI Components ---

def create_trend_filter_component(tab_name: str) -> html.Div:
    """Create trend filter component for a dashboard tab.

    Args:
        tab_name: Name of the tab this filter is for

    Returns:
        HTML Div containing trend filter controls
    """
    store_id = f"{tab_name}-trend-filter-store"
    button_id = f"{tab_name}-trend-filter-btn"

    return html.Div([
        # Hidden storage for trend filter state
        dcc.Store(
            id=store_id,
            data={
                "show_trending_only": False,
                "min_percentage_change": 0.0,
                "min_confidence": 0.0,
                "include_rising": True,
                "include_falling": True,
                "include_stable": True
            }
        ),

        # Trend filter button
        dbc.Button(
            id=button_id,
            children="🔥 Trending",
            color="outline-info",
            size="sm",
            className="mb-2 me-2",
            style={"display": "none"}  # Initially hidden until trends are loaded
        )
    ])


def create_trend_badge(item_data: Dict[str, Any], trending_items: Dict[str, TrendIndicator]) -> Optional[html.Span]:
    """Create trend badge for a content item if it's trending.

    Args:
        item_data: Dictionary representing a content item
        trending_items: Map of trending items

    Returns:
        HTML Span with trend badge, or None if not trending
    """
    if not trending_items:
        return None

    # Try different identifier strategies
    item_id = None
    possible_ids = [
        item_data.get('id'),
        item_data.get('title'),
        item_data.get('category'),
        item_data.get('source')
    ]

    # Find matching trend indicator
    trend_indicator = None
    for possible_id in possible_ids:
        if possible_id:
            trend_indicator = trending_items.get(str(possible_id)) or trending_items.get(str(possible_id).lower())
            if trend_indicator:
                break

    if not trend_indicator:
        return None

    # Create badge if item meets trending criteria
    if trend_indicator.trend_direction.value == "rising" and trend_indicator.confidence_score >= 0.5:
        badge = TrendBadge(emoji="🔥", is_trending=True, **{
            "display_text": "Trending",
            "percentage_change": trend_indicator.percentage_change,
            "color_scheme": "danger" if trend_indicator.percentage_change > 50 else "warning",
            "tooltip": f"Trending: {trend_indicator.percentage_change:+.1f}% | Confidence: {trend_indicator.confidence_score:.0%}"
        })

        return dbc.Badge(
            f"{badge.emoji} {badge.display_text}",
            color=badge.color_scheme,
            className="me-2",
            title=badge.tooltip,
            style={"fontSize": "0.8em"}
        )

    return None


def get_trend_filtered_content(
    content: List[Dict[str, Any]],
    trend_filter_data: Dict[str, Any],
    trending_items: Dict[str, TrendIndicator]
) -> List[Dict[str, Any]]:
    """Filter content based on trend criteria.

    Args:
        content: List of content items to filter
        trend_filter_data: Trend filter configuration
        trending_items: Map of trending items

    Returns:
        Filtered list of content items
    """
    if not trend_filter_data.get("show_trending_only", False):
        return content

    filtered_content = []
    min_confidence = trend_filter_data.get("min_confidence", 0.0)

    for item in content:
        # Check if item is trending
        item_id = None
        possible_ids = [
            item.get('id'),
            item.get('title'),
            item.get('category'),
            item.get('source')
        ]

        trend_indicator = None
        for possible_id in possible_ids:
            if possible_id:
                trend_indicator = trending_items.get(str(possible_id)) or trending_items.get(str(possible_id).lower())
                if trend_indicator:
                    break

        # Include item if it's trending and meets confidence threshold
        if (
            trend_indicator and
            trend_indicator.trend_direction.value == "rising" and
            trend_indicator.confidence_score >= min_confidence
        ):
            # Add trend information to item for display
            item_copy = item.copy()
            item_copy['trend_info'] = {
                'percentage_change': trend_indicator.percentage_change,
                'confidence_score': trend_indicator.confidence_score,
                'trend_direction': trend_indicator.trend_direction.value
            }
            filtered_content.append(item_copy)

    return filtered_content


def register_trend_filter_callbacks(app, tab_name: str, content_update_callback):
    """Register trend filter callbacks for a dashboard tab.

    Args:
        app: Dash application instance
        tab_name: Name of the tab
        content_update_callback: Callback function to update content
    """
    store_id = f"{tab_name}-trend-filter-store"
    button_id = f"{tab_name}-trend-filter-btn"

    @app.callback(
        Output(store_id, "data"),
        Output(button_id, "children"),
        Output(button_id, "color"),
        Output(button_id, "style"),
        Input(button_id, "n_clicks"),
        State(store_id, "data")
    )
    def toggle_trend_filter(n_clicks, current_filter):
        """Toggle trend filter state and button appearance."""
        if n_clicks is None:
            # Initial load - check if we have trend data
            trends_data = load_latest_trends()
            trending_count = len(trends_data.get('trending_items', []))

            if trending_count > 0:
                # Show button if we have trend data
                return current_filter, f"🔥 Trending ({trending_count})", "outline-info", {"display": "block", "fontSize": "0.85em"}
            else:
                # Hide button if no trend data
                return current_filter, "🔥 Trending", "outline-info", {"display": "none"}

        # Toggle filter state
        show_trending = current_filter.get("show_trending_only", False)
        new_filter = current_filter.copy()
        new_filter["show_trending_only"] = not show_trending

        # Update button text and color based on state
        if new_filter["show_trending_only"]:
            button_text = "🔥 All Content"
            button_color = "info"
            button_style = {"display": "block", "fontSize": "0.85em"}
        else:
            trends_data = load_latest_trends()
            trending_count = len(trends_data.get('trending_items', []))
            button_text = f"🔥 Trending ({trending_count})"
            button_color = "outline-info"
            button_style = {"display": "block", "fontSize": "0.85em"}

        return new_filter, button_text, button_color, button_style

    # Register the content update callback with trend filtering
    if content_update_callback:
        @app.callback(
            content_update_callback["outputs"],
            content_update_callback["inputs"],
            prevent_initial_call=True
        )
        def update_content_with_trends(*args):
            """Update content with trend filtering applied."""
            # Extract trend filter data from inputs (assuming it's included)
            # This will be implemented by the specific tab callback
            pass


# --- Convenience Functions ---

def initialize_trend_system():
    """Initialize the trend system and create necessary directories."""
    try:
        # Ensure trends data directory exists
        trends_dir = get_data_path("analytics", "trends")
        trends_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Trend system initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Error initializing trend system: {e}")
        return False


def run_trend_analysis_if_needed():
    """Run trend analysis if no recent data exists."""
    try:
        trends_file = get_data_path("analytics", "trends") / "latest_trends.json"

        # Check if we need to run analysis
        if not trends_file.exists():
            logger.info("No trend data found, running initial analysis")
            from utils.trend_scheduler import run_daily_trend_analysis
            result = run_daily_trend_analysis()
            return result
        else:
            # Check if data is recent (within last 24 hours)
            file_time = datetime.fromtimestamp(trends_file.stat().st_mtime)
            if datetime.utcnow() - file_time > timedelta(hours=24):
                logger.info("Trend data is stale, running fresh analysis")
                from utils.trend_scheduler import run_daily_trend_analysis
                result = run_daily_trend_analysis()
                return result

    except Exception as e:
        logger.error(f"Error checking trend analysis status: {e}")

    return {"success": True, "message": "Recent trend data available"}


# Auto-initialize on module import
initialize_trend_system()