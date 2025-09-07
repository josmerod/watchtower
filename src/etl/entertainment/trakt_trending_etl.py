"""Trakt.tv Trending ETL

Fetches trending movies and shows from Trakt.tv public API. Requires client ID.
If `TRAKT_CLIENT_ID` env var is missing, exits gracefully.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger


logger = get_logger("TraktTrendingETL")


BASE_URL = "https://api.trakt.tv/"
ENV_KEY = "TRAKT_CLIENT_ID"
SECRETS_FILE = "trakt.json"


def fetch_trending(kind: str = "movies", limit: int = 50) -> List[Dict[str, Any]]:
    client_id = os.getenv(ENV_KEY)
    if not client_id:
        # Fallback to secrets file
        try:
            secrets_path = os.path.join(get_project_root(), "secrets", SECRETS_FILE)
            with open(secrets_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            client_id = data.get("client_id")
        except Exception:
            client_id = None
        # Fallback to .env
        if not client_id:
            try:
                env_path = os.path.join(get_project_root(), ".env")
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if line.startswith("TRAKT_CLIENT_ID="):
                            client_id = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                client_id = None
    if not client_id:
        logger.info("TRAKT_CLIENT_ID not set; skipping Trakt ETL.")
        return []

    url = f"{BASE_URL}{kind}/trending"
    headers = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": client_id,
        "User-Agent": "Watchtower/1.0",
    }
    params = {"page": 1, "limit": limit}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            logger.error(f"Trakt API returned {resp.status_code}")
            return []
        data = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch Trakt trending: {e}")
        return []

    items: List[Dict[str, Any]] = []
    for it in data or []:
        try:
            entry = it.get("movie") or it.get("show") or {}
            items.append(
                {
                    "title": entry.get("title", "Unknown"),
                    "year": entry.get("year"),
                    "ids": entry.get("ids", {}),
                    "watchers": it.get("watchers", 0),
                    "content_type": kind[:-1],
                    "platform": "trakt",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception:
            continue
    logger.info(f"Fetched {len(items)} Trakt {kind} trending")
    return items


def save_trakt(kind: str, items: List[Dict[str, Any]]) -> None:
    if not items:
        logger.info("No Trakt items to save")
        return
    output_dir = os.path.join(get_project_root(), "data", "entertainment")
    ensure_directories([output_dir])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"trakt_{kind}_{ts}.json")
    latest_file = os.path.join(output_dir, f"trakt_{kind}_latest.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved Trakt {kind} latest and timestamped outputs")


def main():
    logger.info("Starting Trakt Trending ETL")
    movies = fetch_trending("movies")
    if movies:
        save_trakt("movies", movies)
    shows = fetch_trending("shows")
    if shows:
        save_trakt("shows", shows)
    logger.info("Trakt Trending ETL complete")


if __name__ == "__main__":
    main()

