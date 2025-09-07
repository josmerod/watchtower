"""FreeCodeCamp News RSS ETL

Parses the FreeCodeCamp News RSS feed for programming tutorials and updates.
Outputs canonical latest JSON/CSV files under data/news/.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

import feedparser

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger


logger = get_logger("FreeCodeCampETL")


FEED_URL = "https://www.freecodecamp.org/news/rss/"


def _parse_date(date_str: str | None) -> str | None:
    if not date_str:
        return None
    # Try common formats, including two-digit year
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %y %H:%M:%S %z"):
        try:
            return datetime.strptime(date_str, fmt).isoformat()
        except Exception:
            continue
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
    except Exception:
        return date_str


def fetch_freecodecamp() -> List[Dict[str, Any]]:
    logger.info(f"Fetching FreeCodeCamp RSS: {FEED_URL}")
    entries: List[Dict[str, Any]] = []
    try:
        feed = feedparser.parse(FEED_URL)
    except Exception as e:
        logger.error(f"Failed to fetch FreeCodeCamp RSS: {e}")
        return entries

    for entry in getattr(feed, "entries", []) or []:
        summary = ""
        if hasattr(entry, "summary") and entry.summary:
            summary = entry.summary
        elif hasattr(entry, "content") and entry.content:
            if isinstance(entry.content, list) and entry.content:
                summary = entry.content[0].get("value", "")
            else:
                summary = str(entry.content)
        if summary:
            summary = re.sub(r"<[^>]+>", "", summary).strip()

        tags = [t.term for t in getattr(entry, "tags", []) if hasattr(t, "term")]

        entries.append(
            {
                "source": "freecodecamp",
                "source_category": "education",
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "published": _parse_date(getattr(entry, "published", None)),
                "summary": summary,
                "author": getattr(entry, "author", ""),
                "categories": tags,
                "guid": getattr(entry, "id", getattr(entry, "guid", "")),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "freecodecamp",
                "content_type": "tutorial_article",
                "language": "en",
                "region": "global",
            }
        )

    logger.info(f"Retrieved {len(entries)} FreeCodeCamp articles")
    return entries


def save_freecodecamp(entries: List[Dict[str, Any]]) -> None:
    if not entries:
        logger.info("No FreeCodeCamp entries to save")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "news")
    ensure_directories([output_dir])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"freecodecamp_{ts}.json")
    csv_file = os.path.join(output_dir, f"freecodecamp_{ts}.csv")
    latest_json = os.path.join(output_dir, "freecodecamp_latest.json")
    latest_csv = os.path.join(output_dir, "freecodecamp_latest.csv")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    if entries:
        import csv

        flat = []
        for e in entries:
            r = e.copy()
            if isinstance(r.get("categories"), list):
                r["categories"] = ", ".join(r["categories"])
            flat.append(r)
        fieldnames = list(flat[0].keys())
        for path in (csv_file, latest_csv):
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                w.writerows(flat)

    logger.info("Saved FreeCodeCamp latest and timestamped outputs")


def main():
    logger.info("Starting FreeCodeCamp ETL")
    entries = fetch_freecodecamp()
    if entries:
        save_freecodecamp(entries)
    logger.info("FreeCodeCamp ETL complete")


if __name__ == "__main__":
    main()


