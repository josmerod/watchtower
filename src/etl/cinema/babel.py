"""Cines Babel (València): the cartelera of cinesbabel.com.

A static WordPress page lists every film with its director, running time,
audio and subtitle languages, and one row of start times per day. The days
come without their year ("Sáb 28 Nov"), so they are dated against the day
the page is read. Each start time links to the ticketing site. The page
prints no address and no price.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

from bs4 import BeautifulSoup, Tag

from src.etl.cinema.common import Listing, ListingResult, SourceUnavailable, attr_of, clock_time, day_from_label, http_url, make_session, read_listings, text_of, version_from_language

logger = logging.getLogger(__name__)

SOURCE = "cinesbabel.com"

LISTINGS: tuple[Listing, ...] = (Listing(url="https://cinesbabel.com/cartelera/", key="cinesbabel", name="Cines Babel", city="València"),)

_MINUTES = re.compile(r"(\d{1,3})")


def _cinema_of(soup: BeautifulSoup, fallback: str) -> str:
    """Read the cinema name from the page title, 'Cartelera - Cines Babel'."""
    title = text_of(soup.title)
    if " - " in title and "cartelera" in title.lower():
        return title.split(" - ", 1)[1].strip() or fallback
    return fallback


def _meta_of(head: Tag) -> dict[str, str]:
    """The labelled lines under the title ('Director: ...', 'Duración: ...') by label."""
    meta: dict[str, str] = {}
    for line in head.find_all("div", recursive=False):
        label, separator, value = text_of(line).partition(":")
        if separator:
            meta[label.strip().casefold()] = value.strip()
    return meta


def parse(html: str | bytes, listing: Listing, reference: date) -> list[dict[str, Any]]:
    """Read the cartelera into session dictionaries.

    Args:
        html: The cartelera page.
        listing: The cinema page being read.
        reference: The day the page is read; the day rows carry no year.

    Returns:
        The sessions of every film and day row of the page.

    Raises:
        SourceUnavailable: When the page is not Babel's cartelera (redesign, error page, bot check).
    """
    soup = BeautifulSoup(html, "html.parser")
    posts = soup.select("div.pelicula-post")
    if not posts and "babel" not in text_of(soup.title).lower():
        raise SourceUnavailable(f"{listing.url}: not the Babel cartelera")
    cinema = _cinema_of(soup, listing.name)

    sessions: list[dict[str, Any]] = []
    for post in posts:
        try:
            sessions.extend(_sessions_of_film(post, cinema, listing.city, reference))
        except Exception as exc:  # broad by design: one malformed film block must not sink the other films
            logger.warning("babel: skipped a film block: %s: %s", type(exc).__name__, exc)
    return sessions


def _sessions_of_film(post: Tag, cinema: str, city: str, reference: date) -> list[dict[str, Any]]:
    """The sessions of one film block, across all its day rows."""
    head = post.select_one("div.pelicula-title")
    title = text_of(head.select_one("h2") if head is not None else None)
    meta = _meta_of(head) if head is not None else {}
    audio = meta.get("idioma", "")
    subtitles = meta.get("subtítulos", "")
    minutes = _MINUTES.search(meta.get("duración", ""))
    film_url = http_url(attr_of(post.select_one("div.caratula a[href]"), "href"))

    sessions: list[dict[str, Any]] = []
    for row in post.select("table.tabla-sesiones tr"):
        cells = row.find_all("td", recursive=False)
        if not cells:
            continue
        day = day_from_label(text_of(cells[0]), reference)
        for link in row.select("a[href]"):
            time = clock_time(text_of(link))
            record = make_session(
                title=title,
                cinema=cinema,
                city=city,
                day=day,
                time=time,
                source=SOURCE,
                version=version_from_language(audio, subtitles),
                language=" · ".join(part for part in (audio, f"subt. {subtitles}" if subtitles else "") if part),
                director=meta.get("director", ""),
                duration_min=int(minutes.group(1)) if minutes else None,
                ticket_url=http_url(attr_of(link, "href")),
                film_url=film_url,
            )
            if record:
                sessions.append(record)
    return sessions


def fetch(fetcher: Any, reference: date) -> list[ListingResult]:
    """Read the cartelera, one request."""
    return read_listings(fetcher, LISTINGS, parse, reference)
