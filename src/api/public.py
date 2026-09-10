"""Read-only public API endpoints for LAN automation consumers (e.g. n8n).

Exposes curated Watchtower outputs — crypto markets, the technology radar
merge, and data freshness — as stable JSON envelopes. The module is
intentionally dependency-light: data files are read straight from the project
``data/`` directory and the radar source list is replicated from
``src/web/dashboard/components/tech_radar_tab.py`` (RADAR_SOURCES) so the API
never imports Dash modules. The data root is resolved through
:func:`_get_data_dir`, which tests monkeypatch to point at ``tmp_path``.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.api.models import MarketsResponse, RadarItem, RadarResponse
from src.utils.file_system import get_project_root

logger = logging.getLogger(__name__)

public_router = APIRouter(tags=["public"])

# Relative to the project data/ directory.
MARKETS_FILE = "markets/coingecko_latest.json"
FRESHNESS_FILE = "watchers/data_freshness/freshness_latest.json"
DIGEST_FILE = "insights/digest_latest.json"
SECURITY_FILE = "security/security_latest.json"
VALENCIA_EVENTS_FILE = "valencia_events/valencia_events.json"

# Radar source files, mirroring RADAR_SOURCES in
# src/web/dashboard/components/tech_radar_tab.py (paths + categories only;
# labels/icons are a display concern). Replicated here on purpose so the API
# does not depend on Dash modules.
RADAR_SOURCES: list[dict[str, Any]] = [
    {"key": "google_ai", "files": ["news/google_ai_blog_latest.json"], "category": "AI"},
    {"key": "verge_ai", "files": ["news/verge_ai_latest.json"], "category": "AI"},
    {"key": "ollama", "files": ["ai_platforms/ollama_library_latest.json"], "category": "Local LLM"},
    {"key": "kdnuggets", "files": ["kdnuggets/kdnuggets.json"], "category": "Data Science"},
    {"key": "cloud_updates", "files": ["cloud_updates/cloud_updates_latest.json"], "category": "Cloud"},
    {"key": "azure_blog", "files": ["news/azure_blog_latest.json"], "category": "Cloud"},
    {"key": "selfhosted", "files": ["selfhosted/selfhosted_latest.json"], "category": "Self-Hosting"},
    {
        "key": "reddit_pulse",
        "files": ["reddit_unified/SelfHosted_latest.json", "reddit_unified/homelab_latest.json"],
        "category": "Self-Hosting",
    },
    {"key": "unraid_forums", "files": ["news/unraid_forums_latest.json"], "category": "Self-Hosting"},
    {"key": "lemmy", "files": ["news/lemmy_latest.json"], "category": "Self-Hosting"},
    {"key": "infoq", "files": ["infoq/infoq_news.json"], "category": "Engineering"},
    {"key": "thenewstack", "files": ["thenewstack/thenewstack_news.json"], "category": "Cloud-Native"},
    {"key": "phoronix", "files": ["news/phoronix_latest.json"], "category": "Linux/Hardware"},
    {"key": "servethehome", "files": ["news/servethehome_latest.json"], "category": "Linux/Hardware"},
    {"key": "changelog", "files": ["changelog/changelog_news.json"], "category": "Open Source"},
    {"key": "github_trending", "files": ["github/github_trending_latest.json"], "category": "Open Source"},
    {"key": "producthunt", "files": ["news/producthunt_radar_latest.json"], "category": "Products"},
    {"key": "hn_frontpage", "files": ["news/hn_frontpage_latest.json"], "category": "Discussion"},
    {"key": "lobsters", "files": ["news/lobsters_latest.json"], "category": "Engineering"},
    {"key": "wired", "files": ["news/wired_latest.json"], "category": "Tech Media"},
    {"key": "mit_techreview", "files": ["news/mit_techreview_latest.json"], "category": "Emerging Tech"},
    {"key": "xataka", "files": ["news/xataka_latest.json"], "category": "Tech Media ES"},
    {"key": "mi_stack", "files": ["github/stack_releases_latest.json"], "category": "Mi Stack"},
]

RADAR_DEFAULT_LIMIT = 200


def _get_data_dir() -> Path:
    """Resolve the project ``data/`` directory (injectable for tests).

    Returns:
        Absolute path to the data directory.
    """
    return Path(get_project_root()) / "data"


def _read_json_file(path: Path) -> Any:
    """Read and parse a JSON file from disk.

    Args:
        path: Absolute file path.

    Returns:
        The parsed JSON payload.
    """
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _not_found(message: str) -> JSONResponse:
    """Build a 404 response with an ``{"error": ...}`` body and no-store cache."""
    return JSONResponse(status_code=404, content={"error": message}, headers={"Cache-Control": "no-store"})


def _file_mtime_iso(path: Path) -> str | None:
    """Last-modified timestamp of a file as UTC ISO 8601, or None."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return None


