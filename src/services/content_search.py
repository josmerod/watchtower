"""Unified in-memory content index backing the global search endpoint (T-057).

Builds a flat, normalized index of searchable items — ``{title, url, source,
kind, published}`` — from the latest JSON snapshots the dashboard tabs render:
news/radar articles, GitHub stack releases, CoinGecko coins, YouTube videos and
HF daily papers. The index is rebuilt lazily behind a TTL so repeated queries
do not hammer disk.

This module lives in ``src/services`` and must NEVER import dashboard modules
(the API service depends on it). The source-file lists below are replicated on
purpose — the established keep-in-sync pattern already used by
``src/api/public.py`` — from:

- ``RADAR_SOURCES`` in ``src/web/dashboard/components/tech_radar_tab.py``
- ``NEWS_SOURCES_CONFIG`` / ``CLOUD_UPDATES_SOURCES_CONFIG`` /
  ``VALENCIA_LOCAL_SOURCES_CONFIG`` in ``src/services/data_loader.py``
  (consumed by ``NEWS_TAB_DEFINITIONS`` in ``news_tab.py``)
- ``DATA_FILE`` in ``src/web/dashboard/components/markets_tab.py``
- the ``data/youtube/<channel>/youtube_videos.json`` glob in
  ``src/web/dashboard/components/videos_tab.py``
- ``data/arxiv/hf_daily_papers_latest.json`` (data_loader AI-research config)

Malformed or missing files degrade gracefully: they are skipped and logged at
warning level, never raised.
"""

import json
import logging
import re
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.file_system import get_project_root

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 25
MAX_LIMIT = 100
DEFAULT_TTL_SECONDS = 300.0

# Keep-in-sync news/article collections (see module docstring). ``source`` is a
# short human-readable label shown in the palette; ``kind`` drives the badge.
ARTICLE_COLLECTIONS: list[dict[str, Any]] = [
    # --- Radar sources (RADAR_SOURCES, tech_radar_tab.py) ---
    {"files": ["news/google_ai_blog_latest.json"], "source": "Google AI Blog"},
    {"files": ["news/verge_ai_latest.json"], "source": "The Verge AI"},
    {"files": ["kdnuggets/kdnuggets.json"], "source": "KDnuggets"},
    {"files": ["cloud_updates/cloud_updates_latest.json"], "source": "Cloud Updates"},
    {"files": ["selfhosted/selfhosted_latest.json"], "source": "Self-Hosted"},
    {"files": ["reddit_unified/SelfHosted_latest.json", "reddit_unified/homelab_latest.json"], "source": "Reddit Pulse"},
    {"files": ["news/unraid_forums_latest.json"], "source": "Unraid Forums"},
    {"files": ["infoq/infoq_news.json"], "source": "InfoQ"},
    {"files": ["thenewstack/thenewstack_news.json"], "source": "The New Stack"},
    {"files": ["news/phoronix_latest.json"], "source": "Phoronix"},
    {"files": ["changelog/changelog_news.json"], "source": "Changelog"},
    {"files": ["news/hn_frontpage_latest.json"], "source": "Hacker News"},
    {"files": ["news/lobsters_latest.json"], "source": "Lobsters"},
    {"files": ["news/wired_latest.json"], "source": "Wired"},
    {"files": ["news/mit_techreview_latest.json"], "source": "MIT Tech Review"},
    # --- News-tab sources (NEWS_SOURCES_CONFIG et al., data_loader.py) ---
    {"files": ["news/techcrunch_latest.json"], "source": "TechCrunch"},
    {"files": ["news/venturebeat_latest.json"], "source": "VentureBeat"},
    {"files": ["news/arstechnica_latest.json"], "source": "Ars Technica"},
    {"files": ["news/freecodecamp_latest.json"], "source": "freeCodeCamp"},
    {"files": ["futuretools/futuretoolsnews.json"], "source": "FutureTools"},
    {"files": ["bensbites/bensbites_news.json"], "source": "Ben's Bites"},
    {"files": ["hackernews/hackernews.json"], "source": "Hacker News"},
    {"files": ["medium_genai/medium_genai.json"], "source": "Medium GenAI"},
    {"files": ["meneame/meneame_general_latest.json"], "source": "Meneame General"},
    {"files": ["meneame/meneame_tecnologia_latest.json"], "source": "Meneame Tech"},
    {"files": ["indie_hackers/posts.json"], "source": "Indie Hackers"},
    {"files": ["kagi_world/kagi_world.json"], "source": "Kagi World"},
    {"files": ["kagi_usa/kagi_usa.json"], "source": "Kagi USA"},
    {"files": ["kagi_business/kagi_business.json"], "source": "Kagi Business"},
    {"files": ["kagi_science/kagi_science.json"], "source": "Kagi Science"},
    {"files": ["kagi_gaming/kagi_gaming.json"], "source": "Kagi Gaming"},
    {"files": ["kagi_europe/kagi_europe.json"], "source": "Kagi Europe"},
    {"files": ["kagi_spain/kagi_spain.json"], "source": "Kagi Spain"},
    {"files": ["kagi_ai/kagi_ai.json"], "source": "Kagi AI"},
    {"files": ["microsiervos/output/microsiervos_latest.json"], "source": "Microsiervos"},
    {"files": ["news/spanish_tech_latest.json"], "source": "Spanish Tech"},
    {"files": ["tldr/tldr_news.json"], "source": "tldr.tech"},
    {"files": ["valencia_local/valencia_local_latest.json"], "source": "Valencia Local"},
]

