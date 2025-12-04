"""IsThereAnyDeal API ETL

Fetches current best deals from IsThereAnyDeal API when API key is present.
If no API key is configured, exits gracefully.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import requests

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("IsThereAnyDealETL")


API_URL = "https://api.isthereanydeal.com/v01/deals/list/"
ENV_KEY = "API_ITAD_KEY"


def fetch_itad_deals(limit: int = 50) -> list[dict[str, Any]]:
    api_key = os.getenv(ENV_KEY)
    if not api_key:
        logger.info("IsThereAnyDeal API key not set; skipping.")
        return []

    params = {
        "key": api_key,
        "limit": limit,
        "region": "us",
        "country": "US",
        "shops": "steam,epic,gog,humblestore,greenmangaming,fanatical",
        "sort": "price_cut",
    }

    headers = {"User-Agent": "Watchtower/1.0 (ETL)"}
    try:
        resp = requests.get(API_URL, params=params, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.error(f"ITAD API returned {resp.status_code}")
            return []
        data = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch ITAD deals: {e}")
        return []

    deals: list[dict[str, Any]] = []
    for d in data.get("data", {}).get("list", []) or []:
        try:
            deals.append(
                {
                    "title": d.get("title", "Unknown Game"),
                    "url": d.get("urls", {}).get("game", ""),
                    "store_name": d.get("shop", {}).get("name", ""),
                    "original_price": d.get("price", {}).get("old", 0),
                    "current_price": d.get("price", {}).get("current", 0),
                    "discount_percentage": d.get("price", {}).get("cut", 0),
                    "platform": "isthereanydeal",
                    "content_type": "game_deal",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception:
            continue

    logger.info(f"Fetched {len(deals)} ITAD deals")
    return deals


def save_itad(deals: list[dict[str, Any]]) -> None:
    if not deals:
        logger.info("No ITAD deals to save")
        return

    output_dir = os.path.join(get_project_root(), "data", "games")
    ensure_directories([output_dir])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"isthereanydeal_{ts}.json")
    latest_file = os.path.join(output_dir, "isthereanydeal_latest.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(deals, f, indent=2, ensure_ascii=False)
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(deals, f, indent=2, ensure_ascii=False)
    logger.info("Saved ITAD latest and timestamped outputs")


def main():
    logger.info("Starting IsThereAnyDeal ETL")
    deals = fetch_itad_deals()
    if deals:
        save_itad(deals)
    logger.info("IsThereAnyDeal ETL complete")


if __name__ == "__main__":
    main()
