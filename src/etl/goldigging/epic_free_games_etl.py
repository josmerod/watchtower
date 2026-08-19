"""Epic Games Free Games ETL

Fetches Epic Games Store's free-game promotions from the public storefront
API (no key required) and writes them in the unified scavenging record shape
so the Scavenging tab picks the file up automatically.

Usage:
    uv run python src/etl/goldigging/epic_free_games_etl.py

Output:
    - data/scavenging/epic_free_games.json
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("EpicFreeGamesETL")

API_URL = "https://store-site.ak.epicgames.com/api/v2/freeGamesPromotions"
PARAMS = {"locale": "es-ES", "country": "ES"}
HEADERS = {"User-Agent": "Mozilla/5.0 (WatchtowerBot)"}
OUTPUT_FILE = Path("data/scavenging/epic_free_games.json")


def _store_url(element: dict[str, Any]) -> str:
    """Build the store page URL for a catalog element."""
    slug = element.get("productSlug") or element.get("urlSlug")
    if slug:
        return f"https://store.epicgames.com/es-ES/p/{slug}"
    return "https://store.epicgames.com/es-ES/free-games"


def _parse_date(date_str: str | None) -> str:
    """Parse an Epic ISO date to a display-friendly ISO string."""
    if not date_str:
        return ""
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).astimezone().isoformat(timespec="minutes")
    except ValueError:
        return date_str


def fetch_free_games(max_retries: int = 3) -> list[dict[str, Any]]:
    """Fetch current and upcoming free-game promotions from Epic."""
    payload = None
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching Epic free games promotions from {API_URL}")
            resp = requests.get(API_URL, params=PARAMS, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
            break
        except (requests.RequestException, ValueError) as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e!s}")
            if attempt < max_retries - 1:
                continue
            logger.error(f"Error fetching Epic free games after {max_retries} attempts: {e!s}")
            return []

    elements = ((payload or {}).get("data", {}).get("Catalog", {}).get("searchStore", {}) or {}).get("elements", [])
    records: list[dict[str, Any]] = []

    for element in elements:
        title = element.get("title")
        if not title:
            continue
        promotions = element.get("promotions") or {}
        active = promotions.get("promotionalOffers") or []
        upcoming = promotions.get("upcomingPromotionalOffers") or []

        # Flatten the nested offer windows (each is a list of offer dicts)
        offers = [o for window in active for o in window] if active else [o for window in upcoming for o in window]
        if not offers:
            continue

        status = "active" if active else "upcoming"
        offer = offers[0]
        start_date = _parse_date(offer.get("startDate"))
        end_date = _parse_date(offer.get("endDate"))
        is_upcoming = status == "upcoming"

        summary_parts = []
        if is_upcoming:
            summary_parts.append("UPCOMING — will be free soon")
        if start_date:
            summary_parts.append(f"From: {start_date}")
        if end_date:
            summary_parts.append(f"Until: {end_date} (then it is paid again)")
        description = (element.get("description") or "").strip()
        if description:
            summary_parts.append(description[:200])

        records.append(
            {
                "title": f"{title} — 100% off (Epic)" if is_upcoming else f"{title} — Free now (Epic)",
                "link": _store_url(element),
                "published": start_date or datetime.now().isoformat(timespec="minutes"),
                "summary": " · ".join(summary_parts),
                "category": "epic_free",
                "source": "epic_games",
                "price": "€0.00",
                "deal_type": "Game",
                "expires_at": end_date,
                "status": status,
                "fetched_at": datetime.now().isoformat(timespec="minutes"),
            }
        )

    # Active promotions first, then upcoming
    records.sort(key=lambda r: (r["status"] != "active", r.get("expires_at") or ""))
    logger.info(f"Retrieved {len(records)} Epic free-game promotions")
    return records


def main() -> None:
    """Fetch Epic free games and persist them for the Scavenging tab."""
    logger.info("Starting Epic Free Games ETL")
    records = fetch_free_games()
    if not records:
        logger.warning("No Epic promotions retrieved — keeping any existing file untouched")
        return

    output_path = Path(get_project_root()) / OUTPUT_FILE
    ensure_directories([str(output_path.parent)])
    output_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Saved {len(records)} promotions to {output_path}")


if __name__ == "__main__":
    main()
