"""FutureTools News ETL — AI tools news from news.futuretools.io.

Fetches the FutureTools.io news RSS feed ("The AI News Worth Talking About")
and persists entries to ``data/futuretools/``. FutureTools covers AI tool
launches, updates, and industry news — a relevant source for tracking the
AI tooling landscape.

The previous FutureTools scraper was removed; this rebuilds it against the
site's reliable RSS feed (no JS rendering needed).

Usage:
    uv run python -m src.etl.news.news_get_futuretools

Output:
    - data/futuretools/futuretoolsnews.json  (latest, read by the dashboard)
    - data/futuretools/futuretoolsnews_<timestamp>.json
    - data/futuretools/futuretoolsnews_<timestamp>.csv
"""

import csv
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

logger = get_logger("FutureToolsETL")

RSS_FEED = "https://news.futuretools.io/feed/"


@with_retry
def fetch_futuretools_feed() -> list[dict[str, Any]]:
    """Fetch and parse the FutureTools.io news RSS feed.

    Returns:
        List of normalized news entries.
    """
    entries: list[dict[str, Any]] = []

    logger.info(f"Fetching FutureTools RSS feed from {RSS_FEED}")
    try:
        headers = {"User-Agent": SCRAPER_DEFAULT_USER_AGENT}
        response = requests.get(RSS_FEED, headers=headers, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo:
            logger.warning(f"Feed parse warning: {feed.bozo_exception}")
    except requests.RequestException as exc:
        logger.error(f"Could not fetch FutureTools feed: {exc}")
        return entries

    for entry in feed.entries:
        published_raw = entry.get("published", "")
        published = _parse_date(published_raw)

        # Categories/tags
        categories: list[str] = []
        if hasattr(entry, "tags") and entry.tags:
            categories = [tag.term for tag in entry.tags if hasattr(tag, "term")]
        elif hasattr(entry, "category") and entry.category:
            categories = [entry.category]

        # Author
        author = ""
        if hasattr(entry, "author") and entry.author:
            author = entry.author

        # Summary (strip HTML)
        summary = ""
        if hasattr(entry, "summary") and entry.summary:
            summary = entry.summary
        elif hasattr(entry, "description") and entry.description:
            summary = entry.description
        if summary:
            summary = re.sub(r"<[^>]+>", "", summary).strip()

        entries.append(
            {
                "source": "futuretools",
                "source_category": "ai_tools",
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": published,
                "summary": summary,
                "author": author,
                "categories": categories,
                "guid": entry.get("id", entry.get("guid", "")),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "futuretools",
                "content_type": "news_article",
                "language": "en",
                "region": "global",
            }
        )

    logger.info(f"Retrieved {len(entries)} items from FutureTools RSS feed")
    return entries


def _parse_date(published_raw: str) -> str:
    """Parse an RSS date string to ISO format, falling back to the raw value."""
    if not published_raw:
        return ""
    # RFC 2822 (standard RSS)
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(published_raw, fmt).isoformat()
        except ValueError:
            continue
    # ISO 8601
    try:
        return datetime.fromisoformat(published_raw.replace("Z", "+00:00")).isoformat()
    except ValueError:
        pass
    logger.warning(f"Unparsable date '{published_raw}'; using raw value.")
    return published_raw


def save_futuretools_entries(entries: list[dict[str, Any]]) -> None:
    """Persist FutureTools entries to JSON + CSV under ``data/futuretools/``."""
    if not entries:
        logger.info("No FutureTools entries to save. Skipping.")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "futuretools")
    ensure_directories([output_dir])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"futuretoolsnews_{timestamp}.json")
    csv_file = os.path.join(output_dir, f"futuretoolsnews_{timestamp}.csv")
    # The dashboard reads this fixed filename (per src/services/data_loader.py).
    latest_json = os.path.join(output_dir, "futuretoolsnews.json")

    for path in (json_file, latest_json):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)

    # CSV (flatten list fields)
    csv_entries = []
    for entry in entries:
        flat = entry.copy()
        if isinstance(flat.get("categories"), list):
            flat["categories"] = ", ".join(flat["categories"])
        csv_entries.append(flat)
    fieldnames = csv_entries[0].keys() if csv_entries else []
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_entries)

    logger.info(f"Saved {len(entries)} FutureTools entries to {json_file} + {latest_json}")


def main() -> None:
    """Run the FutureTools ETL."""
    logger.info("Starting FutureTools RSS ETL")
    try:
        entries = fetch_futuretools_feed()
        if not entries:
            logger.warning("No entries fetched from FutureTools. Exiting.")
            return
        save_futuretools_entries(entries)
        logger.info(f"FutureTools ETL complete: {len(entries)} articles.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"FutureTools ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
