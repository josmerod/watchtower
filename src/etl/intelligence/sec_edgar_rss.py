"""SEC EDGAR ATOM ETL

Parses SEC EDGAR company filings ATOM feed (public feed) for intelligence.
Default feed: recent filings.
Outputs canonical latest JSON under data/intelligence/.

"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any
from html.parser import HTMLParser

import feedparser
import urllib.error
import urllib.request

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.utils.retry import fetch_with_retry

logger = get_logger("SECEDGARETL")

# SEC.gov ATOM feed for current filings
FEED_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&company=&dateb=&owner=include&count=40&output=atom"
# SEC requires a proper User-Agent header
HEADERS = {"User-Agent": "Watchtower/1.0 (contact@example.org)"}


class MLStripper(HTMLParser):
    """Utility class to strip HTML tags from text."""

    def __init__(self) -> None:
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text: list[str] = []

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    def get_data(self) -> str:
        return ''.join(self.text)


def strip_tags(html: str) -> str:
    """Remove HTML tags from a string."""
    if not html:
        return ""
    stripper = MLStripper()
    stripper.feed(html)
    return stripper.get_data()


def _parse_date(date_str: str | None) -> str | None:
    """Parse a date string into ISO format."""
    if not date_str:
        return None
    try:
        # Try ISO format first
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
    except Exception:
        try:
            return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z").isoformat()
        except Exception:
            # Fallback: return original string
            return date_str


def _parse_title(title: str) -> dict[str, str]:
    """
    Parse SEC EDGAR entry title to extract form_type, company_name, CIK, filing_type.
    Expected format: "FORM_TYPE - COMPANY_NAME (CIK) (FILING_TYPE)"
    Example: "D - Juniper Health, Inc. (0001809372) (Filer)"
    Returns dict with keys: form_type, company_name, cik, filing_type.
    If parsing fails, returns empty strings.
    """
    # Regex to capture: form_type - company_name (cik) (filing_type)
    # form_type can contain spaces, hyphens, slashes (e.g., "13F-HR", "SC 14D-9", "10-K/A")
    pattern = r'^(.+?)\s+-\s+(.+?)\s+\((\d+)\)\s+\(([^)]+)\)\s*$'
    match = re.match(pattern, title.strip())
    if match:
        form_type, company_name, cik, filing_type = match.groups()
        return {
            "form_type": form_type.strip(),
            "company_name": company_name.strip(),
            "cik": cik.strip(),
            "filing_type": filing_type.strip(),
        }
    # Fallback: try to extract at least form_type and company_name
    parts = title.split(' - ', 1)
    if len(parts) == 2:
        form_type = parts[0].strip()
        rest = parts[1].strip()
        company_match = re.match(r'^(.+?)\s*\((\d+)\)\s*\((.+)\)$', rest)
        if company_match:
            company_name, cik, filing_type = company_match.groups()
            return {
                "form_type": form_type,
                "company_name": company_name.strip(),
                "cik": cik.strip(),
                "filing_type": filing_type.strip(),
            }
        return {
            "form_type": form_type,
            "company_name": rest,
            "cik": "",
            "filing_type": "",
        }
    # If no ' - ', assume entire title is form_type
    return {
        "form_type": title.strip(),
        "company_name": "",
        "cik": "",
        "filing_type": "",
    }


def fetch_sec_edgar() -> list[dict[str, Any]]:
    """Fetch SEC EDGAR ATOM feed with retry logic."""
    logger.info(f"Fetching SEC EDGAR ATOM: {FEED_URL}")
    entries: list[dict[str, Any]] = []

    try:
        content = fetch_with_retry(FEED_URL, timeout=60, headers=HEADERS)
        feed = feedparser.parse(content)
    except Exception as e:
        logger.error(f"Failed to fetch SEC EDGAR feed after retries: {e}")
        return entries

    # Process entries
    for entry in getattr(feed, "entries", []) or []:
        # Parse title for structured data
        title = getattr(entry, "title", "")
        parsed_title = _parse_title(title)

        # Extract link: prefer entry.link, else first link in entry.links
        url = getattr(entry, "link", "")
        if not url and hasattr(entry, "links") and entry.links:
            url = entry.links[0].get('href', "")

        # Extract and strip summary
        summary_html = getattr(entry, "summary", "")
        summary = strip_tags(summary_html)

        # Parse updated date
        updated = getattr(entry, "updated", None)
        published = _parse_date(updated)

        entries.append(
            {
                "source": "sec_edgar",
                "title": title,
                "url": url,
                "published": published,
                "summary": summary,
                "guid": getattr(entry, "id", getattr(entry, "guid", "")),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "content_type": "filing",
                "language": "en",
                "region": "us",
                "form_type": parsed_title.get("form_type", ""),
                "company_name": parsed_title.get("company_name", ""),
            }
        )

    logger.info(f"Retrieved {len(entries)} SEC EDGAR items")
    return entries


def save_sec(entries: list[dict[str, Any]]) -> None:
    """Save entries to JSON files."""
    if not entries:
        logger.info("No SEC entries to save")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "intelligence")
    ensure_directories([output_dir])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"sec_edgar_{ts}.json")
    latest_json = os.path.join(output_dir, "sec_edgar_latest.json")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    logger.info("Saved SEC EDGAR latest and timestamped outputs")


def main() -> None:
    """Main ETL function."""
    logger.info("Starting SEC EDGAR ATOM ETL")
    entries = fetch_sec_edgar()
    if entries:
        save_sec(entries)
    logger.info("SEC EDGAR ETL complete")


if __name__ == "__main__":
    main()