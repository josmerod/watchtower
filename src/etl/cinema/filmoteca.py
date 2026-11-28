"""Filmoteca València (IVAC): the day-by-day programme of the Valencian film institute.

One static page of the public body lists every screening of its three venues
for weeks ahead: day, start time, film, director, country, year, version,
running time and medium. The ticket link carries the ISO date of sessions
that are on sale. The page prints no price.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

from bs4 import BeautifulSoup, Tag

from src.etl.cinema.common import Listing, ListingResult, SourceUnavailable, attr_of, clock_times, http_url, make_session, normalise_version, read_listings, resolve_day, spanish_month, spanish_weekday, text_of

logger = logging.getLogger(__name__)

SOURCE = "ivc.gva.es"

# The page lists Castelló and Alicante too: only the València venue is kept.
LISTINGS: tuple[Listing, ...] = (
    Listing(
        url="https://ivc.gva.es/es/audiovisuales/programacion/programacion-dias",
        key="filmoteca-valencia",
        name="Filmoteca València",
        city="València",
        address="Edificio Rialto",
    ),
)
VENUE_CITY = "València"

_YEAR = re.compile(r"\b(\d{4})\b")
_MINUTES = re.compile(r"^(\d{1,3})'\s*(?:min)?\.?$")
_FILM_MEDIUM = re.compile(r"^\d{2}\s?mm$|blu-?ray|dvd|vhs|super ?8", re.IGNORECASE)
_ISO_DAY_IN_URL = re.compile(r"/(\d{4}-\d{2}-\d{2})/?$")


def _credits_of(item: Tag) -> list[str]:
    """The parts of the credit line under the title, split on the middle dots.

    "<strong>Billy Wilder</strong> · EEUU · 1970 · VOS CASTELLANO · Color · 125' · 35 mm" gives seven parts.
    The note of the second card (``p.azul``) is not a sibling of the title and is left out.
    """
    line = item.select_one("div.textos-peli h2 ~ p")
    if line is None:
        return []
    return [part.strip() for part in text_of(line).split("·") if part.strip()]


def _film_facts(credits: list[str], line: Tag | None) -> dict[str, Any]:
    """Director, year, version, running time and medium, read off the credit parts by what they look like."""
    facts: dict[str, Any] = {}
    if line is not None and line.find("strong") is not None:
        facts["director"] = text_of(line.find("strong"))
    year_from = 0
    for index, part in enumerate(credits):
        year = _YEAR.search(part)
        if year and index > 0:
            facts["year"] = int(year.group(1))
            year_from = index + 1
            break
    minutes = next((part for part in credits if _MINUTES.match(part)), "")
    match = _MINUTES.match(minutes)
    if match:
        facts["duration_min"] = int(match.group(1))
    last = credits[-1] if credits else ""
    if len(credits) >= 5 and last != minutes and _FILM_MEDIUM.search(last):
        facts["format"] = last
    # The version follows the country and the year; nothing before them reads as one.
    for part in credits[max(year_from, 1) :]:
        version = normalise_version(part)
        if version:
            facts["version"] = version
            facts["language"] = part
            break
    return facts


def _day_of(item: Tag, reference: date) -> str:
    """The screening day: the ISO date of the ticket link when it has one, else the date block of the item."""
    ticket = item.select_one("a.btn-venta-entradas[href]")
    match = _ISO_DAY_IN_URL.search(attr_of(ticket, "href"))
    if match:
        return match.group(1)
    try:
        day_number = int(text_of(item.select_one("span.dia")))
    except ValueError:
        return ""
    month = spanish_month(text_of(item.select_one("span.mes")))
    if month is None:
        return ""
    resolved = resolve_day(day_number, month, reference, spanish_weekday(text_of(item.select_one("span.nombre-dia"))))
    return resolved.isoformat() if resolved else ""


def parse(html: str | bytes, listing: Listing, reference: date) -> list[dict[str, Any]]:
    """Read the programme into the sessions of the València venue.

    Args:
        html: The programme page.
        listing: The cinema page being read.
        reference: The day the page is read, for a session whose ticket link carries no date.

    Returns:
        The València sessions of the page, in the order it prints them.

    Raises:
        SourceUnavailable: When the page is not the programme (redesign, error page, bot check).
    """
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.actividad")
    if not items:
        raise SourceUnavailable(f"{listing.url}: not the programme page")

    sessions: list[dict[str, Any]] = []
    for item in items:
        try:
            sessions.extend(_sessions_of_item(item, listing, reference))
        except Exception as exc:  # broad by design: one malformed item must not sink the other screenings
            logger.warning("filmoteca: skipped a screening: %s: %s", type(exc).__name__, exc)
    return sessions


def _sessions_of_item(item: Tag, listing: Listing, reference: date) -> list[dict[str, Any]]:
    """The sessions of one programme item: one per start time it prints."""
    when = item.select_one("div.fecha")
    if when is None:
        return []
    venue = text_of(item.select_one("span.lugar"))
    city, _, venue_name = venue.partition(" - ")
    if not city.strip().casefold().startswith(VENUE_CITY.casefold()):
        return []
    film_link = item.select_one("div.textos-peli h2 a")
    if film_link is None:
        return []
    title = attr_of(film_link, "title") or text_of(film_link)
    credits = _credits_of(item)
    day = _day_of(item, reference)

    sessions: list[dict[str, Any]] = []
    for time in clock_times(text_of(when.select_one("span.hora"))):
        record = make_session(
            title=title,
            cinema=listing.name,
            city=listing.city,
            day=day,
            time=time,
            source=SOURCE,
            address=venue_name.strip() or listing.address,
            ticket_url=http_url(attr_of(item.select_one("a.btn-venta-entradas[href]"), "href")),
            film_url=http_url(attr_of(film_link, "href")),
            **_film_facts(credits, item.select_one("div.textos-peli h2 ~ p")),
        )
        if record:
            sessions.append(record)
    return sessions


def fetch(fetcher: Any, reference: date) -> list[ListingResult]:
    """Read the programme, one request."""
    return read_listings(fetcher, LISTINGS, parse, reference)
