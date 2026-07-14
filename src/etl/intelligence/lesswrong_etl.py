"""LessWrong GraphQL ETL

Fetches articles from LessWrong using their GraphQL API.
Endpoint: https://www.lesswrong.com/graphql
Outputs canonical latest JSON under data/lesswrong/.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import requests

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("LessWrongETL")

GRAPHQL_URL = "https://www.lesswrong.com/graphql"


def fetch_lesswrong() -> list[dict[str, Any]]:
    logger.info("Fetching LessWrong data via GraphQL...")

    # Query for new posts with rich metadata
    query = """
    {
      posts(input: { terms: { view: "new", limit: 100 } }) {
        results {
          _id
          title
          pageUrl
          postedAt
          baseScore
          commentCount
          author
          user {
            displayName
            username
          }
          htmlBody
          tags {
            name
            slug
          }
        }
      }
    }
    """

    headers = {"Content-Type": "application/json", "User-Agent": "Watchtower/ETL/1.0"}

    try:
        response = requests.post(GRAPHQL_URL, json={"query": query}, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            logger.error(f"GraphQL Errors: {data['errors']}")
            return []

        posts = data.get("data", {}).get("posts", {}).get("results", [])
        logger.info(f"Retrieved {len(posts)} raw posts from GraphQL")

        entries = []
        for post in posts:
            # Construct absolute URL
            relative_url = post.get("pageUrl", "")
            if not relative_url.startswith("http"):
                link = f"https://www.lesswrong.com{relative_url}"
            else:
                link = relative_url

            # Parse date
            published_str = post.get("postedAt")
            published = None
            if published_str:
                try:
                    # Usually ISO format 2023-01-01T12:00:00.000Z
                    dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                    published = dt.isoformat()
                except Exception:
                    published = published_str

            # Extract tags
            tags_list = post.get("tags", [])
            tags = [t.get("name") for t in tags_list if t.get("name")]

            # Extract Author
            # LW API often uses 'user' for the author object in some views, or 'author' as a string/id
            # We try both
            author = "LessWrong"
            user_obj = post.get("user")
            if user_obj and isinstance(user_obj, dict):
                author = user_obj.get("displayName") or user_obj.get("username") or author
            elif post.get("author") and isinstance(post.get("author"), str):
                author = post.get("author")

            entry = {
                "source": "lesswrong",
                "title": post.get("title", ""),
                "link": link,
                "published": published,
                "summary": post.get("htmlBody", "")[:2000] + "..." if post.get("htmlBody") else "",  # Truncate summary for file size
                "author": author,
                "guid": post.get("_id", link),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "content_type": "article",
                "language": "en",
                # Rich metadata
                "score": post.get("baseScore", 0),
                "comments": post.get("commentCount", 0),
                "tags": tags,
                "metrics": {"views": post.get("viewCount"), "score": post.get("baseScore", 0), "comments": post.get("commentCount", 0)},  # Might be null, not in my query but useful if added
            }
            entries.append(entry)

        return entries

    except Exception as e:
        logger.error(f"Failed to fetch LessWrong GraphQL: {e}")
        return []


def save_lesswrong(entries: list[dict[str, Any]]) -> None:
    if not entries:
        logger.info("No LessWrong entries to save")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "lesswrong")
    ensure_directories([output_dir])

    # Save minimal latest file (lighter weight)
    # But keep full data in timestamped

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"lesswrong_{ts}.json")
    latest_json = os.path.join(output_dir, "lesswrong_latest.json")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(entries)} items to {latest_json}")


def main():
    logger.info("Starting LessWrong RSS ETL")
    entries = fetch_lesswrong()
    if entries:
        save_lesswrong(entries)
    logger.info("LessWrong ETL complete")


if __name__ == "__main__":
    main()
