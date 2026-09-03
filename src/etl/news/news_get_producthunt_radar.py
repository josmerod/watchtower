"""Product Hunt radar ETL — keyless front-page launch feed.

Fetches Product Hunt's classic Atom feed (``/feed``, no API token needed)
and caps it at 25 launches. Feeds the Tech Radar tab's Products column
(T-082).

This is deliberately separate from the legacy class-based
``news_get_producthunt.py`` (GraphQL-with-token + RSS fallback, product-shaped
``name``/``tagline`` schema for the News tab): the radar and the public
``/api/v1/radar`` endpoint need the article-shaped ``title``/``link``/
``published`` contract, and the radar source must stay keyless.

Usage:
    uv run python -m src.etl.news.news_get_producthunt_radar

Output:
    data/news/producthunt_radar_latest.json (+ timestamped snapshot)
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.utils.retry import with_retry

logger = get_logger("ProductHuntRadarETL")

ATOM_FEED = "https://www.producthunt.com/feed"

# Keep the persisted file lean — the radar column shows at most 25 per source.
MAX_ITEMS = 25


@with_retry
def fetch_producthunt() -> list[dict[str, Any]]:
    """Fetch and parse the Product Hunt front-page Atom feed."""
    entries: list[dict[str, Any]] = []
    logger.info(f"Fetching Product Hunt feed from {ATOM_FEED}")
    try:
        response = requests.get(ATOM_FEED, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo:
            logger.warning(f"Feed parse warning: {feed.bozo_exception}")
    except requests.RequestException as exc:
        logger.error(f"Could not fetch the Product Hunt feed: {exc}")
        return entries

    for entry in feed.entries[:MAX_ITEMS]:
        published = _parse_date(entry.get("published", "") or entry.get("updated", ""))
        summary = ""
        if hasattr(entry, "summary") and entry.summary:
            summary = _clean_summary(entry.summary)
        author = ""
        if hasattr(entry, "author") and entry.author:
            author = entry.author
        entries.append(
            {
                "source": "producthunt",
                "source_category": "products",
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": published,
                "summary": summary[:500],
                "author": author,
                "categories": [t.get("term", "") for t in getattr(entry, "tags", [])],
                "guid": entry.get("id", ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "product_hunt",
                "content_type": "product_launch",
                "language": "en",
                "region": "global",
            }
        )
    logger.info(f"Retrieved {len(entries)} items from the Product Hunt feed")
    return entries


def _clean_summary(raw_html: str) -> str:
    """Strip the feed's HTML and drop the trailing promo links.

    Launch summaries end with a footer the feed renders as links — observed
    variants: ``Check it out`` and ``Discussion | Link``.
    """
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = re.sub(r"\s+", " ", text).strip()
    for promo in (" Check it out", " Discussion | Link"):
        if promo in text:
            text = text.split(promo)[0].strip()
    return text


def _parse_date(published_raw: str) -> str:
    """Parse an Atom/RSS date string to ISO format, falling back to the raw value."""
    if not published_raw:
        return ""
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(published_raw, fmt).isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(published_raw.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return published_raw


def save_producthunt_entries(entries: list[dict[str, Any]]) -> None:
    """Persist the Product Hunt entries under ``data/news/``."""
    if not entries:
        logger.info("No Product Hunt entries to save. Skipping.")
        return
    output_dir = os.path.join(get_project_root(), "data", "news")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "producthunt_radar_latest.json")
    snapshot = os.path.join(output_dir, f"producthunt_radar_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(entries)} Product Hunt entries to {latest}")


def main() -> None:
    """Run the Product Hunt radar ETL."""
    logger.info("Starting Product Hunt radar ETL")
    try:
        entries = fetch_producthunt()
        if not entries:
            logger.warning("No entries fetched from Product Hunt. Exiting.")
            return
        save_producthunt_entries(entries)
        logger.info(f"Product Hunt radar ETL complete: {len(entries)} launches.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"Product Hunt radar ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
