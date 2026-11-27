"""Audible's new releases for the Scavenging tab (audible.es, rolling window).

The search page takes a publication window and pages of 50 results, and never
lists more than ten of them: with about 170 releases a day in the two
languages asked for, that is the last three days. Asked for a page past the
last one, it answers with the last page again. Labels arrive in the site's
language ("Fecha de lanzamiento:", "Duración:"), so each row is read after its
label instead of by its wording. The version row ("Versión íntegra",
"Versión acortada") has no label at all: it sits in the item's hover card
and is told by how it starts.
"""

import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, cast

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.etl.base import BaseETL
from src.utils.logging import get_logger

logger = get_logger("AudibleReleasesETL")

AUDIBLE_BASE = "https://www.audible.es"
NEW_RELEASES_PATH = "/newreleases"
# The filters of the page's own facets: Spanish (18385686031) and English
# (18385668031); audiobooks (18385638031) and training programs (18385639031).
BROWSE_FILTERS = "audible_programs=21870165031&feature_six_browse-bin=18385686031&feature_six_browse-bin=18385668031&feature_twelve_browse-bin=18385638031&feature_twelve_browse-bin=18385639031"
DEFAULT_WINDOW_DAYS = 30
PAGE_SIZE = 50
MAX_PAGES = 25  # the site lists no more
REQUEST_DELAY_SECONDS = 1.0

_DATE = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{2})$")
_RATING = re.compile(r"^(\d+(?:[.,]\d+)?)\s+([\d.,]+)")
_HOURS = re.compile(r"(\d+)\s*h")
_MINUTES = re.compile(r"(\d+)\s*m")
# The version row has no class of its own: it is a bare row that starts with "Versión…", or says "Abridged" or "Grabación original".
_VERSION_ROW = re.compile(r"^(?:versi[oó]n\b|(?:un)?abridged\b|grabaci[oó]n original\b)", re.IGNORECASE)


def publication_window(today: date | None = None, days: int = DEFAULT_WINDOW_DAYS) -> tuple[date, date]:
    """The window the page is asked for: ``days`` ending today.

    It used to be a fixed pair of dates that expired, after which every run
    read the same old page.
    """
    end = today or datetime.now(timezone.utc).date()
    return end - timedelta(days=max(1, days) - 1), end


def build_url(window: tuple[date, date], page: int, page_size: int = PAGE_SIZE) -> str:
    """The search page for one page of ``window``."""
    start, end = window
    return f"{AUDIBLE_BASE}{NEW_RELEASES_PATH}?{BROWSE_FILTERS}&publication_date={start:%Y%m%d}-{end:%Y%m%d}&sort=pubdate-desc-rank&page={page}&pageSize={page_size}"


def parse_release_date(text: str) -> datetime | None:
    """``"26-11-26"`` → that day at midnight UTC; None for anything else."""
    match = _DATE.match(text.strip())
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return datetime(2000 + year, month, day, tzinfo=timezone.utc)
    except ValueError:  # 31-02-26
        return None


def parse_runtime_minutes(text: str) -> int | None:
    """``"8 horas y 24 mins"`` → 504 (``"8 hrs and 24 mins"`` reads the same)."""
    hours, minutes = _HOURS.search(text), _MINUTES.search(text)
    if not hours and not minutes:
        return None
    return (int(hours.group(1)) * 60 if hours else 0) + (int(minutes.group(1)) if minutes else 0)


def parse_rating(text: str) -> tuple[float | None, int]:
    """``"5,0 1 valoración"`` → (5.0, 1); ``"sin valoraciones"`` → (None, 0)."""
    match = _RATING.match(" ".join(text.split()))
    if not match:
        return None, 0
    return float(match.group(1).replace(",", ".")), int(match.group(2).replace(".", "").replace(",", ""))


