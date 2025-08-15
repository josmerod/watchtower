# Use Case: Epic Free Games

"""Fetch current free games from Epic Games Store API and save to JSON and CSV."""

import os
from datetime import datetime, timezone

import pandas as pd
import requests

from src.utils.file_system import ensure_directories, get_project_root

# Add the project root to the path for imports
from src.utils.logging import get_logger

logger = get_logger("Epic_Free_Games_ETL")
EPIC_API_URL = (
    "https://store-site-backend-static.ak.epicgames.com"
    "/freeGamesPromotions?locale=es-ES&country=ES"
)


def get_epic_free_games() -> None:
    """
    Fetches current free games from Epic Games Store and saves them as JSON and CSV.

    Extracted values:
    - title: game title
    - id: game unique identifier
    - url: game store URL
    - start_date: ISO timestamp when the promotion starts
    - end_date: ISO timestamp when the promotion ends
    """
    logger.info("Fetching Epic Games free promotions")
    try:
        response = requests.get(EPIC_API_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
        logger.debug("Fetched data from Epic Games API")
    except Exception as e:
        logger.error(f"Error fetching Epic Games promotions: {e}")
        return

    elements = (
        data.get("data", {})
        .get("Catalog", {})
        .get("searchStore", {})
        .get("elements", [])
    )
    free_games: list[dict[str, str]] = []
    now = datetime.now(timezone.utc)

    for elem in elements:
        promotions = elem.get("promotions") or {}
        offers = promotions.get("promotionalOffers", []) + promotions.get(
            "upcomingPromotionalOffers", []
        )
        for offer_group in offers:
            for offer in offer_group.get("promotionalOffers", []):
                start = datetime.fromisoformat(
                    offer.get("startDate").replace("Z", "+00:00")
                )
                end = datetime.fromisoformat(
                    offer.get("endDate").replace("Z", "+00:00")
                )
                if start <= now <= end:
                    game_url = (
                        f"https://www.epicgames.com/store/p/{elem.get('productSlug')}"
                    )
                    free_games.append(
                        {
                            "title": elem.get("title"),
                            "id": elem.get("id"),
                            "url": game_url,
                            "start_date": start.isoformat(),
                            "end_date": end.isoformat(),
                        }
                    )
                    break

    df = pd.DataFrame(free_games)
    if not df.empty:
        df = df.sort_values(by="end_date")

    output_dir = os.path.join(get_project_root(), "data/games")
    ensure_directories(["data/games"])

    json_path = os.path.join(output_dir, "epic_free_games.json")
    csv_path = os.path.join(output_dir, "epic_free_games.csv")

    df.to_json(json_path, orient="records")
    logger.info(f"Epic free games saved to {json_path}")
    df.to_csv(csv_path, index=False, sep="|")
    logger.info(f"Epic free games saved to {csv_path}")


if __name__ == "__main__":
    get_epic_free_games()
