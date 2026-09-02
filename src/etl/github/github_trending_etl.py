"""GitHub Trending ETL — repos trending today on github.com/trending.

The trending page is server-rendered HTML with one ``article.Box-row`` card
per repository carrying the repo path, description, language, total stars and
a "N stars today" counter. There is no JSON API for the trending view (the
api.github.com search used by news_get_gittrends.py is a different signal),
so the cards are parsed with BeautifulSoup.

Selectors are deliberately structure/attribute-based (``h2 a``, ``p``,
``[itemprop=programmingLanguage]``, ``a[href$='/stargazers']``) — the T-078
probe caught GitHub A/B-testing ``tmp-``-prefixed utility classes, so exact
class names are not stable anchors. Verified stable in the probe: two
fetches 20 s apart parsed 14/14 identical repos.

Feeds the Tech Radar tab's "🐙 GH Trending" source (category "Open Source",
T-078).

Usage:
    uv run python -m src.etl.github.github_trending_etl

Output:
    data/github/github_trending_latest.json (+ timestamped snapshot)
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.retry import with_retry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TRENDING_URL = "https://github.com/trending"

# Keep the persisted file lean — the radar column shows at most 25 per source
# (and the page itself rarely lists more).
MAX_ITEMS = 25

# "3,128 stars today" / "210 stars this week" — amount captured separately so
# the period wording can change without breaking the count.
_STARS_TODAY_RE = re.compile(r"^([\d,]+)\s+stars?\s+today", re.IGNORECASE)

# Truncate the description in the display summary (chars).
_SUMMARY_DESC_MAX = 120


def _parse_count(raw: str) -> int:
    """Convert a comma-grouped star count ("3,128") to an int."""
    try:
        return int(raw.replace(",", "").strip())
    except ValueError:
        return 0


def _stars_today(row: Any) -> int:
    """Extract the "N stars today" counter from one trending card.

    Scans the card's spans by text instead of class names — the counter span
    (``float-sm-right`` in today's markup) is the only text matching the
    pattern, and class names are A/B-tested by GitHub.
    """
    for span in row.find_all("span"):
        match = _STARS_TODAY_RE.match(span.get_text(" ", strip=True))
        if match:
            return _parse_count(match.group(1))
    return 0


def parse_trending_html(html: str, now: datetime | None = None) -> list[dict[str, Any]]:
    """Parse the github.com/trending HTML into repo records, page order kept.

    The page lists trending repos in rank order, so feed order is preserved;
    every record is "today" news, hence a shared ``published`` of the fetch
    time keeps the unified radar feed correctly interleaved.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    records: list[dict[str, Any]] = []
    soup = BeautifulSoup(html, "html.parser")
    for row in soup.select("article.Box-row"):
        title_link = row.select_one("h2 a[href]")
        if title_link is None or not title_link.get("href"):
            continue
        repo = str(title_link["href"]).strip("/")
        if "/" not in repo:  # guard against stray links
            continue
        desc_el = row.select_one("p")
        description = desc_el.get_text(" ", strip=True) if desc_el else ""
        lang_el = row.select_one("[itemprop='programmingLanguage']")
        language = lang_el.get_text(strip=True) if lang_el else ""
        stars_el = row.select_one("a[href$='/stargazers']")
        total_stars = _parse_count(stars_el.get_text(" ", strip=True)) if stars_el else 0
        stars_today = _stars_today(row)
        url = f"https://github.com/{repo}"
        summary_bits = [f"⭐ {stars_today:,} today" if stars_today else "", language, description[:_SUMMARY_DESC_MAX]]
        records.append(
            {
                "source": "github_trending",
                "source_category": "open_source",
                "title": repo,
                "repo": repo,
                "link": url,
                "url": url,
                "description": description,
                "language": language,
                "stars_today": stars_today,
                "total_stars": total_stars,
                "published": now.isoformat(),
                "summary": " · ".join(bit for bit in summary_bits if bit),
                "platform": "github",
                "content_type": "trending_repo",
                "region": "global",
                "fetched_at": now.isoformat(),
            }
        )
        if len(records) >= MAX_ITEMS:
            break
    logger.info(f"Parsed {len(records)} GitHub trending repos")
    return records


@with_retry
def fetch_github_trending() -> list[dict[str, Any]]:
    """Fetch the GitHub trending page and return the repo records."""
    logger.info(f"Fetching GitHub trending from {TRENDING_URL}")
    try:
        response = requests.get(TRENDING_URL, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error(f"Could not fetch the GitHub trending page: {exc}")
        return []
    records = parse_trending_html(response.text)
    if not records:
        logger.warning("GitHub trending page parsed to zero rows — markup may have changed.")
    return records


def save_github_trending(records: list[dict[str, Any]]) -> None:
    """Persist the trending repos under ``data/github/`` (empty run keeps last-good)."""
    if not records:
        logger.info("No GitHub trending records to save. Skipping.")
        return
    output_dir = os.path.join(get_project_root(), "data", "github")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "github_trending_latest.json")
    snapshot = os.path.join(output_dir, f"github_trending_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(records)} GitHub trending repos to {latest}")


def main() -> None:
    """Run the GitHub trending ETL."""
    logger.info("Starting GitHub trending ETL")
    try:
        records = fetch_github_trending()
        if not records:
            logger.warning("No records fetched from GitHub trending. Exiting.")
            return
        save_github_trending(records)
        logger.info(f"GitHub trending ETL complete: {len(records)} repos.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"GitHub trending ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
