"""EXHICINE chain: Cine Tívoli in Burjassot, on the chain's site exhicine.es.

The chain publishes one static WordPress page per cinema with every session
on it. Film, ISO day, start time and room come straight from the hidden
fields of each ticket form, so no JavaScript and no second request are
needed. The pages print neither a version nor a format nor a price. The
parser reads any cinema page of the chain; ``LISTINGS`` says which are read.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

from bs4 import BeautifulSoup, Tag

from src.etl.cinema.common import Listing, ListingResult, SourceUnavailable, attr_of, clock_time, day_from_label, http_url, make_session, read_listings, text_of

logger = logging.getLogger(__name__)

SOURCE = "exhicine.es"
BASE_URL = "https://exhicine.es"

# One line per cinema page read, Cine Tívoli first. ``name`` and ``city`` stand
# in for a page that stops printing its heading or its address. The chain has
# four more cinemas around the city, one line each when they are wanted:
# ``auditori-burjassot`` and ``cine-verano-serra`` (open-air, from June/July),
# ``cine-avenida-el-perello`` and ``cine-museros`` (no sessions most days).
LISTINGS: tuple[Listing, ...] = (Listing(url=f"{BASE_URL}/cine/cine-tivoli/", key="cine-tivoli", name="Cine Tívoli", city="Burjassot"),)

_ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CITY_LINE = re.compile(r"^\s*\d{5}\s*-?\s*([^,]+?)\s*(?:,\s*.+?)?\s*$")


def _cinema_of(soup: BeautifulSoup, fallback: str) -> str:
    """Read the cinema name from the page heading, 'Cartelera · Cine Tívoli'."""
    heading = text_of(soup.find("h1"))
    if "·" in heading:
        name = heading.split("·", 1)[1].strip()
        if name:
            return name
    return fallback


def _where_of(soup: BeautifulSoup) -> tuple[str, str]:
    """Read the street and the city from the location block, 'Carrer de José Carsí, 50' and '46100 - Burjassot, Valencia'."""
    lines = [text_of(line) for line in soup.select("div.info-location div.dir > div")]
    city = ""
    for line in lines[1:]:
        match = _CITY_LINE.match(line)
        if match:
            city = match.group(1).strip()
            break
    return (lines[0] if lines else ""), city


def _day_of(form: Tag, label: str, reference: date) -> str:
    """The session day: the ISO date of the form when it has one, else the day its label prints."""
    iso_day = attr_of(form.find("input", attrs={"name": "m_date"}), "value")
    if _ISO_DAY.fullmatch(iso_day):
        return iso_day
    return day_from_label(label, reference)


def parse(html: str | bytes, listing: Listing, reference: date) -> list[dict[str, Any]]:
    """Read one cinema page into session dictionaries.

    Args:
        html: The cartelera page.
        listing: The cinema page being read.
        reference: The day the page is read, for a form that carries no date.

    Returns:
        The sessions, one per ticket form of the page; none when the cinema has nothing on.

    Raises:
        SourceUnavailable: When the page is not a cartelera of the chain (redesign, error page, bot check).
    """
    soup = BeautifulSoup(html, "html.parser")
    if "cartelera" not in text_of(soup.find("h1")).lower() and not soup.select("div.sesiones-pelicula"):
        raise SourceUnavailable(f"{listing.url}: not a cartelera page")
    cinema = _cinema_of(soup, listing.name)
    street, city = _where_of(soup)
    city = city or listing.city

    sessions: list[dict[str, Any]] = []
    for movie in soup.select("div.movie[id^=movie-]"):
        try:
            sessions.extend(_sessions_of_film(movie, cinema, city, street or listing.address, listing.url, reference))
        except Exception as exc:  # broad by design: one malformed film block must not sink the other films
            logger.warning("exhicine: skipped a film block of %s: %s: %s", listing.key, type(exc).__name__, exc)
    return sessions


def _sessions_of_film(movie: Tag, cinema: str, city: str, street: str, page_url: str, reference: date) -> list[dict[str, Any]]:
    """The sessions of one film block of a cinema page.

    A session links to the cinema's page, where its time is a button of the ticket form: the form itself
    only takes a POST, so it cannot be the link.
    """
    title = text_of(movie.select_one("h2.title"))
    film_url = http_url(attr_of(movie.select_one("div.image a[href]"), "href"))
    sessions: list[dict[str, Any]] = []
    for block in movie.select("div.sesiones-pelicula div.content-date"):
        label = text_of(block.select_one("div.date"))
        for form in block.select("div.hour form"):
            time = clock_time(attr_of(form.select_one("input.link[type=submit]"), "value"))
            if not time:
                continue
            day = _day_of(form, label, reference)
            record = make_session(
                title=title,
                cinema=cinema,
                city=city,
                day=day,
                time=time,
                source=SOURCE,
                address=street,
                room=attr_of(form.find("input", attrs={"name": "m_room"}), "value"),
                ticket_url=page_url,
                film_url=film_url,
            )
            if record:
                sessions.append(record)
    return sessions


def fetch(fetcher: Any, reference: date) -> list[ListingResult]:
    """Read every cinema page of the chain, one request each."""
    return read_listings(fetcher, LISTINGS, parse, reference)
