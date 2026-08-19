import json
import logging
import re
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import html

from src.web.dashboard.utils import get_data_path

logger = logging.getLogger(__name__)


def load_latest_trends() -> list[dict]:
    """Loads the latest trend analysis results."""
    try:
        trends_path = Path(get_data_path("analytics", "trends", "latest_trends.json"))
        if not trends_path.exists():
            return []

        with open(trends_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading trends: {e}")
        return []


def get_trending_items_map() -> dict[str, dict]:
    """Returns a map of item_id -> trend_data for quick lookup."""
    trends = load_latest_trends()
    return {t["item_id"]: t for t in trends if t.get("is_trending")}


def get_trend_terms(trending_map: dict[str, dict]) -> set[str]:
    """Return the set of trending terms present in the map's records."""
    return {t.get("term") for t in trending_map.values() if t.get("term")}


def render_trend_badge(trend_data: dict | None) -> html.Span | None:
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
        title=badge_info.get("tooltip", ""),
    )


def match_item_trend(item: dict, trending_map: dict[str, dict]) -> dict | None:
    """Return the trend record matching an item, or None.

    Match order: item id, item url, category/source, then trending term in
    the title (word boundary). The term fallback covers sources whose items
    carry no stable id (most RSS-shaped news files).
    """
    if not trending_map:
        return None

    item_id = item.get("id")
    if item_id and item_id in trending_map:
        return trending_map[item_id]

    item_url = item.get("url") or item.get("link")
    if item_url:
        for record in trending_map.values():
            if record.get("url") and record["url"] == item_url:
                return record

    source = item.get("source")
    if source and f"category:{source}" in trending_map:
        return trending_map[f"category:{source}"]

    title = str(item.get("title") or item.get("name") or "")
    if title:
        title_lower = title.lower()
        for record in trending_map.values():
            term = record.get("term")
            if term and re.search(rf"\b{re.escape(term)}\b", title_lower):
                return record
    return None


def is_item_trending(item: dict, trending_map: dict[str, dict]) -> bool:
    """Checks if an item is trending."""
    return match_item_trend(item, trending_map) is not None
