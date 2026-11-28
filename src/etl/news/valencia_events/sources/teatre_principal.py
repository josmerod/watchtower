"""Teatre Principal de València (season at the Teatre Martín i Soler), through the IVC programme.  # codespell:ignore

`https://ivc.gva.es/es/ivc/programacion-ivc/teatro-principal-de-valencia` —
HTML, one request. One ``div.minificha`` per production: a date line
(``del 28 al 29 noviembre de 2026 · Teatre Principal de València al Teatre
Martín i Soler``, ``20 diciembre de 2026 · ...``), the title with its link and a  # codespell:ignore
ticket link to the IVC box office. The season pass ("ABONO") is a subscription,
not a performance, and is skipped.

No time or price on the listing: the record is all-day and the price unknown.
A plain HTTP client gets the data (verified 2026-11-28: 200, 51 KB, 4 productions).
"""

import logging
import re
from typing import Any

from bs4 import BeautifulSoup

from src.etl.news.valencia_events.dates import parse_written_range
from src.etl.news.valencia_events.dom import text_of
from src.etl.news.valencia_events.http import fetch_page
from src.etl.news.valencia_events.records import CITY_VALENCIA, build_record

LISTING_URL = "https://ivc.gva.es/es/ivc/programacion-ivc/teatro-principal-de-valencia"
SOURCE = "ivc.gva.es/teatre-principal"
LABEL = "Teatre Principal (IVC)"
DEFAULT_VENUE = "Teatre Principal de València"
_SEPARATORS = ("·", "-", "|")
_SEASON_PASS_RE = re.compile(r"^\s*abono\b", re.IGNORECASE)


def split_date_line(text: str) -> tuple[str, str]:
    """Split a date line into its date part and its venue part ("del 28 al 29 noviembre de 2026 · <venue>")."""
    for separator in _SEPARATORS:
        if separator in text:
            date_part, _, venue_part = text.partition(separator)
            return date_part.strip(), venue_part.strip()
    return text.strip(), ""


def venue_of(venue_text: str) -> tuple[str, str]:
    """The hall and the company from the venue part of a date line.

    ``Teatre Principal de València al Teatre Martín i Soler`` is the Principal  # codespell:ignore
    company playing at the Palau de les Arts while its own theatre is closed:
    the hall is what places the event.
    """
    company, separator, hall = venue_text.partition(" al ")
    if separator and hall.strip():
        return hall.strip(), company.strip()
    return venue_text.strip() or DEFAULT_VENUE, ""


def parse(html: bytes) -> list[dict[str, Any]]:
    """Read the productions of the season page.

    Args:
        html: Raw body of the programme page.

    Returns:
        Raw records in page order; a production without a readable date is skipped.
    """
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []
    for card in soup.select("div.minificha"):
        heading = card.select_one("h2 a[href]")
        if heading is None:
            continue
        title = text_of(heading)
        if not title or _SEASON_PASS_RE.match(title):
            continue
        date_part, venue_text = split_date_line(text_of(card.select_one("p.fecha")))
        start, end = parse_written_range(date_part)
        if start is None:
            continue
        venue, company = venue_of(venue_text)
        tickets = card.select_one("a.boton-venta[href]")
        records.append(
            build_record(
                source=SOURCE,
                title=title,
                url=str(heading.get("href") or ""),
                start_date=start,
                end_date=end,
                date_text=date_part,
                category="teatro",
                venue=venue,
                city=CITY_VALENCIA,
                metadata={"ticket_url": str(tickets.get("href") or "") if tickets else "", "venue_text": venue_text, "company": company},
            )
        )
    return records


def fetch(logger: logging.Logger | None = None) -> list[dict[str, Any]]:
    """Fetch the programme once and return its productions."""
    log = logger or logging.getLogger(__name__)
    log.info(f"Fetching Teatre Principal programme from {LISTING_URL}")
    records = parse(fetch_page(LISTING_URL))
    log.info(f"Retrieved {len(records)} productions from the Teatre Principal programme")
    return records
