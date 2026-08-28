"""Phoronix ETL — Linux, hardware, and open-source benchmarking news.

Fetches Phoronix's main RSS feed — the reference outlet for Linux kernel,
graphics driver, and storage/hardware coverage on the homelab angle. Feeds
the Tech Radar tab's Linux/Hardware column (T-070).

Usage:
    uv run python -m src.etl.news.news_get_phoronix

Output:
    data/news/phoronix_latest.json (+ timestamped snapshot)
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

logger = get_logger("PhoronixETL")

RSS_FEED = "https://www.phoronix.com/rss.php"

# Keep the persisted file lean — the radar column shows at most 25 per source.
MAX_ITEMS = 25


@with_retry
def fetch_phoronix() -> list[dict[str, Any]]:
    """Fetch and parse the Phoronix RSS feed."""
    entries: list[dict[str, Any]] = []
    logger.info(f"Fetching Phoronix RSS feed from {RSS_FEED}")
    try:
        response = requests.get(RSS_FEED, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo:
            logger.warning(f"Feed parse warning: {feed.bozo_exception}")
    except requests.RequestException as exc:
        logger.error(f"Could not fetch the Phoronix feed: {exc}")
        return entries

    for entry in feed.entries[:MAX_ITEMS]:
        published = _parse_date(entry.get("published", ""))
        summary = ""
        if hasattr(entry, "summary") and entry.summary:
            summary = re.sub(r"<[^>]+>", "", entry.summary).strip()
        author = ""
        if hasattr(entry, "author") and entry.author:
            author = entry.author
        entries.append(
            {
                "source": "phoronix",
                "source_category": "linux_hardware",
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": published,
                "summary": summary[:500],
                "author": author,
                "categories": [t.get("term", "") for t in getattr(entry, "tags", [])],
                "guid": entry.get("id", ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "phoronix",
                "content_type": "news_article",
                "language": "en",
                "region": "global",
            }
        )
    logger.info(f"Retrieved {len(entries)} items from the Phoronix feed")
    return entries


def _parse_date(published_raw: str) -> str:
    """Parse an RSS date string to ISO format, falling back to the raw value."""
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


def save_phoronix_entries(entries: list[dict[str, Any]]) -> None:
    """Persist the Phoronix entries under ``data/news/``."""
    if not entries:
        logger.info("No Phoronix entries to save. Skipping.")
        return
    output_dir = os.path.join(get_project_root(), "data", "news")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "phoronix_latest.json")
    snapshot = os.path.join(output_dir, f"phoronix_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(entries)} Phoronix entries to {latest}")


def main() -> None:
    """Run the Phoronix ETL."""
    logger.info("Starting Phoronix RSS ETL")
    try:
        entries = fetch_phoronix()
        if not entries:
            logger.warning("No entries fetched from Phoronix. Exiting.")
            return
        save_phoronix_entries(entries)
        logger.info(f"Phoronix ETL complete: {len(entries)} articles.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"Phoronix ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
