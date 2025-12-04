"""Ars Technica RSS ETL

Parses Ars Technica RSS to collect deep technical analysis articles.
Outputs canonical latest JSON/CSV under data/news/.
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

logger = get_logger("ArsTechnicaETL")


FEED_URL = "https://feeds.arstechnica.com/arstechnica/index"


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


def fetch_arstechnica() -> list[dict[str, Any]]:
    logger.info(f"Fetching Ars Technica RSS: {FEED_URL}")
    entries: list[dict[str, Any]] = []
    try:
        feed = feedparser.parse(FEED_URL)
    except Exception as e:
        logger.error(f"Failed to fetch Ars Technica RSS: {e}")
        return entries

    for entry in getattr(feed, "entries", []) or []:
        summary = getattr(entry, "summary", "")
        summary_text = re.sub(r"<[^>]+>", "", summary).strip() if summary else ""
        tags = [t.term for t in getattr(entry, "tags", []) if hasattr(t, "term")]
        entries.append(
            {
                "source": "arstechnica",
                "source_category": "tech_news",
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "published": _parse_date(getattr(entry, "published", None)),
                "summary": summary_text,
                "author": getattr(entry, "author", ""),
                "categories": tags,
                "guid": getattr(entry, "id", getattr(entry, "guid", "")),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "arstechnica",
                "content_type": "news_article",
                "language": "en",
                "region": "global",
            }
        )

    logger.info(f"Retrieved {len(entries)} Ars Technica posts")
    return entries


def save_arstechnica(entries: list[dict[str, Any]]) -> None:
    if not entries:
        logger.info("No Ars Technica entries to save")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "news")
    ensure_directories([output_dir])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"arstechnica_{ts}.json")
    csv_file = os.path.join(output_dir, f"arstechnica_{ts}.csv")
    latest_json = os.path.join(output_dir, "arstechnica_latest.json")
    latest_csv = os.path.join(output_dir, "arstechnica_latest.csv")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    if entries:
        import csv

        flat: list[dict[str, Any]] = []
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

    logger.info("Saved Ars Technica latest and timestamped outputs")


def main():
    logger.info("Starting Ars Technica ETL")
    entries = fetch_arstechnica()
    if entries:
        save_arstechnica(entries)
    logger.info("Ars Technica ETL complete")


if __name__ == "__main__":
    main()
