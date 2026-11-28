"""FilmAffinity cartelera: the cinemas of València whose own sites cannot be read with plain HTTP.

Kinépolis answers 403 to every client but a browser, Cinesa parks requests in
a waiting room, and the ABC, Yelmo and Ocine sites are single-page apps whose
sessions only arrive through scripts. FilmAffinity republishes all of them on
one server-rendered page per cinema, with the version and the format of the
cinemas' own feeds, so it is the one plain-HTTP route to those cinemas.

The page is read for what it is, a second-hand listing:

- ``data-sess-date`` is the session day. The day labels next to it ("Hoy",
  "Mañana", a bare weekday) are printed for the first rows of the feed and are
  wrong whenever the feed still starts on yesterday: they are not read.
- A start-time link may go through an affiliate redirect; the ticketing
  address it wraps is what gets stored.

Cinemas with a readable site of their own (Cine Tívoli, Babel, Filmoteca) are
not read here: the first-party listing wins.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, Tag

from src.etl.cinema.common import Listing, ListingResult, SourceUnavailable, attr_of, clock_time, http_url, make_session, read_listings, split_title, text_of

logger = logging.getLogger(__name__)

SOURCE = "filmaffinity.com"

_SHOWTIMES = "https://www.filmaffinity.com/es/theater-showtimes.php?id="

# One line per cinema, by its FilmAffinity theatre id: the cinemas of València
# and its ring that have no readable site of their own. ``name`` and ``city``
# stand in for a page that stops printing its heading or its address. Others in
# the province are one line away (Yelmo Cines VidaNova Parc 1223, Alucine
# Sagunto 204, Kinépolis Alzira 371, Cines Axion Xàtiva 471, Abc Gandía 518...).
LISTINGS: tuple[Listing, ...] = (
    Listing(url=f"{_SHOWTIMES}295", key="295", name="Kinépolis Valencia", city="Paterna"),
    Listing(url=f"{_SHOWTIMES}291", key="291", name="Cinesa Bonaire", city="Aldaia"),
    Listing(url=f"{_SHOWTIMES}543", key="543", name="Abc Park", city="València"),
    Listing(url=f"{_SHOWTIMES}516", key="516", name="Abc El Saler", city="València"),
    Listing(url=f"{_SHOWTIMES}507", key="507", name="Cines Lys", city="València"),
    Listing(url=f"{_SHOWTIMES}503", key="503", name="Yelmo Cines Mercado de Campanar", city="València"),
    Listing(url=f"{_SHOWTIMES}450", key="450", name="Ocine Aqua", city="València"),
    Listing(url=f"{_SHOWTIMES}536", key="536", name="Cines Mn4", city="Alfafar"),
    Listing(url=f"{_SHOWTIMES}519", key="519", name="ABC Gran Turia", city="Xirivella"),
)

_YEAR = re.compile(r"\b(\d{4})\b")
_MINUTES = re.compile(r"(\d{1,3})")
_CUT_OFF = re.compile(r"\s*(?:\.\.\.|…)\s*$")


def _where_of(soup: BeautifulSoup, listing: Listing) -> tuple[str, str]:
    """Read the street and the city from the address block, when the page has one."""
    block = soup.select_one("div.th-data div.street")
    if block is None:
        return listing.address, listing.city
    street = text_of(block.find("div"))
    for fragment in block.find_all(string=True, recursive=False):
        city = fragment.strip().strip(",").strip()
        if city:
            return street, city
    return street, listing.city


def _films_of(soup: BeautifulSoup) -> dict[str, dict[str, Any]]:
    """The film cards of the page by movie id: where a showtime block takes its film page, year and director."""
    films: dict[str, dict[str, Any]] = {}
    for card in soup.select("div.fa-content-card.movie[id^=m-]"):
        link = card.select_one(".mc-title a[href]")
        if link is None:
            continue
        year = _YEAR.search(text_of(card.select_one(".mc-year")))
        director = card.select_one(".mc-director")
        names = [text_of(name) for name in director.select("a")] if director is not None else []
        films[attr_of(card, "id")[2:]] = {
            "title": text_of(link),
            "film_url": http_url(attr_of(link, "href")),
            "year": int(year.group(1)) if year else None,
            # The feed cuts a long list short with "Fawn Veerasunthorn ...": the dots are not a name.
            "director": _CUT_OFF.sub("", ", ".join(names) if names else text_of(director)),
        }
    return films


def _direct_url(href: str) -> str:
    """Unwrap the affiliate redirect some start-time links go through, to the ticketing address it hides."""
    parsed = urlparse(href)
    if (parsed.hostname or "").endswith("awin1.com"):
        target = parse_qs(parsed.query).get("ued", [""])[0]
        if target.startswith(("https://", "http://")):
            return target
    return href


def parse(html: str | bytes, listing: Listing, reference: date) -> list[dict[str, Any]]:
    """Read one cinema page into session dictionaries.

    Args:
        html: The cinema's cartelera page.
        listing: The cinema page being read.
        reference: Unused: every row carries its own ISO date.

    Returns:
        The sessions of the page, block by block, each with the version and the format of its block title.

    Raises:
        SourceUnavailable: When the page is not a cinema cartelera (bot check, error page, redesign).
    """
    del reference
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.select_one("h1#main-title")
    if heading is None or "filmaffinity" not in text_of(soup.title).lower():
        raise SourceUnavailable(f"{listing.url}: not a cinema cartelera page")
    cinema = text_of(heading) or listing.name
    street, city = _where_of(soup, listing)
    films = _films_of(soup)

    sessions: list[dict[str, Any]] = []
    for block in soup.select("div.movie-showtimes-n[data-m-id]"):
        try:
            sessions.extend(_sessions_of_block(block, cinema, city, street, films))
        except Exception as exc:  # broad by design: one malformed block must not sink the other films
            logger.warning("filmaffinity: skipped a film block of %s: %s: %s", listing.key, type(exc).__name__, exc)
    return sessions


def _sessions_of_block(block: Tag, cinema: str, city: str, street: str, films: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """The sessions of one showtime block: one film in one version and one format."""
    title, version, format_name = split_title(text_of(block.select_one(".mv-title .fs-5")))
    film = films.get(attr_of(block, "data-m-id"), {})
    minutes = _MINUTES.search(text_of(block.select_one(".mv-title .runtime")))

    sessions: list[dict[str, Any]] = []
    for row in block.select("div.row[data-sess-date]"):
        day = attr_of(row, "data-sess-date")
        for link in row.select("div.sess-times a[href]"):
            record = make_session(
                title=title or str(film.get("title", "")),
                cinema=cinema,
                city=city,
                day=day,
                time=clock_time(text_of(link)),
                source=SOURCE,
                version=version,
                format=format_name,
                address=street,
                room=attr_of(link, "title"),
                ticket_url=_direct_url(http_url(attr_of(link, "href"))),
                film_url=str(film.get("film_url", "")),
                duration_min=int(minutes.group(1)) if minutes else None,
                year=film.get("year"),
                director=str(film.get("director", "")),
            )
            if record:
                sessions.append(record)
    return sessions


def fetch(fetcher: Any, reference: date) -> list[ListingResult]:
    """Read every cinema page of the aggregator, one request each."""
    return read_listings(fetcher, LISTINGS, parse, reference)