def _after_label(text: str) -> str:
    """What a labelled row says after its label ("Narrado por: A , B" → "A, B").

    Only the label goes: a series name may hold a colon of its own ("Serie: Something: Else, libro 1").
    """
    return re.sub(r"\s+([,;])", r"\1", text.split(":", 1)[-1].strip())


def _row_text(item: Any, class_name: str) -> str:
    """The text of the item's row with that class, or "" when there is none."""
    tag = item.find("li", class_=class_name)
    return tag.get_text(" ", strip=True) if tag else ""


def _version_row(item: Any) -> str:
    """The text of the row that tells the version ("Versión íntegra"), or "" when there is none.

    Only rows that carry no label are candidates, so a title or a subtitle that happens to contain "versión" is not mistaken for it.
    """
    for row in item.find_all("li", class_="bc-list-item"):
        if [label for label in row.get("class") or [] if label != "bc-list-item"]:
            continue
        text = row.get_text(" ", strip=True)
        if _VERSION_ROW.match(text):
            return text
    return ""


def _unabridged(version: str) -> bool | None:
    """Read the version row: False for "Versión acortada", True for "Versión íntegra", None for anything else ("Grabación original")."""
    text = version.lower()
    if "íntegra" in text or "unabridged" in text:
        return True
    if "acortada" in text or "abridged" in text:
        return False
    return None


def parse_releases_page(html: str) -> list[dict[str, Any]]:
    """The releases of one results page, as raw fields."""
    soup = BeautifulSoup(html, "html.parser")
    releases = []
    for item in soup.find_all("li", class_="productListItem"):
        heading = item.find("h3", class_="bc-heading")
        link = heading.find("a", href=True) if heading else None
        if link is None:
            continue

        version = _version_row(item)
        rating, rating_count = parse_rating(_after_label(_row_text(item, "ratingsLabel")))

        releases.append(
            {
                "title": link.get_text(" ", strip=True),
                # Without the tracking parameters, and absolute.
                "link": AUDIBLE_BASE + cast("str", link["href"]).split("?")[0],
                "subtitle": _row_text(item, "subtitle"),
                "author": _after_label(_row_text(item, "authorLabel")),
                "narrator": _after_label(_row_text(item, "narratorLabel")),
                "series": _after_label(_row_text(item, "seriesLabel")),
                "runtime": _after_label(_row_text(item, "runtimeLabel")),
                "language": _after_label(_row_text(item, "languageLabel")),
                "release_date": _after_label(_row_text(item, "releaseDateLabel")),
                "rating": rating,
                "rating_count": rating_count,
                "version": version,
                "unabridged": _unabridged(version) if version else None,
            }
        )
    return releases


def to_record(item: dict[str, Any]) -> dict[str, Any]:
    """One release in the shape the Scavenging tab reads, with its own columns."""
    released = parse_release_date(item.get("release_date", ""))
    # A no-break space after each icon, so that the narrow Details column never wraps one away from what it labels.
    parts = [
        f"👨‍💻\u00a0Autor: {item['author']}" if item.get("author") else "",
        f"🎙️\u00a0Narrador: {item['narrator']}" if item.get("narrator") else "",
        f"📚\u00a0Serie: {item['series']}" if item.get("series") else "",
        f"⏱️\u00a0{item['runtime']}" if item.get("runtime") else "",
        f"🌐\u00a0{item['language']}" if item.get("language") else "",
    ]
    if item.get("rating") is not None:
        parts.append(f"★ {item['rating']:.1f} ({item['rating_count']})")
    if item.get("unabridged") is False:
        parts.append("Versión acortada")
    return {
        "title": item.get("title", "Unknown Title"),
        "link": item.get("link", ""),
        # The release date: the tab sorts by it, and it used to be the time of the run for every book.
        "published": released.isoformat() if released else "",
        "summary": " | ".join(part for part in parts if part),
        "category": "audible",
        "source": "audible_releases_etl",
        "deal_type": "Audiobook",
        "price": "Included",
        "currency": "-",
        "subtitle": item.get("subtitle", ""),
        "author": item.get("author", ""),
        "narrator": item.get("narrator", ""),
        "series": item.get("series", ""),
        "runtime": item.get("runtime", ""),
        "runtime_minutes": parse_runtime_minutes(item.get("runtime", "")),
        "language": item.get("language", ""),
        "rating": item.get("rating"),
        "rating_count": item.get("rating_count", 0),
        "version": item.get("version", ""),
        "unabridged": item.get("unabridged"),
    }


