"""Ollama Library ETL — newest models from the public ollama.com/library.

The library page is server-rendered HTML (verified stable across repeated
fetches — byte-identical bodies in the T-075 probe) with one ``<a>`` card per
model carrying name, description, capability tags, size variants, pull count
and a relative "Updated" date. There is no public JSON API, so the cards are
parsed with regexes anchored on stable markup (title div, description <p>,
the "Pulls"/"Updated" label spans).

The ETL parses every card, converts the relative updated dates to approximate
ISO timestamps and keeps the ``MAX_ITEMS`` newest models — feeding the Tech
Radar tab's "🦙 Ollama" source (category "Local LLM", T-075).

Usage:
    uv run python -m src.etl.ai_platforms.ollama_library_etl

Output:
    data/ai_platforms/ollama_library_latest.json (+ timestamped snapshot)
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from html import unescape
from typing import Any

import requests

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.retry import with_retry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

LIBRARY_URL = "https://ollama.com/library"

# Keep the persisted file lean — the radar column shows at most 25 per source.
MAX_ITEMS = 25

# Card markup anchors (validated against live HTML in the T-075 probe).
_CARD_RE = re.compile(r'<a\s+href="/library/([a-z0-9_.:\-]+)"[^>]*>(.*?)</a>', re.S)
_DESC_RE = re.compile(r'<p class="max-w-lg break-words[^"]*">(.*?)</p>', re.S)
_PULLS_RE = re.compile(r'<span\s*>([0-9.,]+[KM]?)</span>\s*<span class="hidden sm:flex">&nbsp;Pulls</span>')
_UPDATED_RE = re.compile(r'<span class="hidden sm:flex">Updated&nbsp;</span>\s*<span\s*>(.*?)</span>')
_TAG_RE = re.compile(r'rounded-md bg-indigo-50[^"]*"[^>]*>([a-z0-9_\-]+)</span>')
_SIZE_RE = re.compile(r'rounded-md bg-\[#ddf4ff\][^"]*"[^>]*>([a-z0-9._\-]+)</span>')

# Relative-date grammar seen on the page: "yesterday", "15 hours ago",
# "3 weeks ago", "10 months ago", "2 years ago".
_REL_RE = re.compile(r"^(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago$")
_UNIT_DAYS = {"second": 1 / 86400, "minute": 1 / 1440, "hour": 1 / 24, "day": 1, "week": 7, "month": 30, "year": 365}


def _strip_tags(fragment: str) -> str:
    """Strip tags, unescape entities and collapse whitespace from HTML."""
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def parse_pulls(raw: str) -> int:
    """Convert an Ollama pull count ("6,325", "940K", "118.9M") to an int."""
    cleaned = raw.replace(",", "").strip()
    try:
        value = float(cleaned.rstrip("KM"))
        multiplier = {"K": 1_000, "M": 1_000_000}.get(cleaned[-1:], 1)
        return int(value * multiplier)
    except (ValueError, AttributeError):
        return 0


def relative_to_iso(raw: str, now: datetime) -> str:
    """Convert a relative updated date to an approximate ISO timestamp.

    Months count as 30 days and years as 365 — the site only exposes this
    granularity, which is plenty for newest-first ordering.
    """
    cleaned = _strip_tags(raw).lower()
    if cleaned == "yesterday":
        return (now - timedelta(days=1)).isoformat()
    match = _REL_RE.match(cleaned)
    if match:
        amount, unit = match.groups()
        return (now - timedelta(days=int(amount) * _UNIT_DAYS[unit])).isoformat()
    return ""


def parse_library_html(html: str, now: datetime | None = None) -> list[dict[str, Any]]:
    """Parse the ollama.com/library HTML into model records, newest first.

    Every model card is parsed; records without a parsable updated date sort
    last (ties broken by pull count, most popular first) and the caller caps
    the list.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    records: list[dict[str, Any]] = []
    for name, card_html in _CARD_RE.findall(html):
        desc_match = _DESC_RE.search(card_html)
        description = _strip_tags(desc_match.group(1)) if desc_match else ""
        pulls_raw = _PULLS_RE.search(card_html)
        pulls = _strip_tags(pulls_raw.group(1)) if pulls_raw else ""
        updated_raw = _UPDATED_RE.search(card_html)
        updated_relative = _strip_tags(updated_raw.group(1)) if updated_raw else ""
        published = relative_to_iso(updated_relative, now)
        url = f"https://ollama.com/library/{name}"
        tags = _TAG_RE.findall(card_html)
        sizes = _SIZE_RE.findall(card_html)
        summary_bits = [bit for bit in [description, f"⬇ {pulls} pulls" if pulls else "", ", ".join(sizes)] if bit]
        records.append(
            {
                "source": "ollama_library",
                "source_category": "local_llm",
                "title": name,
                "name": name,
                "link": url,
                "url": url,
                "description": description,
                "summary": " · ".join(summary_bits),
                "published": published,
                "updated_relative": updated_relative,
                "pulls": pulls,
                "pulls_count": parse_pulls(pulls),
                "tags": tags,
                "sizes": sizes,
                "platform": "ollama",
                "content_type": "model",
                "language": "en",
                "region": "global",
                "fetched_at": now.isoformat(),
            }
        )
    records.sort(key=lambda r: (r["published"] or "", r["pulls_count"]), reverse=True)
    logger.info(f"Parsed {len(records)} Ollama library cards")
    return records


@with_retry
def fetch_ollama_library() -> list[dict[str, Any]]:
    """Fetch the Ollama library page and return the newest model records."""
    logger.info(f"Fetching Ollama library from {LIBRARY_URL}")
    try:
        response = requests.get(LIBRARY_URL, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error(f"Could not fetch the Ollama library page: {exc}")
        return []
    records = parse_library_html(response.text)
    if not records:
        logger.warning("Ollama library page parsed to zero cards — markup may have changed.")
    return records[:MAX_ITEMS]


def save_ollama_library(records: list[dict[str, Any]]) -> bool:
    """Persist the newest models under ``data/ai_platforms/``.

    Returns True when files were written; an empty run writes nothing so the
    previous latest snapshot (last-good) survives markup changes.
    """
    if not records:
        logger.info("No Ollama library records to save. Skipping.")
        return False
    output_dir = os.path.join(get_project_root(), "data", "ai_platforms")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "ollama_library_latest.json")
    snapshot = os.path.join(output_dir, f"ollama_library_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(records)} Ollama models to {latest}")
    return True


def main() -> None:
    """Run the Ollama library ETL."""
    logger.info("Starting Ollama library ETL")
    try:
        records = fetch_ollama_library()
        if not records:
            logger.warning("No records fetched from the Ollama library. Exiting.")
            return
        save_ollama_library(records)
        logger.info(f"Ollama library ETL complete: {len(records)} newest models.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"Ollama library ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
