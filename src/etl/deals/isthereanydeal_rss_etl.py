"""IsThereAnyDeal RSS ETL

Fetches Deals, Bundles, and Giveaways from IsThereAnyDeal RSS feeds.
Saves canonical latest JSON files under data/deals/.

Feeds per docs: https://isthereanydeal.com/feeds/
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import feedparser

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger


logger = get_logger("IsThereAnyDealRSSETL")


BASE = "https://isthereanydeal.com"
FEEDS = {
    "deals": f"{BASE}/feeds/US/USD/deals.rss",
    "bundles": f"{BASE}/feeds/US/USD/bundles.rss",
    "giveaways": f"{BASE}/feeds/US/giveaways.rss",
}


def _parse_date(date_str: str | None) -> str | None:
    if not date_str:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %y %H:%M:%S %z"):
        try:
            return datetime.strptime(date_str, fmt).isoformat()
        except Exception:
            continue
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
    except Exception:
        return date_str


def _extract_prices(text: str) -> Tuple[float | None, float | None, int | None]:
    if not text:
        return None, None, None
    # Try to extract percentages like "-75%" or "75% off"
    pct = None
    m = re.search(r"(\d{1,3})\s*%", text)
    if m:
        try:
            pct = int(m.group(1))
        except Exception:
            pct = None
    prices = [float(p) for p in re.findall(r"\$(\d+(?:\.\d{2})?)", text)]
    sale = min(prices) if prices else None
    orig = max(prices) if prices and len(prices) > 1 else None
    return orig, sale, pct


def _normalize_item(entry: Any, source: str, kind: str) -> Dict[str, Any]:
    title = getattr(entry, "title", "")
    link = getattr(entry, "link", "")
    summary = getattr(entry, "summary", getattr(entry, "description", "")) or ""
    summary_txt = re.sub(r"<[^>]+>", "", summary).strip()
    orig, sale, pct = _extract_prices(summary_txt)
    return {
        "title": title,
        "url": link,
        "platform": "IsThereAnyDeal",
        "category": "games",
        "deal_type": kind,
        "original_price": orig or 0,
        "current_price": sale or 0,
        "discount_percentage": pct or 0,
        "store_name": "Multiple",
        "description": summary_txt[:500],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
    }


def fetch_feed(kind: str) -> List[Dict[str, Any]]:
    url = FEEDS[kind]
    logger.info(f"Fetching ITAD {kind} feed: {url}")
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        logger.error(f"Failed to fetch ITAD {kind}: {e}")
        return []
    items: List[Dict[str, Any]] = []
    for entry in getattr(feed, "entries", []) or []:
        try:
            items.append(_normalize_item(entry, f"itad_{kind}", kind))
        except Exception:
            continue
    logger.info(f"Retrieved {len(items)} ITAD {kind} items")
    return items


def save_itad(kind: str, items: List[Dict[str, Any]]) -> None:
    out_dir = os.path.join(get_project_root(), "data", "deals")
    ensure_directories([out_dir])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(out_dir, f"isthereanydeal_{kind}_{ts}.json")
    latest_file = os.path.join(out_dir, f"isthereanydeal_{kind}_latest.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved ITAD {kind} latest and timestamped outputs")


def main():
    logger.info("Starting ITAD RSS ETL")
    for kind in ("deals", "bundles", "giveaways"):
        items = fetch_feed(kind)
        if items:
            save_itad(kind, items)
    logger.info("ITAD RSS ETL complete")


if __name__ == "__main__":
    main()