def _coerce_item_list(raw: Any) -> list[Any]:
    """Coerce heterogeneous ETL payloads into a flat list of entries."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("items", "articles", "coins"):
            candidate = raw.get(key)
            if isinstance(candidate, list):
                return candidate
    return []


def _sortable_date(published: Any) -> float:
    """Best-effort epoch for date-desc sorting; undated entries sort last.

    Mirrors ``_sortable_date`` in tech_radar_tab.py (same parsing fallbacks).
    """
    raw = str(published or "")
    if not raw:
        return 0.0
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        pass
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def _max_generated_at(items: list[dict[str, Any]], keys: tuple[str, ...]) -> str | None:
    """Newest parseable timestamp among ``keys`` across items, or None."""
    best: tuple[float, str] | None = None
    for item in items:
        for key in keys:
            raw = item.get(key)
            if not raw:
                continue
            epoch = _sortable_date(raw)
            if epoch > 0 and (best is None or epoch > best[0]):
                best = (epoch, str(raw))
    return best[1] if best else None


@public_router.get("/markets", response_model=MarketsResponse)
async def get_markets(response: Response, limit: int = Query(RADAR_DEFAULT_LIMIT, ge=1, le=500, description="Max items to return")):
    """Get top crypto market quotes (CoinGecko snapshot).

    Reads ``data/markets/coingecko_latest.json`` and returns the stored coin
    list as-is (malformed entries are skipped).
    """
    path = _get_data_dir() / MARKETS_FILE
    if not path.is_file():
        return _not_found(f"Market data file not found: {MARKETS_FILE}")
    try:
        raw = _read_json_file(path)
        entries = [e for e in _coerce_item_list(raw) if isinstance(e, dict) and e]
        generated_at = _max_generated_at(entries, ("fetched_at", "generated_at")) or _file_mtime_iso(path)
        items = entries[:limit]
        response.headers["Cache-Control"] = "no-store"
        return MarketsResponse(generated_at=generated_at, count=len(items), items=items)
    except (OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
        logger.error(f"Error fetching markets: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@public_router.get("/radar", response_model=RadarResponse)
async def get_radar(response: Response, limit: int = Query(RADAR_DEFAULT_LIMIT, ge=1, le=500, description="Max items to return")):
    """Get the merged technology-radar feed (newest first).

    Merges the same source files as the dashboard's Tech Radar tab: per-source
    de-duplication on ``link``/``url``/``title``, ``published`` falling back to
    ``published_at``/``fetched_at``, date-descending order. Each item carries
    ``{title, link, source, published, category}`` where ``source`` is the
    stable radar source key (e.g. ``google_ai``).
    """
    data_dir = _get_data_dir()
    found_any_file = False
    newest_mtime: str | None = None
    rows: list[tuple[float, dict[str, Any]]] = []
    for source in RADAR_SOURCES:
        articles: list[dict[str, Any]] = []
        seen: set[str] = set()
        for file_rel in source["files"]:
            path = data_dir / file_rel
            if not path.is_file():
                continue
            found_any_file = True
            try:
                raw = _read_json_file(path)
            except (OSError, json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Skipping unreadable radar file {file_rel}: {e}")
                continue
            mtime = _file_mtime_iso(path)
            if mtime and (newest_mtime is None or mtime > newest_mtime):
                newest_mtime = mtime
            for entry in raw if isinstance(raw, list) else []:
                if not isinstance(entry, dict):
                    continue
                key = entry.get("link") or entry.get("url") or entry.get("title") or ""
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                articles.append(entry)
        for entry in articles:
            title = entry.get("title")
            if not title:
                continue
            published = entry.get("published") or entry.get("published_at") or entry.get("fetched_at") or ""
            link = entry.get("link") or entry.get("url")
            item = {
                "title": str(title),
                "link": str(link) if link else None,
                "source": source["key"],
                "published": str(published),
                "category": source["category"],
            }
            rows.append((_sortable_date(published), item))
    if not found_any_file:
        return _not_found("No tech radar data files found. Run the ETL pipelines first.")
    rows.sort(key=lambda row: row[0], reverse=True)
    items = [item for _, item in rows[:limit]]
    response.headers["Cache-Control"] = "no-store"
    return RadarResponse(generated_at=newest_mtime, count=len(items), items=cast("list[RadarItem]", items))


@public_router.get("/freshness")
async def get_freshness(response: Response):
    """Get the data-freshness summary plus a convenience ``stale_sources`` list.

    Reads ``data/watchers/data_freshness/freshness_latest.json`` and returns
    the stored summary as-is; ``stale_sources`` lists every source record whose
    status is not ``fresh`` (i.e. ``stale`` or ``critical``).
    """
    path = _get_data_dir() / FRESHNESS_FILE
    if not path.is_file():
        return _not_found(f"Freshness data file not found: {FRESHNESS_FILE}")
    try:
        summary = _read_json_file(path)
        if not isinstance(summary, dict):
            raise ValueError(f"Unexpected freshness payload type: {type(summary).__name__}")
        sources = summary.get("sources")
        stale_sources = [s for s in sources if isinstance(s, dict) and s.get("status") != "fresh"] if isinstance(sources, list) else []
        response.headers["Cache-Control"] = "no-store"
        return {**summary, "stale_sources": stale_sources}
    except (OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
        logger.error(f"Error fetching freshness: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@public_router.get("/digest")
async def get_digest(response: Response):
    """Get the compiled weekly digest (terms, radar picks, movers).

    Reads ``data/insights/digest_latest.json`` (produced by the weekly-digest
    ETL from local files) and returns the stored summary as-is.
    """
    path = _get_data_dir() / DIGEST_FILE
    if not path.is_file():
        return _not_found(f"Digest data file not found: {DIGEST_FILE}")
    try:
        digest = _read_json_file(path)
        if not isinstance(digest, dict):
            raise ValueError(f"Unexpected digest payload type: {type(digest).__name__}")
        response.headers["Cache-Control"] = "no-store"
        return digest
    except (OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
        logger.error(f"Error fetching digest: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@public_router.get("/security/kev")
async def get_security_kev(response: Response, limit: int = Query(100, ge=1, le=500, description="Max KEV entries to return")):
    """Get actively-exploited CVEs (CISA KEV) plus matches against my stack.

    Reads ``data/security/security_latest.json`` (the Security tab's envelope)
    and returns the KEV items plus the ``stack_matches`` cross-reference
    (T-081): every KEV entry whose vendor/product hits one of the self-hosted
    stack services.
    """
    path = _get_data_dir() / SECURITY_FILE
    if not path.is_file():
        return _not_found(f"Security data file not found: {SECURITY_FILE}")
    try:
        envelope = _read_json_file(path)
        if not isinstance(envelope, dict):
            raise ValueError(f"Unexpected security payload type: {type(envelope).__name__}")
        items = envelope.get("items") or []
        stack_matches = envelope.get("stack_matches") or []
        response.headers["Cache-Control"] = "no-store"
        return {
            "generated_at": envelope.get("generated_at") or _file_mtime_iso(path),
            "kev_count": len(items),
            "items": items[:limit],
            "stack_matches": stack_matches,
        }
    except (OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
        logger.error(f"Error fetching security KEV: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@public_router.get("/valencia/events")
async def get_valencia_events(
    response: Response, days: int = Query(0, ge=0, le=365, description="Only events starting within N days from now (0 = all)"), limit: int = Query(200, ge=1, le=500, description="Max events to return")
):
    """Get Valencia events (for calendar automations).

    Reads ``data/valencia_events/valencia_events.json`` and returns the events
    as-is. With ``days > 0`` only events whose ``start_date`` falls within the
    next N days are returned (events without a date are excluded from that
    filtered view only).
    """
    path = _get_data_dir() / VALENCIA_EVENTS_FILE
    if not path.is_file():
        return _not_found(f"Valencia events file not found: {VALENCIA_EVENTS_FILE}")
    try:
        events = _read_json_file(path)
        if isinstance(events, dict):
            events = events.get("events") or events.get("items") or []
        if not isinstance(events, list):
            raise ValueError(f"Unexpected Valencia events payload type: {type(events).__name__}")
        if days > 0:
            now = datetime.now(timezone.utc).timestamp()
            horizon = now + days * 86400
            events = [e for e in events if isinstance(e, dict) and now <= _sortable_date(e.get("start_date")) <= horizon]
        response.headers["Cache-Control"] = "no-store"
        return {
            "generated_at": _file_mtime_iso(path),
            "count": len(events),
            "items": events[:limit],
        }
    except (OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
        logger.error(f"Error fetching Valencia events: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
