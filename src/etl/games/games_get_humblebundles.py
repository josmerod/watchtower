# src/etl/games/games_get_humblebundles.py
import os
import sys
import json
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories, get_project_root

logger = get_logger("HumbleBundleETL")


def get_humblebundle_data() -> List[Dict[str, Any]]:
    """
    Fetches active game bundles from Humble Bundle via their public JSON endpoint.

    Returns:
        List of bundle metadata dictionaries.
    """
    url = "https://www.humblebundle.com/v2/app/bundles?window_size=100"
    logger.info(f"Requesting Humble Bundle data from {url}")
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    bundles = data.get("bundles", [])
    results: List[Dict[str, Any]] = []
    for bundle in bundles:
        title = bundle.get("human_name")
        relative_url = bundle.get("human_url", "")
        link = f"https://www.humblebundle.com{relative_url}"
        price = bundle.get("human_price")
        end_ts = bundle.get("end_date")
        end_date = datetime.fromtimestamp(end_ts, tz=timezone.utc) if end_ts else None

        # Extract included games
        items = bundle.get("items", [])
        games = [item.get("human_name") for item in items if item.get("type") == "game"]

        results.append({
            "title": title,
            "link": link,
            "end_date": end_date.isoformat() if end_date else None,
            "price": price,
            "games": games,
        })
    logger.info(f"Retrieved {len(results)} bundles from Humble Bundle")
    return results


def save_humblebundle_bundles(bundles: List[Dict[str, Any]]) -> None:
    """
    Saves Humble Bundle data to JSON and CSV in the data/games directory.

    Args:
        bundles: List of bundle metadata dictionaries.
    """
    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data/games")
    ensure_directories(["data/games"])

    json_path = os.path.join(output_dir, "humblebundles.json")
    csv_path = os.path.join(output_dir, "humblebundles.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(bundles, f, indent=2)

    import pandas as pd  # type: ignore
    pd.DataFrame(bundles).to_csv(csv_path, index=False)

    logger.info(f"Saved Humble Bundle data to {json_path} and {csv_path}")


def main() -> None:
    """
    Main entry point for the Humble Bundle ETL process.
    """
    bundles = get_humblebundle_data()
    save_humblebundle_bundles(bundles)


if __name__ == "__main__":
    logger.info("Starting Humble Bundle ETL process")
    main()
    logger.info("Humble Bundle ETL process completed") 