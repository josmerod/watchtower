"""GiantBomb API ETL

Fetches latest games and reviews from GiantBomb API.
Requires API key via env GIANTBOMB_API_KEY or secrets/giantbomb.json.
Docs: https://www.giantbomb.com/api/
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import requests

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("GiantBombETL")


BASE = "https://www.giantbomb.com/api"


def _get_api_key() -> str | None:
    key = os.getenv("GIANTBOMB_API_KEY")
    if key:
        return key
    try:
        secrets_path = os.path.join(get_project_root(), "secrets", "giantbomb.json")
        with open(secrets_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("api_key")
    except Exception:
        pass
    # Fallback: parse .env in project root
    try:
        env_path = os.path.join(get_project_root(), ".env")
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("GIANTBOMB_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return None


def _request(path: str, params: dict[str, Any]) -> dict[str, Any] | None:
    key = _get_api_key()
    if not key:
        logger.info("GiantBomb API key not set; skipping.")
        return None
    headers = {"User-Agent": "Watchtower/1.0 (ETL)"}
    base_params = {"api_key": key, "format": "json"}
    try:
        resp = requests.get(f"{BASE}{path}", params=base_params | params, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.error(f"GiantBomb API {path} returned {resp.status_code}")
            return None
        return resp.json()
    except Exception as e:
        logger.error(f"GiantBomb API error {path}: {e}")
        return None


def fetch_games(limit: int = 50) -> list[dict[str, Any]]:
    params = {
        "sort": "date_added:desc",
        "limit": limit,
        "field_list": "name,site_detail_url,original_release_date,expected_release_year,platforms,deck,image,genres,date_added",
    }
    data = _request("/games/", params)
    items: list[dict[str, Any]] = []
    for g in (data or {}).get("results", []) or []:
        try:
            items.append(
                {
                    "title": g.get("name"),
                    "url": g.get("site_detail_url"),
                    "release_date": g.get("original_release_date"),
                    "expected_release_year": g.get("expected_release_year"),
                    "platforms": [p.get("name") for p in (g.get("platforms") or []) if isinstance(p, dict)],
                    "summary": g.get("deck"),
                    "genres": [p.get("name") for p in (g.get("genres") or []) if isinstance(p, dict)],
                    "image": (g.get("image") or {}).get("super_url"),
                    "date_added": g.get("date_added"),
                    "platform": "giantbomb",
                    "content_type": "game",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception:
            continue
    logger.info(f"Fetched {len(items)} GiantBomb games")
    return items


def fetch_reviews(limit: int = 30) -> list[dict[str, Any]]:
    params = {
        "sort": "publish_date:desc",
        "limit": limit,
        "field_list": "publish_date,score,deck,description,site_detail_url,platforms,game",
    }
    data = _request("/reviews/", params)
    items: list[dict[str, Any]] = []
    for r in (data or {}).get("results", []) or []:
        try:
            game = r.get("game") or {}
            items.append(
                {
                    "title": game.get("name") or "Review",
                    "url": r.get("site_detail_url"),
                    "score": r.get("score"),
                    "publish_date": r.get("publish_date"),
                    "summary": r.get("deck"),
                    "description": r.get("description"),
                    "platforms": [p.get("name") for p in (r.get("platforms") or []) if isinstance(p, dict)],
                    "game": game,
                    "platform": "giantbomb",
                    "content_type": "review",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception:
            continue
    logger.info(f"Fetched {len(items)} GiantBomb reviews")
    return items


def _save(kind: str, items: list[dict[str, Any]]) -> None:
    if not items:
        logger.info(f"No {kind} to save")
        return
    out_dir = os.path.join(get_project_root(), "data", "games")
    ensure_directories([out_dir])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(out_dir, f"giantbomb_{kind}_{ts}.json")
    latest_file = os.path.join(out_dir, f"giantbomb_{kind}_latest.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved GiantBomb {kind} latest and timestamped outputs")


def main():
    logger.info("Starting GiantBomb ETL")
    games = fetch_games()
    if games:
        _save("games", games)
    reviews = fetch_reviews()
    if reviews:
        _save("reviews", reviews)
    logger.info("GiantBomb ETL complete")


if __name__ == "__main__":
    main()
