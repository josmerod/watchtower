"""Replicate Models ETL

Fetches public trending models from Replicate API. Requires `REPLICATE_API_TOKEN`.
If token missing, exits gracefully.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import requests

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("ReplicateModelsETL")


BASE_URL = "https://api.replicate.com/v1/collections/trending"
ENV_KEY = "REPLICATE_API_TOKEN"


def fetch_replicate_trending() -> list[dict[str, Any]]:
    token = os.getenv(ENV_KEY)
    if not token:
        logger.info("REPLICATE_API_TOKEN not set; skipping Replicate ETL.")
        return []
    headers = {"Authorization": f"Token {token}", "User-Agent": "Watchtower/1.0"}
    try:
        resp = requests.get(BASE_URL, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.error(f"Replicate API returned {resp.status_code}")
            return []
        data = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch Replicate models: {e}")
        return []

    items: list[dict[str, Any]] = []
    for it in data.get("results", []) or []:
        try:
            model = it.get("model", {})
            items.append(
                {
                    "name": model.get("name", ""),
                    "owner": model.get("owner", ""),
                    "url": model.get("url", ""),
                    "tags": it.get("tags", []),
                    "platform": "replicate",
                    "content_type": "model",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception:
            continue
    logger.info(f"Fetched {len(items)} Replicate trending models")
    return items


def save_replicate(items: list[dict[str, Any]]) -> None:
    if not items:
        logger.info("No Replicate models to save")
        return
    output_dir = os.path.join(get_project_root(), "data", "ai_platforms")
    ensure_directories([output_dir])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"replicate_trending_{ts}.json")
    latest_file = os.path.join(output_dir, "replicate_trending_latest.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    logger.info("Saved Replicate trending latest and timestamped outputs")


def main():
    logger.info("Starting Replicate Models ETL")
    items = fetch_replicate_trending()
    if items:
        save_replicate(items)
    logger.info("Replicate Models ETL complete")


if __name__ == "__main__":
    main()
