"""Khan Academy API ETL

Fetches selected free course content metadata from Khan Academy's public endpoints.
Outputs canonical latest JSON under data/courses/.

Note: Khan Academy API is partially public/undocumented. This ETL uses
the topic tree endpoint which is accessible without auth for high-level content.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import requests

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("KhanAcademyETL")


TOPIC_TREE_URL = "https://www.khanacademy.org/api/v1/topictree"


def _flatten_topics(node: dict[str, Any], results: list[dict[str, Any]], path: list[str] | None = None) -> None:
    path = path or []
    kind = node.get("kind")
    title = node.get("title") or node.get("translated_title") or ""
    url = node.get("ka_url", "")

    if kind in {"Video", "Article", "Exercise"}:
        results.append(
            {
                "title": title,
                "url": (f"https://www.khanacademy.org{url}" if url.startswith("/") else url),
                "content_kind": kind,
                "subject_path": "/".join(path),
                "platform": "khan_academy",
                "language": node.get("translated_youtube_lang", "en"),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    # Recurse
    for child in node.get("children", []) or []:
        child_title = child.get("title") or child.get("translated_title") or ""
        _flatten_topics(child, results, path + ([title] if title else []))


def fetch_khan_academy(limit: int = 500) -> list[dict[str, Any]]:
    headers = {"User-Agent": "Watchtower/1.0 (ETL)"}
    try:
        resp = requests.get(TOPIC_TREE_URL, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch Khan Academy topic tree: {e}")
        return []

    results: list[dict[str, Any]] = []
    _flatten_topics(data, results)
    # Keep a reasonable cap
    if len(results) > limit:
        results = results[:limit]
    logger.info(f"Flattened {len(results)} Khan Academy content items")
    return results


def save_khan(entries: list[dict[str, Any]]) -> None:
    if not entries:
        logger.info("No Khan Academy entries to save")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "courses")
    ensure_directories([output_dir])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"khan_academy_{ts}.json")
    latest_json = os.path.join(output_dir, "khan_academy_latest.json")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    logger.info("Saved Khan Academy latest and timestamped outputs")


def main():
    logger.info("Starting Khan Academy ETL")
    entries = fetch_khan_academy()
    if entries:
        save_khan(entries)
    logger.info("Khan Academy ETL complete")


if __name__ == "__main__":
    main()