# GitHub releases of the self-hosted stack (github/stack_releases_latest.json,
# rendered by the radar "Mi stack" subtab — tech_radar_tab.py TR-F4).
RELEASES_FILE = "github/stack_releases_latest.json"
RELEASES_SOURCE = "Mi Stack"

# CoinGecko snapshot (markets_tab.py DATA_FILE). Coins have no stored URL, so
# one is built from the coin id exactly like markets_tab.py does.
MARKETS_FILE = "markets/coingecko_latest.json"
MARKETS_SOURCE = "CoinGecko"
_COIN_URL_TEMPLATE = "https://www.coingecko.com/en/coins/{coin_id}"

# HF daily papers (data_loader AI-research config; rendered by the AI tabs).
PAPERS_FILE = "arxiv/hf_daily_papers_latest.json"
PAPERS_SOURCE = "HF Daily Papers"

# YouTube channel snapshots (videos_tab.py): data/youtube/<channel>/youtube_videos.json.
VIDEOS_GLOB = "youtube/*/youtube_videos.json"
VIDEOS_SOURCE = "YouTube"

_WORD_BOUNDARY_CACHE: dict[str, re.Pattern[str]] = {}


def _default_data_dir() -> Path:
    """Resolve the project ``data/`` directory."""
    return Path(get_project_root()) / "data"


def _sortable_date(published: Any) -> float:
    """Best-effort epoch for date-desc sorting; undated entries sort last.

    Mirrors ``_sortable_date`` in ``src/api/public.py`` / ``tech_radar_tab.py``
    (same parsing fallbacks).
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


def _coerce_item_list(raw: Any) -> list[Any]:
    """Coerce heterogeneous ETL payloads into a flat list of entries."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("items", "articles", "coins", "videos"):
            candidate = raw.get(key)
            if isinstance(candidate, list):
                return candidate
    return []


def _read_json(path: Path) -> Any:
    """Read and parse a JSON file, returning None on any read/parse failure."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Skipping unreadable search file {path.name}: {e}")
        return None


def _article_items(entry: dict[str, Any], source: str) -> dict[str, Any] | None:
    """Normalize a news/radar/paper/release entry into an index item."""
    title = entry.get("title")
    if not title:
        return None
    link = entry.get("link") or entry.get("url")
    published = entry.get("published") or entry.get("published_at") or entry.get("fetched_at") or ""
    return {
        "title": str(title),
        "url": str(link) if link else None,
        "source": str(entry.get("source") or source),
        "kind": "news",
        "published": str(published),
        "_epoch": _sortable_date(published),
    }


def _coin_item(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize a CoinGecko coin into an index item."""
    name = entry.get("name")
    if not name:
        return None
    symbol = entry.get("symbol")
    title = f"{name} ({symbol.upper()})" if isinstance(symbol, str) and symbol else str(name)
    coin_id = entry.get("id")
    published = entry.get("fetched_at") or ""
    return {
        "title": title,
        "url": _COIN_URL_TEMPLATE.format(coin_id=coin_id) if coin_id else None,
        "source": MARKETS_SOURCE,
        "kind": "coin",
        "published": str(published),
        "_epoch": _sortable_date(published),
    }


def _video_item(entry: dict[str, Any], channel: str) -> dict[str, Any] | None:
    """Normalize a YouTube video into an index item."""
    title = entry.get("title")
    url = entry.get("url")
    if not title or not url:
        return None
    published = entry.get("published_at") or entry.get("fetched_at") or ""
    return {
        "title": str(title),
        "url": str(url),
        "source": str(entry.get("channel") or channel),
        "kind": "video",
        "published": str(published),
        "_epoch": _sortable_date(published),
    }


