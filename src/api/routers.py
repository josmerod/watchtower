"""API routers for Watchtower data."""

import json
import logging
from collections.abc import Collection

from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError

from src.api.models import UnifiedItem
from src.services.data_loader import (
    AI_PLATFORMS_SOURCES_CONFIG,
    ARXIV_SOURCES_CONFIG,
    BENCHMARKS_SOURCES_CONFIG,
    CLOUD_UPDATES_SOURCES_CONFIG,
    EXPANDED_SOURCES_CONFIG,
    GAMES_SOURCES_CONFIG,
    KNOWLEDGE_SOURCES_CONFIG,
    NEWS_SOURCES_CONFIG,
    SPANISH_AID_SOURCES_CONFIG,
    VALENCIA_LOCAL_SOURCES_CONFIG,
    format_article_date,
    get_item_dedupe_key,
    load_data_from_file,
)

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


def _load_and_process_items(config_dict: dict, source_filter: str | None = None, limit: int = 10000) -> list[UnifiedItem]:
    """Helper to load items from config and convert to UnifiedItem."""
    items: list[UnifiedItem] = []

    sources_to_load: Collection[str] = config_dict.keys()
    if source_filter:
        if source_filter in config_dict:
            sources_to_load = [source_filter]
        else:
            # Try replacing - with _ or vice versa if direct match fails
            alt_key = source_filter.replace("-", "_")
            if alt_key in config_dict:
                sources_to_load = [alt_key]
            else:
                return []  # Or raise 404? For now return empty list

    for key in sources_to_load:
        source_config = config_dict[key]
        raw_data = load_data_from_file(source_config["path"])

        for item in raw_data:
            # Map raw item to UnifiedItem
            # Handle variations in field names
            title = item.get("title") or item.get("name") or item.get("full_name") or item.get("model") or item.get("qualified_name") or item.get("display") or "No Title"
            url = item.get("url") or item.get("link") or item.get("html_url") or item.get("website")

            # Skip items without Title? (Maybe keep them for completeness but model requires title)
            if not title:
                continue

            unified_item = UnifiedItem(title=title, url=url, source=source_config["name"], published_at=format_article_date(item), category=key)  # Use the config key as category for now
            items.append(unified_item)

    # Sort items by some criteria? The dashboard sorts by date.
    # It might be expensive to sort everything every time.
    # Let's limit first? No, we must search/sort then limit.
    # For now, return unsorted or relying on file order, but dashboard sorts.
    # Let's simple return list

    # Remove duplicates across combined sources before applying the response limit.
    # Keep first-seen item, preserving source order and source-specific recency order.
    seen = set()
    unique_items: list[UnifiedItem] = []
    # separate name from the raw-dict `item` loop above so each keeps its true type
    for unified in items:
        dedupe_key = get_item_dedupe_key(unified.model_dump())
        if dedupe_key and dedupe_key in seen:
            continue
        if dedupe_key:
            seen.add(dedupe_key)
        unique_items.append(unified)

    return unique_items[:limit] if limit > 0 else unique_items


def _load_benchmarks(source_filter: str | None = None) -> dict:
    """Load benchmark data as raw dicts (not UnifiedItem) for table display."""
    sources_to_load: Collection[str] = BENCHMARKS_SOURCES_CONFIG.keys()
    if source_filter:
        if source_filter in BENCHMARKS_SOURCES_CONFIG:
            sources_to_load = [source_filter]
        else:
            return {"models": []}

    all_models = []
    for key in sources_to_load:
        source_config = BENCHMARKS_SOURCES_CONFIG[key]
        raw_data = load_data_from_file(source_config["path"])
        for item in raw_data:
            item["category"] = key
            item["source_name"] = source_config["name"]
            all_models.append(item)

    return {
        "count": len(all_models),
        "models": all_models,
    }


