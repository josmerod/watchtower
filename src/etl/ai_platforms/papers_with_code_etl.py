"""Papers with Code API ETL

Fetches latest papers and associated code repositories using the public API.
Saves canonical latest JSON under data/ai_platforms/.

Note: For simplicity and to avoid rate limits/auth, this ETL uses a basic
endpoint for recent papers and keeps fields minimal but consistent with
existing AI platform data patterns.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger


logger = get_logger("PapersWithCodeETL")


BASE_URL = "https://paperswithcode.com/api/v1/"


def fetch_recent_papers(page_size: int = 50) -> List[Dict[str, Any]]:
    url = f"{BASE_URL}papers/"
    params = {"items_per_page": page_size, "page": 1, "ordering": "-published"}
    headers = {"User-Agent": "Watchtower/1.0 (ETL)"}

    results: List[Dict[str, Any]] = []
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.error(f"Papers with Code API returned status {resp.status_code}")
            return results
        data = resp.json()
        for item in data.get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url_abs", item.get("url", "")),
                    "paper_url": item.get("url_abs", ""),
                    "authors": item.get("authors", []),
                    "published": item.get("published", None),
                    "conference": item.get("conference", ""),
                    "arxiv_id": item.get("arxiv_id", ""),
                    "repository": item.get("repository", {}),
                    "tasks": [t.get("name") for t in item.get("tasks", [])],
                    "methods": [m.get("name") for m in item.get("methods", [])],
                    "datasets": [d.get("name") for d in item.get("datasets", [])],
                    "platform": "paperswithcode",
                    "content_type": "research_paper",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    except Exception as e:
        logger.error(f"Failed to fetch Papers with Code data: {e}")
        return results

    logger.info(f"Fetched {len(results)} recent papers from Papers with Code")
    return results


def save_papers(entries: List[Dict[str, Any]]) -> None:
    if not entries:
        logger.info("No Papers with Code entries to save")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "ai_platforms")
    ensure_directories([output_dir])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"paperswithcode_{ts}.json")
    latest_json = os.path.join(output_dir, "paperswithcode_latest.json")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    logger.info("Saved Papers with Code latest and timestamped outputs")


def main():
    logger.info("Starting Papers with Code ETL")
    entries = fetch_recent_papers()
    if entries:
        save_papers(entries)
    logger.info("Papers with Code ETL complete")


if __name__ == "__main__":
    main()