def build_index(data_dir: Path) -> list[dict[str, Any]]:
    """Build the normalized item list from every collection under ``data_dir``.

    Args:
        data_dir: Data root (normally the project ``data/`` directory).

    Returns:
        De-duplicated list of ``{title, url, source, kind, published, _epoch}``
        items. Missing or malformed files are skipped gracefully.
    """
    items: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    def _add(item: dict[str, Any] | None) -> None:
        if item is None:
            return
        url = item["url"]
        if url:
            if url in seen_urls:
                return
            seen_urls.add(url)
        else:
            title_key = f"{item['source'].lower()}|{item['title'].lower()}"
            if title_key in seen_titles:
                return
            seen_titles.add(title_key)
        items.append(item)

    # News/radar articles.
    for collection in ARTICLE_COLLECTIONS:
        for file_rel in collection["files"]:
            path = data_dir / file_rel
            if not path.is_file():
                continue
            raw = _read_json(path)
            if raw is None:
                continue
            for entry in _coerce_item_list(raw):
                if isinstance(entry, dict) and entry:
                    _add(_article_items(entry, collection["source"]))

    # GitHub stack releases.
    releases_path = data_dir / RELEASES_FILE
    if releases_path.is_file():
        raw = _read_json(releases_path)
        if raw is not None:
            for entry in _coerce_item_list(raw):
                if isinstance(entry, dict) and entry:
                    release = _article_items(entry, RELEASES_SOURCE)
                    if release is not None:
                        release["kind"] = "release"
                        _add(release)

    # CoinGecko coins.
    markets_path = data_dir / MARKETS_FILE
    if markets_path.is_file():
        raw = _read_json(markets_path)
        if raw is not None:
            for entry in _coerce_item_list(raw):
                if isinstance(entry, dict) and entry:
                    _add(_coin_item(entry))

    # HF daily papers.
    papers_path = data_dir / PAPERS_FILE
    if papers_path.is_file():
        raw = _read_json(papers_path)
        if raw is not None:
            for entry in _coerce_item_list(raw):
                if isinstance(entry, dict) and entry:
                    paper = _article_items(entry, PAPERS_SOURCE)
                    if paper is not None:
                        paper["kind"] = "paper"
                        _add(paper)

    # YouTube videos (one snapshot file per channel directory).
    videos_root = data_dir / "youtube"
    if videos_root.is_dir():
        for json_file in sorted(videos_root.glob("*/youtube_videos.json")):
            raw = _read_json(json_file)
            if raw is None:
                continue
            for entry in _coerce_item_list(raw):
                if isinstance(entry, dict) and entry:
                    _add(_video_item(entry, json_file.parent.name))

    return items


class ContentSearchIndex:
    """TTL-refreshed wrapper around :func:`build_index` with a query method.

    Args:
        data_dir: Data root, or a zero-arg callable resolving it (lazy so the
            default only touches the filesystem on first use).
        ttl_seconds: How long a built index stays fresh.
        now_fn: Time seam returning epoch seconds (injectable for tests).
    """

    def __init__(
        self,
        data_dir: Path | Callable[[], Path] | None = None,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        now_fn: Callable[[], float] = time.time,
    ) -> None:
        self._data_dir = data_dir if data_dir is not None else _default_data_dir
        self.ttl_seconds = ttl_seconds
        self._now_fn = now_fn
        self._items: list[dict[str, Any]] = []
        self._built_at = float("-inf")
        self._lock = threading.Lock()

    def _resolve_data_dir(self) -> Path:
        """Return the data root, invoking it when a callable was given."""
        return self._data_dir() if callable(self._data_dir) else self._data_dir

    def items(self) -> list[dict[str, Any]]:
        """Return the (possibly rebuilt) index items. Thread-safe."""
        with self._lock:
            fresh = (self._now_fn() - self._built_at) < self.ttl_seconds
            if fresh:
                return self._items
        items = build_index(self._resolve_data_dir())
        with self._lock:
            self._items = items
            self._built_at = self._now_fn()
        return items

    def invalidate(self) -> None:
        """Drop the cached items so the next ``items()`` call rebuilds."""
        with self._lock:
            self._items = []
            self._built_at = float("-inf")

    def search(self, query: str, limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
        """Query the index, ranked and capped.

        Ranking (per item, best wins): title prefix match > whole-word match in
        title > substring in title > substring in source. Ties break by newest
        ``published`` first, then alphabetically by title.

        Args:
            query: Case-insensitive search term (whitespace-stripped).
            limit: Maximum items to return; clamped to ``[1, MAX_LIMIT]``.

        Returns:
            Capped list of ``{title, url, source, kind, published}`` dicts.
        """
        term = (query or "").strip().lower()
        if not term:
            return []
        limit = max(1, min(limit, MAX_LIMIT))
        ranked: list[tuple[float, float, str, dict[str, Any]]] = []
        pattern = _WORD_BOUNDARY_CACHE.get(term)
        if pattern is None:
            pattern = re.compile(rf"\b{re.escape(term)}\b")
            _WORD_BOUNDARY_CACHE[term] = pattern
        for item in self.items():
            title = item["title"].lower()
            source = item["source"].lower()
            if title.startswith(term):
                score = 3.0
            elif pattern.search(title):
                score = 2.0
            elif term in title or term in source:
                score = 1.0
            else:
                continue
            ranked.append((score, item["_epoch"], title, item))
        ranked.sort(key=lambda row: (-row[0], -row[1], row[2]))
        return [
            {
                "title": item["title"],
                "url": item["url"],
                "source": item["source"],
                "kind": item["kind"],
                "published": item["published"],
            }
            for _, _, _, item in ranked[:limit]
        ]
