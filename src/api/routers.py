"""API routers for Watchtower data."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.models import UnifiedItem
from src.services.data_loader import (
    KNOWLEDGE_SOURCES_CONFIG,
    NEWS_SOURCES_CONFIG,
    format_article_date,
    load_data_from_file,
)

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

def _load_and_process_items(config_dict: dict, source_filter: Optional[str] = None, limit: int = 10000) -> List[UnifiedItem]:
    """Helper to load items from config and convert to UnifiedItem."""
    items = []
    
    sources_to_load = config_dict.keys()
    if source_filter:
        if source_filter in config_dict:
            sources_to_load = [source_filter]
        else:
             # Try replacing - with _ or vice versa if direct match fails
            alt_key = source_filter.replace("-", "_")
            if alt_key in config_dict:
                sources_to_load = [alt_key]
            else:
                return [] # Or raise 404? For now return empty list

    for key in sources_to_load:
        source_config = config_dict[key]
        raw_data = load_data_from_file(source_config["path"])
        
        for item in raw_data:
            # Map raw item to UnifiedItem
            # Handle variations in field names
            title = item.get("title") or item.get("name") or item.get("full_name") or "No Title"
            url = item.get("url") or item.get("link") or item.get("html_url") or item.get("website")
            
            # Skip items without URL or Title? (Maybe keep them for completeness but model requires title)
            if not title:
                continue

            unified_item = UnifiedItem(
                title=title,
                url=url,
                source=source_config["name"],
                published_at=format_article_date(item),
                category=key # Use the config key as category for now
            )
            items.append(unified_item)
            
    # Sort items by some criteria? The dashboard sorts by date.
    # It might be expensive to sort everything every time.
    # Let's limit first? No, we must search/sort then limit.
    # For now, return unsorted or relying on file order, but dashboard sorts.
    # Let's simple return list
    
    return items[:limit] if limit > 0 else items


@router.get("/news", response_model=List[UnifiedItem])
async def get_news(
    source: Optional[str] = Query(None, description="Filter by source key (e.g. 'techcrunch')"),
    limit: int = Query(10000, ge=1, le=10000, description="Max items to return")
):
    """Get news items."""
    try:
        return _load_and_process_items(NEWS_SOURCES_CONFIG, source, limit)
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-garden", response_model=List[UnifiedItem])
async def get_knowledge(
    source: Optional[str] = Query(None, description="Filter by source key (e.g. 'opensource')"),
    limit: int = Query(10000, ge=1, le=10000, description="Max items to return")
):
    """Get knowledge garden items."""
    try:
        return _load_and_process_items(KNOWLEDGE_SOURCES_CONFIG, source, limit)
    except Exception as e:
        logger.error(f"Error fetching knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sources", response_model=dict)
async def get_sources():
    """Get available sources."""
    return {
        "news": {k: v["name"] for k, v in NEWS_SOURCES_CONFIG.items()},
        "knowledge_garden": {k: v["name"] for k, v in KNOWLEDGE_SOURCES_CONFIG.items()}
    }
