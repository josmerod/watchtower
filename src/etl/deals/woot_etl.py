"""Woot! RSS ETL Module

Fetches daily deals from Woot! RSS feeds and saves canonical latest outputs.
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

logger = get_logger("WootETL")


RSS_URL = "https://www.woot.com/rss/"


def _parse_price(text: str) -> dict[str, Any]:
    info: dict[str, Any] = {"has_price": False, "prices": []}
    if not text:
        return info
    prices = re.findall(r"\$(\d+(?:\.\d{2})?)", text)
    if prices:
        info["has_price"] = True
        info["prices"] = [float(p) for p in prices]
    return info


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


def fetch_woot() -> list[dict[str, Any]]:
    logger.info(f"Fetching Woot RSS: {RSS_URL}")
    entries: list[dict[str, Any]] = []
    try:
        feed = feedparser.parse(RSS_URL)
    except Exception as e:
        logger.error(f"Failed to fetch Woot RSS: {e}")
        return entries

    for entry in getattr(feed, "entries", []) or []:
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
        summary_text = re.sub(r"<[^>]+>", "", summary).strip() if summary else ""

        price_info = _parse_price(summary_text)

        entries.append(
            {
                "source": "woot",
                "source_category": "daily_deals",
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "published": _parse_date(getattr(entry, "published", None)),
                "summary": summary_text,
                "author": getattr(entry, "author", ""),
                "categories": [t.term for t in getattr(entry, "tags", []) if hasattr(t, "term")],
                "guid": getattr(entry, "id", getattr(entry, "guid", "")),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "woot",
                "content_type": "deal",
                "language": "en",
                "region": "us",
                "price_info": price_info,
            }
        )

    logger.info(f"Retrieved {len(entries)} Woot deals")
    return entries


def save_woot(entries: list[dict[str, Any]]) -> None:
    if not entries:
        logger.info("No Woot entries to save")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "deals")
    ensure_directories([output_dir])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"woot_{ts}.json")
    csv_file = os.path.join(output_dir, f"woot_{ts}.csv")
    latest_json = os.path.join(output_dir, "woot_latest.json")
    latest_csv = os.path.join(output_dir, "woot_latest.csv")

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
            if isinstance(r.get("price_info"), dict):
                r["price_info"] = json.dumps(r["price_info"])
            flat.append(r)
        fieldnames = list(flat[0].keys())
        for path in (csv_file, latest_csv):
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                w.writerows(flat)

    logger.info("Saved Woot latest and timestamped outputs")


def main():
    logger.info("Starting Woot ETL")
    entries = fetch_woot()
    if entries:
        save_woot(entries)
    logger.info("Woot ETL complete")


if __name__ == "__main__":
    main()
