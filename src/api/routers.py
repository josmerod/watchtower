"""API routers for Watchtower data."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.models import UnifiedItem
from src.services.data_loader import (
    KNOWLEDGE_SOURCES_CONFIG,
    NEWS_SOURCES_CONFIG,
    ECOMMERCE_SOURCES_CONFIG,
    ENTERTAINMENT_SOURCES_CONFIG,
    INTEL_SOURCES_CONFIG,
    TRAVEL_SOURCES_CONFIG,
    RESEARCH_SOURCES_CONFIG,
    MUSEUMS_CONFIG,
    GAMES_SOURCES_CONFIG,
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

@router.get("/ecommerce", response_model=List[UnifiedItem])
async def get_ecommerce(
    source: Optional[str] = Query(None, description="Filter by source key"),
    limit: int = Query(10000, ge=1, le=10000, description="Max items to return")
):
    """Get e-commerce items."""
    try:
        return _load_and_process_items(ECOMMERCE_SOURCES_CONFIG, source, limit)
    except Exception as e:
        logger.error(f"Error fetching ecommerce: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/entertainment", response_model=List[UnifiedItem])
async def get_entertainment(
    source: Optional[str] = Query(None, description="Filter by source key"),
    limit: int = Query(10000, ge=1, le=10000, description="Max items to return")
):
    """Get entertainment items."""
    try:
        return _load_and_process_items(ENTERTAINMENT_SOURCES_CONFIG, source, limit)
    except Exception as e:
        logger.error(f"Error fetching entertainment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/intelligence", response_model=List[UnifiedItem])
async def get_intelligence(
    source: Optional[str] = Query(None, description="Filter by source key"),
    limit: int = Query(10000, ge=1, le=10000, description="Max items to return")
):
    """Get intelligence items."""
    try:
        return _load_and_process_items(INTEL_SOURCES_CONFIG, source, limit)
    except Exception as e:
        logger.error(f"Error fetching intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/travel", response_model=List[UnifiedItem])
async def get_travel(
    source: Optional[str] = Query(None, description="Filter by source key"),
    limit: int = Query(10000, ge=1, le=10000, description="Max items to return")
):
    """Get travel items."""
    try:
        return _load_and_process_items(TRAVEL_SOURCES_CONFIG, source, limit)
    except Exception as e:
        logger.error(f"Error fetching travel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/research", response_model=List[UnifiedItem])
async def get_research(
    source: Optional[str] = Query(None, description="Filter by source key"),
    limit: int = Query(10000, ge=1, le=10000, description="Max items to return")
):
    """Get research items."""
    try:
        return _load_and_process_items(RESEARCH_SOURCES_CONFIG, source, limit)
    except Exception as e:
        logger.error(f"Error fetching research: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/museums", response_model=List[UnifiedItem])
async def get_museums(
    source: Optional[str] = Query(None, description="Filter by source key"),
    limit: int = Query(10000, ge=1, le=10000, description="Max items to return")
):
    """Get museums items."""
    try:
        return _load_and_process_items(MUSEUMS_CONFIG, source, limit)
    except Exception as e:
        logger.error(f"Error fetching museums: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/games", response_model=List[UnifiedItem])
async def get_games(
    source: Optional[str] = Query(None, description="Filter by source key"),
    limit: int = Query(10000, ge=1, le=10000, description="Max items to return")
):
    """Get games items."""
    try:
        return _load_and_process_items(GAMES_SOURCES_CONFIG, source, limit)
    except Exception as e:
        logger.error(f"Error fetching games: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sources", response_model=dict)
async def get_sources():
    """Get available sources."""
    return {
        "news": {k: v["name"] for k, v in NEWS_SOURCES_CONFIG.items()},
        "knowledge_garden": {k: v["name"] for k, v in KNOWLEDGE_SOURCES_CONFIG.items()},
        "ecommerce": {k: v["name"] for k, v in ECOMMERCE_SOURCES_CONFIG.items()},
        "entertainment": {k: v["name"] for k, v in ENTERTAINMENT_SOURCES_CONFIG.items()},
        "intelligence": {k: v["name"] for k, v in INTEL_SOURCES_CONFIG.items()},
        "travel": {k: v["name"] for k, v in TRAVEL_SOURCES_CONFIG.items()},
        "research": {k: v["name"] for k, v in RESEARCH_SOURCES_CONFIG.items()},
        "museums": {k: v["name"] for k, v in MUSEUMS_CONFIG.items()},
        "games": {k: v["name"] for k, v in GAMES_SOURCES_CONFIG.items()},
    }
