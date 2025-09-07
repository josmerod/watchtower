"""Lobsters RSS ETL

Parses the Lobsters technical community RSS feed.
Outputs canonical latest JSON/CSV under data/news/.
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


logger = get_logger("LobstersETL")


FEED_URL = "https://lobste.rs/rss"


def _parse_date(date_str: str | None) -> str | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z").isoformat()
    except Exception:
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
        except Exception:
            return date_str


def fetch_lobsters() -> List[Dict[str, Any]]:
    logger.info(f"Fetching Lobsters RSS: {FEED_URL}")
    entries: List[Dict[str, Any]] = []
    try:
        feed = feedparser.parse(FEED_URL)
    except Exception as e:
        logger.error(f"Failed to fetch Lobsters RSS: {e}")
        return entries

    for entry in getattr(feed, "entries", []) or []:
        summary = getattr(entry, "summary", "")
        summary_text = re.sub(r"<[^>]+>", "", summary).strip() if summary else ""
        tags = [t.term for t in getattr(entry, "tags", []) if hasattr(t, "term")]
        entries.append(
            {
                "source": "lobsters",
                "source_category": "developer_community",
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "published": _parse_date(getattr(entry, "published", None)),
                "summary": summary_text,
                "author": getattr(entry, "author", ""),
                "categories": tags,
                "guid": getattr(entry, "id", getattr(entry, "guid", "")),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "lobsters",
                "content_type": "news_article",
                "language": "en",
                "region": "global",
            }
        )

    logger.info(f"Retrieved {len(entries)} Lobsters posts")
    return entries


def save_lobsters(entries: List[Dict[str, Any]]) -> None:
    if not entries:
        logger.info("No Lobsters entries to save")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "news")
    ensure_directories([output_dir])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"lobsters_{ts}.json")
    csv_file = os.path.join(output_dir, f"lobsters_{ts}.csv")
    latest_json = os.path.join(output_dir, "lobsters_latest.json")
    latest_csv = os.path.join(output_dir, "lobsters_latest.csv")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    if entries:
        import csv

        flat: List[Dict[str, Any]] = []
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

    logger.info("Saved Lobsters latest and timestamped outputs")


def main():
    logger.info("Starting Lobsters ETL")
    entries = fetch_lobsters()
    if entries:
        save_lobsters(entries)
    logger.info("Lobsters ETL complete")


if __name__ == "__main__":
    main()

