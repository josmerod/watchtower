# Use Case: Itch.io Trending Games

"""Fetch trending games from itch.io API and save to JSON and CSV."""

import sys
import os
from datetime import datetime, timezone
import requests
import pandas as pd

# Add the project root to the path for imports
from utils.logging import get_logger
from utils.file_system import ensure_directories, get_project_root

logger = get_logger("ItchIo_Trending_ETL")
ITC_API_URL = "https://itch.io/games?sort=trending&format=json"


def get_itchio_trending() -> None:
    """
    Fetches trending games from itch.io and saves them as JSON and CSV.

    Extracted values:
    - id: game unique identifier
    - title: game title
    - url: game URL on itch.io
    - fetched_at: ISO timestamp when the ETL was run
    """
    logger.info("Fetching itch.io trending games")
    try:
        response = requests.get(ITC_API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        games = data.get("games", [])
        logger.debug(f"Retrieved {len(games)} games from Itch.io API")
    except Exception as e:
        logger.error(f"Error fetching itch.io trending games: {e}")
        return

    trending_list: list[dict[str, str]] = []
    fetched_at = datetime.now(timezone.utc).isoformat()
    for game in games:
        trending_list.append({
            "id": game.get("id"),
            "title": game.get("title"),
            "url": game.get("url"),
            "fetched_at": fetched_at
        })

    df = pd.DataFrame(trending_list)
    
    # Only sort if DataFrame is not empty and has required columns
    if not df.empty and "title" in df.columns:
        df = df.sort_values(by="title")
    else:
        logger.warning("DataFrame is empty or missing 'title' column, skipping sort")

    output_dir = os.path.join(get_project_root(), "data/games")
    ensure_directories(["data/games"])

    json_path = os.path.join(output_dir, "itchio_trending.json")
    csv_path = os.path.join(output_dir, "itchio_trending.csv")

    df.to_json(json_path, orient="records")
    logger.info(f"Itch.io trending games saved to {json_path}")
    df.to_csv(csv_path, index=False, sep="|")
    logger.info(f"Itch.io trending games saved to {csv_path}")


if __name__ == "__main__":
    get_itchio_trending() 