"""Unraid Forums ETL — official announcements from the Unraid forum.

Fetches the Invision "Announcements Latest Topics" feed exposed by the News &
Announcements forum (id 7, discovered in the T-075 probe via the forum page's
``<link rel="alternate">``). The forum lives at forums.unraid.net and runs
Invision Community, so focused per-forum feeds use the /forum/{id}-{slug}.xml/
pattern — the old /rss/1-all-unraid-topics.xml/ aggregate mixed in every
support thread, which was noise; announcements (releases, betas, RCs) are the
signal for the homelab/Unraid angle the dashboard runs on. If the focused
feed fails or comes back empty, the ETL falls back to the all-topics feed so
the radar column degrades instead of going dark.

Usage:
    uv run python -m src.etl.news.news_get_unraid_forums

Output:
    data/news/unraid_forums_latest.json (+ timestamped snapshot)
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

logger = get_logger("UnraidForumsETL")

# Primary: News & Announcements forum (forum id 7). Fallback: full aggregate.
NEWS_FEED_URL = "https://forums.unraid.net/forum/7-announcements.xml/"
ALL_TOPICS_FEED_URL = "https://forums.unraid.net/rss/1-all-unraid-topics.xml/"

# Keep the persisted file lean — the radar column shows at most 25 per source.
MAX_ITEMS = 25


def _fetch_feed(url: str) -> list[dict[str, Any]]:
    """Fetch and normalize one Invision RSS feed into raw feedparser entries."""
    logger.info(f"Fetching Unraid feed {url}")
    response = requests.get(url, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    if feed.bozo:
        logger.warning(f"Feed parse warning for {url}: {feed.bozo_exception}")
    return list(feed.entries)


def _to_entry(entry: Any, feed_name: str) -> dict[str, Any]:
    """Normalize one feedparser entry to the persisted record shape."""
    published = _parse_date(entry.get("published", ""))
    summary = ""
    if hasattr(entry, "summary") and entry.summary:
        summary = re.sub(r"<[^>]+>", "", entry.summary).strip()
    author = ""
    if hasattr(entry, "author") and entry.author:
        author = entry.author
    return {
        "source": "unraid_forums",
        "source_category": "self_hosting",
        "title": entry.get("title", ""),
        "link": entry.get("link", ""),
        "published": published,
        "summary": summary[:500],
        "author": author,
        "categories": [t.get("term", "") for t in getattr(entry, "tags", [])],
        "guid": entry.get("id", ""),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "platform": "forums.unraid.net",
        "content_type": "forum_thread",
        "feed": feed_name,
        "language": "en",
        "region": "global",
    }


@with_retry
def fetch_unraid_forums() -> list[dict[str, Any]]:
    """Fetch Unraid forum entries: announcements first, all-topics as fallback."""
    entries: list[dict[str, Any]] = []
    feed_url, feed_name = NEWS_FEED_URL, "announcements"
    try:
        raw_entries = _fetch_feed(feed_url)
    except requests.RequestException as exc:
        logger.error(f"Could not fetch the Unraid announcements feed: {exc}")
        raw_entries = []

    if not raw_entries:
        logger.warning("Announcements feed empty or unreachable — falling back to the all-topics feed.")
        feed_url, feed_name = ALL_TOPICS_FEED_URL, "all_topics"
        try:
            raw_entries = _fetch_feed(feed_url)
        except requests.RequestException as exc:
            logger.error(f"Could not fetch the Unraid all-topics feed either: {exc}")
            return entries

    for entry in raw_entries[:MAX_ITEMS]:
        entries.append(_to_entry(entry, feed_name))
    logger.info(f"Retrieved {len(entries)} items from {feed_url}")
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


def save_unraid_forums_entries(entries: list[dict[str, Any]]) -> None:
    """Persist the Unraid forums entries under ``data/news/``."""
    if not entries:
        logger.info("No Unraid forums entries to save. Skipping.")
        return
    output_dir = os.path.join(get_project_root(), "data", "news")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "unraid_forums_latest.json")
    snapshot = os.path.join(output_dir, f"unraid_forums_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(entries)} Unraid forums entries to {latest}")


def main() -> None:
    """Run the Unraid forums ETL."""
    logger.info("Starting Unraid forums RSS ETL")
    try:
        entries = fetch_unraid_forums()
        if not entries:
            logger.warning("No entries fetched from the Unraid forums. Exiting.")
            return
        save_unraid_forums_entries(entries)
        logger.info(f"Unraid forums ETL complete: {len(entries)} threads.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"Unraid forums ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
