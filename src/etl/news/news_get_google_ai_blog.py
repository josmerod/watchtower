"""Google AI Blog RSS ETL Module

Fetches AI research and product updates from the Google AI Blog Atom feed.

Outputs canonical latest JSON and CSV files under data/news/.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import feedparser

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("GoogleAIBlogETL")


# Use RSS variant to avoid occasional Atom bozo parse errors
FEED_URL = "https://ai.googleblog.com/feeds/posts/default?alt=rss"
FALLBACK_FEED_URL = "https://blog.google/technology/ai/rss/"


def _parse_date(date_str: str | None) -> str | None:
    if not date_str:
        return None
    try:
        # Atom often provides updated/published in ISO-like format
        if "T" in date_str:
            # Normalize Z suffix if present
            if date_str.endswith("Z"):
                date_str = date_str[:-1] + "+00:00"
            return datetime.fromisoformat(date_str).isoformat()
    except Exception:
        pass
    # Fallbacks for RSS-like strings
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(date_str, fmt).isoformat()
        except Exception:
            continue
    # Give up, return raw
    return date_str


def fetch_google_ai_blog() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for url in (FEED_URL, FALLBACK_FEED_URL):
        logger.info(f"Fetching Google AI Blog feed: {url}")
        try:
            feed = feedparser.parse(url)
            if getattr(feed, "bozo", False):
                logger.warning(f"Feed parse error: {getattr(feed, 'bozo_exception', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to fetch Google AI Blog feed: {e}")
            continue

        if getattr(feed, "entries", []) and len(feed.entries) > 0:
            selected_feed = feed
            break
    else:
        selected_feed = None

    if not selected_feed:
        return entries

    for entry in getattr(selected_feed, "entries", []) or []:
        # Extract summary/content
        summary = ""
        if hasattr(entry, "summary") and entry.summary:
            summary = entry.summary
        elif hasattr(entry, "content") and entry.content:
            if isinstance(entry.content, list) and entry.content:
                summary = entry.content[0].get("value", "")
            else:
                summary = str(entry.content)
        # Strip HTML
        if summary:
            summary = re.sub(r"<[^>]+>", "", summary).strip()

        entry_data = {
            "source": "google_ai_blog",
            "source_category": "ai_research",
            "title": getattr(entry, "title", ""),
            "link": getattr(entry, "link", ""),
            # Prefer updated, fall back to published
            "published": _parse_date(getattr(entry, "updated", None) or getattr(entry, "published", None)),
            "summary": summary,
            "author": getattr(entry, "author", ""),
            "categories": [t.term for t in getattr(entry, "tags", []) if hasattr(t, "term")],
            "guid": getattr(entry, "id", getattr(entry, "guid", "")),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "platform": "google_ai_blog",
            "content_type": "ai_blog_post",
            "language": "en",
            "region": "global",
        }
        entries.append(entry_data)

    logger.info(f"Retrieved {len(entries)} Google AI Blog posts")
    return entries


def save_google_ai_blog(entries: list[dict[str, Any]]) -> None:
    if not entries:
        logger.info("No Google AI Blog entries to save")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "news")
    ensure_directories([output_dir])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"google_ai_blog_{ts}.json")
    csv_file = os.path.join(output_dir, f"google_ai_blog_{ts}.csv")
    latest_json = os.path.join(output_dir, "google_ai_blog_latest.json")
    latest_csv = os.path.join(output_dir, "google_ai_blog_latest.csv")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    # Save CSV (flatten lists)
    if entries:
        import csv

        flat_entries: list[dict[str, Any]] = []
        for e in entries:
            row = e.copy()
            for field in ("categories",):
                if isinstance(row.get(field), list):
                    row[field] = ", ".join(row[field])
            flat_entries.append(row)

        fieldnames = list(flat_entries[0].keys())
        for path in (csv_file, latest_csv):
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(flat_entries)

    logger.info(f"Saved Google AI Blog to {json_file} and {csv_file}; latest updated")


def main():
    logger.info("Starting Google AI Blog ETL")
    entries = fetch_google_ai_blog()
    if entries:
        save_google_ai_blog(entries)
    logger.info("Google AI Blog ETL complete")


if __name__ == "__main__":
    main()
