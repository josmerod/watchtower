"""Metacritic Games RSS ETL

Parses Metacritic Games RSS to collect recent reviews and scores.
Outputs canonical latest JSON/CSV under data/games/.
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

logger = get_logger("MetacriticGamesETL")


FEED_URL = "https://www.metacritic.com/rss/games"


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


def _extract_score(text: str) -> int | None:
    if not text:
        return None
    match = re.search(r"(\b\d{1,3}\b)\s*(?:/\s*100|/100)?", text)
    if match:
        try:
            score = int(match.group(1))
            if 0 <= score <= 100:
                return score
        except Exception:
            return None
    return None


def fetch_metacritic_games() -> list[dict[str, Any]]:
    logger.info(f"Fetching Metacritic Games RSS: {FEED_URL}")
    entries: list[dict[str, Any]] = []
    try:
        feed = feedparser.parse(FEED_URL)
    except Exception as e:
        logger.error(f"Failed to fetch Metacritic RSS: {e}")
        return entries

    for entry in getattr(feed, "entries", []) or []:
        title = getattr(entry, "title", "")
        summary = getattr(entry, "summary", "")
        summary_text = re.sub(r"<[^>]+>", "", summary).strip() if summary else ""
        score_in_title = _extract_score(title)
        score_in_summary = _extract_score(summary_text)
        score = score_in_title if score_in_title is not None else score_in_summary

        entries.append(
            {
                "source": "metacritic",
                "source_category": "games_reviews",
                "title": title,
                "link": getattr(entry, "link", ""),
                "published": _parse_date(getattr(entry, "published", None)),
                "summary": summary_text,
                "author": getattr(entry, "author", ""),
                "categories": [t.term for t in getattr(entry, "tags", []) if hasattr(t, "term")],
                "guid": getattr(entry, "id", getattr(entry, "guid", "")),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "metacritic",
                "content_type": "game_review",
                "language": "en",
                "region": "global",
                "metacritic_score": score,
            }
        )

    logger.info(f"Retrieved {len(entries)} Metacritic items")
    return entries


def save_metacritic(entries: list[dict[str, Any]]) -> None:
    if not entries:
        logger.info("No Metacritic entries to save")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "games")
    ensure_directories([output_dir])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"metacritic_{ts}.json")
    csv_file = os.path.join(output_dir, f"metacritic_{ts}.csv")
    latest_json = os.path.join(output_dir, "metacritic_latest.json")
    latest_csv = os.path.join(output_dir, "metacritic_latest.csv")

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

    logger.info("Saved Metacritic latest and timestamped outputs")


def main():
    logger.info("Starting Metacritic Games RSS ETL")
    entries = fetch_metacritic_games()
    if entries:
        save_metacritic(entries)
    logger.info("Metacritic ETL complete")


if __name__ == "__main__":
    main()
