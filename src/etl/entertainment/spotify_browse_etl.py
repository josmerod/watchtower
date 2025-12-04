"""Spotify Browse ETL

Fetches featured playlists and new releases using Spotify Web API.
Requires `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` env vars.
If credentials missing, exits gracefully.
"""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from typing import Any

import requests

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("SpotifyBrowseETL")


TOKEN_URL = "https://accounts.spotify.com/api/token"
BROWSE_PLAYLISTS_URL = "https://api.spotify.com/v1/browse/featured-playlists"
NEW_RELEASES_URL = "https://api.spotify.com/v1/browse/new-releases"


def _get_token() -> str | None:
    cid = os.getenv("SPOTIFY_CLIENT_ID")
    secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    # Fallback to secrets file if env not set
    if not cid or not secret:
        try:
            secrets_path = os.path.join(get_project_root(), "secrets", "spotify.json")
            with open(secrets_path, encoding="utf-8") as f:
                data = json.load(f)
            cid = cid or data.get("client_id")
            secret = secret or data.get("client_secret")
        except Exception:
            pass
    # Fallback to .env if still not set
    if not cid or not secret:
        try:
            env_path = os.path.join(get_project_root(), ".env")
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("SPOTIFY_CLIENT_ID="):
                        cid = cid or line.split("=", 1)[1].strip().strip('"').strip("'")
                    if line.startswith("SPOTIFY_CLIENT_SECRET="):
                        secret = secret or line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    if not cid or not secret:
        logger.info("Spotify credentials not set; skipping.")
        return None
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        resp = requests.post(
            TOKEN_URL,
            headers=headers,
            data={"grant_type": "client_credentials"},
            timeout=30,
        )
        if resp.status_code != 200:
            logger.error(f"Spotify token error {resp.status_code}: {resp.text[:120]}")
            return None
        return resp.json().get("access_token")
    except Exception as e:
        logger.error(f"Failed to get Spotify token: {e}")
        return None


def fetch_spotify() -> dict[str, list[dict[str, Any]]]:
    token = _get_token()
    if not token:
        return {"playlists": [], "new_releases": []}
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "Watchtower/1.0"}
    out: dict[str, list[dict[str, Any]]] = {"playlists": [], "new_releases": []}
    try:
        r1 = requests.get(
            BROWSE_PLAYLISTS_URL,
            headers=headers,
            params={"country": "US", "limit": 20},
            timeout=30,
        )
        if r1.status_code == 200:
            for p in r1.json().get("playlists", {}).get("items", []) or []:
                out["playlists"].append(
                    {
                        "name": p.get("name"),
                        "url": p.get("external_urls", {}).get("spotify", ""),
                        "owner": p.get("owner", {}).get("display_name", ""),
                        "tracks": p.get("tracks", {}).get("total", 0),
                        "image": (p.get("images", [{}])[0] or {}).get("url", ""),
                        "platform": "spotify",
                        "content_type": "playlist",
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
        else:
            logger.error(f"Spotify playlists API {r1.status_code}")
        r2 = requests.get(
            NEW_RELEASES_URL,
            headers=headers,
            params={"country": "US", "limit": 20},
            timeout=30,
        )
        if r2.status_code == 200:
            for a in r2.json().get("albums", {}).get("items", []) or []:
                out["new_releases"].append(
                    {
                        "name": a.get("name"),
                        "url": a.get("external_urls", {}).get("spotify", ""),
                        "release_date": a.get("release_date"),
                        "artists": [ar.get("name") for ar in a.get("artists", [])],
                        "image": (a.get("images", [{}])[0] or {}).get("url", ""),
                        "platform": "spotify",
                        "content_type": "album",
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
        else:
            logger.error(f"Spotify new releases API {r2.status_code}")
    except Exception as e:
        logger.error(f"Spotify API error: {e}")
    return out


def save_spotify(data: dict[str, list[dict[str, Any]]]) -> None:
    if not data.get("playlists") and not data.get("new_releases"):
        logger.info("No Spotify data to save")
        return
    out_dir = os.path.join(get_project_root(), "data", "entertainment")
    ensure_directories([out_dir])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(out_dir, f"spotify_browse_{ts}.json")
    latest_file = os.path.join(out_dir, "spotify_browse_latest.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Saved Spotify browse latest and timestamped outputs")


def main():
    logger.info("Starting Spotify Browse ETL")
    data = fetch_spotify()
    save_spotify(data)
    logger.info("Spotify Browse ETL complete")


if __name__ == "__main__":
    main()