@router.get("/news", response_model=list[UnifiedItem])
async def get_news(source: str | None = Query(None, description="Filter by source key (e.g. 'techcrunch')"), limit: int = Query(10000, ge=1, le=10000, description="Max items to return")):
    """Get news items."""
    try:
        return _load_and_process_items(NEWS_SOURCES_CONFIG, source, limit)
    except (OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
        logger.error(f"Error fetching news: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/knowledge-garden", response_model=list[UnifiedItem])
async def get_knowledge(source: str | None = Query(None, description="Filter by source key (e.g. 'opensource')"), limit: int = Query(10000, ge=1, le=10000, description="Max items to return")):
    """Get knowledge garden items."""
    try:
        return _load_and_process_items(KNOWLEDGE_SOURCES_CONFIG, source, limit)
    except (OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
        logger.error(f"Error fetching knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/games", response_model=list[UnifiedItem])
async def get_games(source: str | None = Query(None, description="Filter by source key"), limit: int = Query(10000, ge=1, le=10000, description="Max items to return")):
    """Get games items."""
    try:
        return _load_and_process_items(GAMES_SOURCES_CONFIG, source, limit)
    except (OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
        logger.error(f"Error fetching games: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/benchmarks")
async def get_benchmarks(
    source: str | None = Query(None, description="Filter by benchmark category (overall, security, etc.)"),
):
    """Get AI coding benchmark data from BridgeBench.ai."""
    try:
        return _load_benchmarks(source)
    except (OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
        logger.error(f"Error fetching benchmarks: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/arxiv", response_model=list[UnifiedItem])
async def get_arxiv(source: str | None = Query(None, description="Filter by source key (e.g. 'papers', 'machine_learning')"), limit: int = Query(10000, ge=1, le=10000, description="Max items to return")):
    """Get ArXiv research papers."""
    try:
        return _load_and_process_items(ARXIV_SOURCES_CONFIG, source, limit)
    except (OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
        logger.error(f"Error fetching arxiv: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/ai-platforms", response_model=list[UnifiedItem])
async def get_ai_platforms(source: str | None = Query(None, description="Filter by source key (e.g. 'replicate')"), limit: int = Query(10000, ge=1, le=10000, description="Max items to return")):
    """Get AI platform model data."""
    try:
        return _load_and_process_items(AI_PLATFORMS_SOURCES_CONFIG, source, limit)
    except (OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
        logger.error(f"Error fetching ai-platforms: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/expanded", response_model=list[UnifiedItem])
async def get_expanded(
    source: str | None = Query(None, description="Filter by source key (e.g. 'github_analytics', 'stackexchange')"), limit: int = Query(10000, ge=1, le=10000, description="Max items to return")
):
    """Get expanded intelligence data (GitHub, StackExchange, OpenAlex, packages, Kaggle)."""
    try:
        return _load_and_process_items(EXPANDED_SOURCES_CONFIG, source, limit)
    except (OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
        logger.error(f"Error fetching expanded: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/spanish-aid", response_model=list[UnifiedItem])
async def get_spanish_aid(source: str | None = Query(None, description="Filter by source key"), limit: int = Query(10000, ge=1, le=10000, description="Max items to return")):
    """Get Spanish public aid and subsidies data."""
    try:
        return _load_and_process_items(SPANISH_AID_SOURCES_CONFIG, source, limit)
    except (OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
        logger.error(f"Error fetching spanish-aid: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/cloud-updates", response_model=list[UnifiedItem])
async def get_cloud_updates(source: str | None = Query(None, description="Filter by source key"), limit: int = Query(10000, ge=1, le=10000, description="Max items to return")):
    """Get cloud provider updates (AWS, GCP, CNCF, GitHub Blog)."""
    try:
        return _load_and_process_items(CLOUD_UPDATES_SOURCES_CONFIG, source, limit)
    except (OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
        logger.error(f"Error fetching cloud-updates: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/valencia-local", response_model=list[UnifiedItem])
async def get_valencia_local(source: str | None = Query(None, description="Filter by source key"), limit: int = Query(10000, ge=1, le=10000, description="Max items to return")):
    """Get Valencia local news and transport updates."""
    try:
        return _load_and_process_items(VALENCIA_LOCAL_SOURCES_CONFIG, source, limit)
    except (OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
        logger.error(f"Error fetching valencia-local: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sources", response_model=dict)
async def get_sources():
    """Get available sources."""
    return {
        "news": {k: v["name"] for k, v in NEWS_SOURCES_CONFIG.items()},
        "knowledge_garden": {k: v["name"] for k, v in KNOWLEDGE_SOURCES_CONFIG.items()},
        "games": {k: v["name"] for k, v in GAMES_SOURCES_CONFIG.items()},
        "benchmarks": {k: v["name"] for k, v in BENCHMARKS_SOURCES_CONFIG.items()},
        "arxiv": {k: v["name"] for k, v in ARXIV_SOURCES_CONFIG.items()},
        "ai_platforms": {k: v["name"] for k, v in AI_PLATFORMS_SOURCES_CONFIG.items()},
        "expanded": {k: v["name"] for k, v in EXPANDED_SOURCES_CONFIG.items()},
        "spanish_aid": {k: v["name"] for k, v in SPANISH_AID_SOURCES_CONFIG.items()},
        "cloud_updates": {k: v["name"] for k, v in CLOUD_UPDATES_SOURCES_CONFIG.items()},
        "valencia_local": {k: v["name"] for k, v in VALENCIA_LOCAL_SOURCES_CONFIG.items()},
    }
