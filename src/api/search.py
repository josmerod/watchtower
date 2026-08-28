"""Keyless global content search endpoint (T-057).

Serves the unified index built by :mod:`src.services.content_search` so the
dashboard command palette (and any LAN consumer) can search across every
indexed collection — news, releases, coins, videos and papers — from one
place. Same envelope/error conventions as :mod:`src.api.public` (``{"error":
...}`` bodies, ``Cache-Control: no-store``); the data root and the index are
injectable for hermetic tests.

Empty or whitespace-only ``q`` is rejected with **400** (chosen over returning
an empty result: an empty query is a client bug, not a legitimate "no matches"
state, and 400 keeps the palette from rendering stale-empty groups).
"""

import logging
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.services.content_search import DEFAULT_LIMIT, MAX_LIMIT, ContentSearchIndex
from src.utils.file_system import get_project_root

logger = logging.getLogger(__name__)

search_router = APIRouter(tags=["search"])


class SearchItem(BaseModel):
    """One normalized search result."""

    title: str
    url: str | None
    source: str
    kind: str
    published: str


class SearchResponse(BaseModel):
    """Envelope for ``GET /api/v1/search``."""

    query: str
    count: int
    items: list[SearchItem]


def _get_data_dir() -> Path:
    """Resolve the project ``data/`` directory (injectable for tests).

    Returns:
        Absolute path to the data directory.
    """
    return Path(get_project_root()) / "data"


def _build_index() -> ContentSearchIndex:
    """Create the index bound to the current data dir (injectable for tests)."""
    return ContentSearchIndex(data_dir=_get_data_dir())


_index: ContentSearchIndex | None = None
_index_lock = threading.Lock()


def _get_index() -> ContentSearchIndex:
    """Return the process-wide index, building it on first use."""
    global _index
    with _index_lock:
        if _index is None:
            _index = _build_index()
        return _index


@search_router.get("/search", response_model=SearchResponse)
async def global_search(
    response: Response, q: str = Query(..., description="Search term (case-insensitive substring)"), limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Max items to return")
) -> SearchResponse | JSONResponse:
    """Search every indexed collection (news, releases, coins, videos, papers).

    Returns ``{query, count, items}`` ranked by relevance (title prefix >
    whole word > substring, newest first within a tier). Missing data files
    simply contribute no items, so an empty corpus yields a 200 with ``count``
    0 rather than a 404. Empty or whitespace-only ``q`` yields 400.
    """
    term = (q or "").strip()
    if not term:
        return JSONResponse(status_code=400, content={"error": "Parameter 'q' must not be empty"}, headers={"Cache-Control": "no-store"})
    try:
        results = _get_index().search(term, limit=limit)
        response.headers["Cache-Control"] = "no-store"
        return SearchResponse(query=term, count=len(results), items=[SearchItem(**item) for item in results])
    except (OSError, ValueError, TypeError) as e:
        logger.error(f"Error running content search for {term!r}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
