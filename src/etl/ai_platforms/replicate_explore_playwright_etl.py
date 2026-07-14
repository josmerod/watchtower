"""Replicate Explore Playwright ETL

Scrapes Replicate Explore page for featured/popular/official models using Playwright.
No API key needed. Writes a latest JSON file under data/ai_platforms/.

Reference: https://replicate.com/explore
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from playwright.sync_api import sync_playwright

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("ReplicateExploreETL")


EXPLORE_URL = "https://replicate.com/explore"


def _normalize_model_link(href: str) -> str | None:
    # Expect paths like /owner/model
    if not href or not href.startswith("/"):
        return None
    parts = href.strip("/").split("/")
    if len(parts) < 2:
        return None
    owner, model = parts[0], parts[1]
    if not owner or not model:
        return None
    return f"{owner}/{model}"


def fetch_replicate_explore(max_items: int = 100) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    logger.info(f"Fetching Replicate Explore page: {EXPLORE_URL}")

    try:
        with sync_playwright() as p:
            browserless_ws = os.getenv("BROWSERLESS_ENDPOINT")
            if browserless_ws:
                logger.info(f"Connecting to remote browser at {browserless_ws}")
                browser = p.chromium.connect_over_cdp(browserless_ws)
            else:
                logger.info("Launching local browser")
                browser = p.chromium.launch(headless=True)

            context = browser.new_context()
            page = context.new_page()
            page.goto(EXPLORE_URL, wait_until="networkidle", timeout=60000)

            # Scroll to load more content
            for _ in range(6):
                page.mouse.wheel(0, 1000)
                page.wait_for_timeout(800)

            # Collect model links from anchors
            anchors = page.query_selector_all("a[href*='/']")
            for a in anchors:
                try:
                    href = a.get_attribute("href") or ""
                    if not href.startswith("/"):
                        continue
                    norm = _normalize_model_link(href)
                    if not norm or norm in seen:
                        continue
                    # Visible name text
                    name_text = (a.inner_text() or "").strip()
                    # Basic filter: avoid menu and unrelated links
                    if "/explore" in href or name_text.lower() in {
                        "explore",
                        "blog",
                        "docs",
                        "pricing",
                    }:
                        continue
                    seen.add(norm)
                    items.append(
                        {
                            "qualified_name": norm,
                            "display": name_text,
                            "url": f"https://replicate.com/{norm}",
                            "platform": "replicate",
                            "content_type": "model",
                            "fetched_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    if len(items) >= max_items:
                        break
                except Exception:
                    continue

            page.close()
            context.close()
            browser.close()
    except Exception as e:
        logger.error(f"Error scraping Replicate Explore: {e}")
        return []

    logger.info(f"Collected {len(items)} Replicate models from Explore")
    return items


def save_replicate_explore(items: list[dict[str, Any]]) -> None:
    if not items:
        logger.info("No Replicate explore items to save")
        return
    out_dir = os.path.join(get_project_root(), "data", "ai_platforms")
    ensure_directories([out_dir])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(out_dir, f"replicate_explore_{ts}.json")
    latest_file = os.path.join(out_dir, "replicate_explore_latest.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    logger.info("Saved Replicate explore latest and timestamped outputs")


def main():
    logger.info("Starting Replicate Explore ETL")
    items = fetch_replicate_explore()
    save_replicate_explore(items)
    logger.info("Replicate Explore ETL complete")


if __name__ == "__main__":
    main()
