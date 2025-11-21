import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dash import html
import dash_bootstrap_components as dbc

from src.web.dashboard.utils import get_data_path

logger = logging.getLogger(__name__)

def load_latest_trends() -> List[Dict]:
    """Loads the latest trend analysis results."""
    try:
        trends_path = Path(get_data_path("analytics", "trends", "latest_trends.json"))
        if not trends_path.exists():
            return []
            
        with open(trends_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading trends: {e}")
        return []

def get_trending_items_map() -> Dict[str, Dict]:
    """Returns a map of item_id -> trend_data for quick lookup."""
    trends = load_latest_trends()
    return {t["item_id"]: t for t in trends if t.get("is_trending")}

def render_trend_badge(trend_data: Optional[Dict]) -> Optional[html.Span]:
    """Renders a trend badge if data is present."""
    if not trend_data:
        return None
        
    badge_info = trend_data.get("badge")
    if not badge_info:
        return None
        
    return dbc.Badge(
        badge_info.get("label", "🔥 Trending"),
        color=badge_info.get("color", "danger"),
        className="ms-2",
        title=badge_info.get("tooltip", "")
    )

def is_item_trending(item: Dict, trending_map: Dict[str, Dict]) -> bool:
    """Checks if an item is trending."""
    # Check by specific ID if available
    item_id = item.get("id")
    if item_id and item_id in trending_map:
        return True
        
    # Check by category/source
    source = item.get("source")
    if source and f"category:{source}" in trending_map:
        return True
        
    return False