class AudibleReleasesETL(BaseETL[dict[str, Any], dict[str, Any]]):
    """ETL to scrape Audible New Releases for the Scavenging tab."""

    def __init__(self, window_days: int = DEFAULT_WINDOW_DAYS, max_pages: int = MAX_PAGES):
        super().__init__(name="audible_releases", description="Scrapes Audible New Releases (last 30 days) into the Scavenging ecosystem", enable_checkpointing=True, max_retries=3, retry_delay=5)
        self.window_days = window_days
        self.max_pages = max_pages
        self.headers = {"User-Agent": SCRAPER_DEFAULT_USER_AGENT, "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}

    def _get(self, url: str) -> str:
        response = requests.get(url, headers=self.headers, timeout=15)
        response.raise_for_status()
        return response.text

    def extract(self) -> list[dict[str, Any]]:
        """Read every results page of the window, in order, until the site starts repeating itself."""
        window = publication_window(days=self.window_days)
        self.logger.info(f"Reading Audible new releases from {window[0]} to {window[1]}")
        releases: list[dict[str, Any]] = []
        seen_pages: set[tuple[str, ...]] = set()
        for page in range(1, self.max_pages + 1):
            self.logger.info(f"Scraping Audible releases page {page}...")
            try:
                found = parse_releases_page(self._get(build_url(window, page)))
            except Exception as e:  # broad by design: a page that fails to load keeps what the earlier ones gave
                self.logger.error(f"Failed fetching page {page}: {e}")
                break

            if not found:
                self.logger.info("No more products found, stopping extraction.")
                break
            page_links = tuple(release["link"] for release in found)
            if page_links in seen_pages:
                self.logger.info(f"Page {page} repeats an earlier one: the end of the results.")
                break
            seen_pages.add(page_links)
            releases.extend(found)
            time.sleep(REQUEST_DELAY_SECONDS)

        self.logger.info(f"Extracted {len(releases)} releases from Audible across {len(seen_pages)} pages.")
        return releases

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format the data to fit the Scavenging tab, one record per release."""
        transformed = []
        seen: set[str] = set()
        for item in data:
            link = item.get("link", "")
            if not link or link in seen:
                continue
            seen.add(link)
            transformed.append(to_record(item))

        self.logger.info(f"Transformed {len(transformed)} releases for Scavenging layout.")
        return transformed

    def load(self, data: list[dict[str, Any]]) -> None:
        """Write out to the canonical data/audible_releases/output/ directory.

        Records keep the scavenging display shape consumed by the dashboard
        Scavenging tab (see SCAVENGING_SOURCES in the tab component).
        """
        if not data:
            self.logger.warning("No data to load for Audible Releases.")
            return

        json_file = self.output_dir / "audible_releases_latest.json"
        csv_file = self.output_dir / "audible_releases_latest.csv"

        try:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved {len(data)} entries to {json_file}")
        except (OSError, TypeError, ValueError) as e:
            self.logger.error(f"Failed creating JSON: {e}")

        try:
            df = pd.DataFrame(data)
            df.to_csv(csv_file, index=False, encoding="utf-8")
        except Exception as e:  # broad by design: pandas DataFrame/CSV serialization of scraped data
            self.logger.error(f"Failed creating CSV: {e}")


if __name__ == "__main__":
    AudibleReleasesETL().run()
