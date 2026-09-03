"""Lemmy communities ETL — self-hosting and homelab discussion pulse.

Fetches the native RSS feeds of two Lemmy communities on lemmy.world
(!selfhosted and !homelab, both ``?sort=New``) and merges them into a single
output file — a federated sibling to the reddit_unified r/SelfHosted +
r/homelab community pulse with a different (non-overlapping) community.
Feeds the Tech Radar tab's Self-Hosting column (T-082).

Design choice (single merged file, not the multi-file reddit_pulse shape):
both communities land in ONE ``lemmy_latest.json`` so the radar source entry
stays a plain ``file`` source; the merge/dedup happens here at save time and
one feed failing still saves the other (graceful degradation).

Usage:
    uv run python -m src.etl.news.news_get_lemmy

Output:
    data/news/lemmy_latest.json (+ timestamped snapshot)
"""

import calendar
import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.utils.retry import with_retry

logger = get_logger("LemmyETL")

# Community key -> native RSS feed (discovered from the community pages; the
# ?sort=New variant is the freshest ordering Lemmy offers).
FEEDS: dict[str, str] = {
    "selfhosted": "https://lemmy.world/feeds/c/selfhosted.xml?sort=New",
    "homelab": "https://lemmy.world/feeds/c/homelab.xml?sort=New",
}

# Per-community cap (feed order is newest-first except pinned posts).
MAX_ITEMS_PER_FEED = 25

# Merged cap: a bit above the radar's 25-per-source render cap so the two
# communities both keep depth in the unified "Todos" feed.
MAX_ITEMS = 30


def _fetch_community_feed(url: str) -> list[Any]:
    """Fetch and feed-parse one community RSS URL.

    Raises:
        requests.RequestException: propagated for the caller's per-feed
            graceful degradation (and tenacity retries before that).
    """
    response = requests.get(url, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    if feed.bozo:
        logger.warning(f"Feed parse warning for {url}: {feed.bozo_exception}")
    return list(feed.entries)


def _summarize(raw_html: str, community: str) -> str:
    """Build a compact engagement summary from Lemmy's description HTML.

    Lemmy descriptions read ``submitted by <a>user</a> to <a>community</a>
    519 points | 42 comments`` — extract the counters and badge the community
    fediverse-style instead of dumping the stripped markup.
    """
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = re.sub(r"\s+", " ", text).strip()
    score_match = re.search(r"(\d+)\s*points?", text)
    comments_match = re.search(r"(\d+)\s*comments?", text)
    if score_match or comments_match:
        parts = []
        if score_match:
            parts.append(f"⬆ {score_match.group(1)}")
        if comments_match:
            parts.append(f"💬 {comments_match.group(1)}")
        parts.append(f"!{community}@lemmy.world")
        return " · ".join(parts)
    return text


@with_retry
def fetch_lemmy() -> list[dict[str, Any]]:
    """Fetch and merge both Lemmy community feeds (newest first, deduped)."""
    records: list[tuple[float, dict[str, Any]]] = []
    seen_links: set[str] = set()
    for community, url in FEEDS.items():
        logger.info(f"Fetching Lemmy community {community} from {url}")
        try:
            entries = _fetch_community_feed(url)
        except requests.RequestException as exc:
            logger.error(f"Could not fetch the Lemmy {community} feed: {exc}")
            continue
        kept = 0
        for entry in entries[:MAX_ITEMS_PER_FEED]:
            link = entry.get("link", "")
            if not link or link in seen_links:
                continue  # cross-posted/duplicated link, keep once
            seen_links.add(link)
            published_struct = entry.get("published_parsed")
            epoch = calendar.timegm(published_struct) if published_struct else 0.0
            summary_html = entry.get("summary", "") if hasattr(entry, "summary") else ""
            records.append(
                (
                    epoch,
                    {
                        "source": "lemmy",
                        "source_category": "self_hosting",
                        "community": community,
                        "title": entry.get("title", ""),
                        "link": link,
                        "published": _parse_date(entry.get("published", "")),
                        "summary": _summarize(summary_html, community)[:500],
                        "author": entry.get("author", "") if hasattr(entry, "author") else "",
                        "guid": entry.get("id", ""),
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "platform": "lemmy.world",
                        "content_type": "forum_post",
                        "language": "en",
                        "region": "global",
                    },
                )
            )
            kept += 1
        logger.info(f"Retrieved {kept} items from the Lemmy {community} feed")
    records.sort(key=lambda pair: pair[0], reverse=True)
    merged = [record for _, record in records[:MAX_ITEMS]]
    logger.info(f"Merged {len(merged)} Lemmy items (newest first, cap {MAX_ITEMS})")
    return merged


def _parse_date(published_raw: str) -> str:
    """Parse an RSS date string to ISO format, falling back to the raw value."""
    if not published_raw:
        return ""
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(published_raw, fmt).isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(published_raw.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return published_raw


def save_lemmy_entries(entries: list[dict[str, Any]]) -> None:
    """Persist the Lemmy entries under ``data/news/``."""
    if not entries:
        logger.info("No Lemmy entries to save. Skipping.")
        return
    output_dir = os.path.join(get_project_root(), "data", "news")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "lemmy_latest.json")
    snapshot = os.path.join(output_dir, f"lemmy_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(entries)} Lemmy entries to {latest}")


def main() -> None:
    """Run the Lemmy communities ETL."""
    logger.info("Starting Lemmy RSS ETL")
    try:
        entries = fetch_lemmy()
        if not entries:
            logger.warning("No entries fetched from Lemmy. Exiting.")
            return
        save_lemmy_entries(entries)
        logger.info(f"Lemmy ETL complete: {len(entries)} posts.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"Lemmy ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
