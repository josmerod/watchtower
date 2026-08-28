"""CoinGecko markets ETL — top cryptocurrencies, keyless (T-043 v1).

Fetches the top-50 coins by market cap from CoinGecko's free REST API (no
key): price, market cap, volume, and 24h/7d changes. Feeds the new
"📈 Markets" dashboard tab — Watchtower's first financial-capability tab.

Usage:
    uv run python -m src.etl.markets.coingecko_etl

Output:
    data/markets/coingecko_latest.json (+ timestamped snapshot)
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

import requests

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.utils.retry import with_retry

logger = get_logger("CoinGeckoETL")

API_URL = "https://api.coingecko.com/api/v3/coins/markets"
PER_PAGE = 50


@with_retry
def fetch_markets() -> list[dict[str, Any]]:
    """Fetch and normalize the top coins by market cap."""
    records: list[dict[str, Any]] = []
    logger.info(f"Fetching CoinGecko markets from {API_URL}")
    try:
        response = requests.get(
            API_URL,
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": PER_PAGE,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "24h,7d",
            },
            headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()
        coins = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.error(f"Could not fetch CoinGecko markets: {exc}")
        return records

    for coin in coins:
        if not coin.get("id"):
            continue
        records.append(
            {
                "source": "coingecko",
                "source_category": "crypto_markets",
                "id": coin["id"],
                "rank": coin.get("market_cap_rank"),
                "name": coin.get("name", ""),
                "symbol": str(coin.get("symbol", "")).upper(),
                "price_usd": coin.get("current_price"),
                "market_cap_usd": coin.get("market_cap"),
                "volume_24h_usd": coin.get("total_volume"),
                "change_24h_pct": coin.get("price_change_percentage_24h_in_currency", coin.get("price_change_percentage_24h")),
                "change_7d_pct": coin.get("price_change_percentage_7d_in_currency"),
                "high_24h_usd": coin.get("high_24h"),
                "low_24h_usd": coin.get("low_24h"),
                "ath_usd": coin.get("ath"),
                "ath_change_pct": coin.get("ath_change_percentage"),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "coingecko",
                "content_type": "market_quote",
                "region": "global",
            }
        )
    records.sort(key=lambda r: r.get("rank") or 999)
    logger.info(f"Retrieved {len(records)} coins from CoinGecko")
    return records


def save_markets(records: list[dict[str, Any]]) -> None:
    """Persist the market records under ``data/markets/``."""
    if not records:
        logger.info("No CoinGecko records to save. Skipping.")
        return
    output_dir = os.path.join(get_project_root(), "data", "markets")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "coingecko_latest.json")
    snapshot = os.path.join(output_dir, f"coingecko_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(records)} coins to {latest}")


def main() -> None:
    """Run the CoinGecko markets ETL."""
    logger.info("Starting CoinGecko markets ETL")
    try:
        records = fetch_markets()
        if not records:
            logger.warning("No records fetched from CoinGecko. Exiting.")
            return
        save_markets(records)
        logger.info(f"CoinGecko markets ETL complete: {len(records)} coins.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"CoinGecko markets ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
