"""Filmoteca de València (Institut Valencià de Cultura): the screenings of the current cycle.

`https://ivc.gva.es/es/audiovisuales/programacion/valencia-la-filmoteca-cas`
— HTML, one request. One ``div.actividad`` per screening: day, month, weekday
and time in the date box, the venue, the cycle, the film (title, link, director
line) and a ticket link whose path ends in the full date
(``/entradas/<slug>/2026-11-28``).

The listing prints no year. It is taken from the ticket link; a screening
without one takes the year of the screening before it, rolled over when its
month is earlier (a cycle that crosses New Year). A screening that comes before
any dated one is dropped rather than dated by guesswork (T-193).

No price on the listing. A plain HTTP client gets the data (verified
2026-11-28: 200, 93 KB, 48 screenings from 28 November to 30 December).
"""

import logging
import re
from datetime import date
from typing import Any

from bs4 import BeautifulSoup, Tag

from src.etl.news.valencia_events.dates import WEEKDAYS_SHORT, month_number
from src.etl.news.valencia_events.dom import text_of
from src.etl.news.valencia_events.http import fetch_page
from src.etl.news.valencia_events.records import CITY_VALENCIA, build_record, clock_text

LISTING_URL = "https://ivc.gva.es/es/audiovisuales/programacion/valencia-la-filmoteca-cas"
SOURCE = "ivc.gva.es/filmoteca"
LABEL = "Filmoteca de València"

_TICKET_DATE_RE = re.compile(r"/(\d{4}-\d{2}-\d{2})/?$")
_CITY_PREFIX = "valència"
MIN_YEAR = 2000


def _ticket_date(item: Tag) -> date | None:
    link = item.select_one("a.btn-venta-entradas[href]")
    match = _TICKET_DATE_RE.search(str(link.get("href") or "")) if link else None
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def ticket_url(item: Tag) -> str:
    """Href of the ticket link, "" when the screening has none."""
    link = item.select_one("a.btn-venta-entradas[href]")
    return str(link.get("href") or "") if link else ""


def parse(html: bytes, today: date | None = None) -> list[dict[str, Any]]:
    """Read the listing into one record per screening.

    Args:
        html: Raw body of the València listing.
        today: Reference day for the sanity bound on years; the current day when None.

    Returns:
        Raw records in page order (the page lists them chronologically).
    """
    soup = BeautifulSoup(html, "html.parser")
    reference = today or date.today()
    cursor: tuple[int, int, int] | None = None  # year, month, day of the previous dated screening
    records: list[dict[str, Any]] = []
    for item in soup.select("div.actividad"):
        box = item.select_one(".fecha")
        place = text_of(item.select_one("span.lugar"))
        if box is None or not place.lower().startswith(_CITY_PREFIX):
            continue
        try:
            day = int(text_of(box.select_one(".dia")))
        except ValueError:
            continue
        month = month_number(text_of(box.select_one(".mes")))
        if month is None or not 1 <= day <= 31:
            continue
        ticket = _ticket_date(item)
        if ticket is not None:
            if (ticket.month, ticket.day) != (month, day):
                continue  # the ticket link points at another session: the row is inconsistent
            when = ticket
        elif cursor is None:
            continue  # no dated screening before this one: the year is not known
        else:
            year, cursor_month, cursor_day = cursor
            if (month, day) < (cursor_month, cursor_day):
                year += 1
            try:
                when = date(year, month, day)
            except ValueError:
                continue
        if not MIN_YEAR <= when.year <= reference.year + 1:
            continue
        cursor = (when.year, when.month, when.day)

        heading = item.select_one("h2 a[href]")
        if heading is None:
            continue
        title = text_of(heading)
        if not title:
            continue
        hour = text_of(box.select_one(".hora"))
        start_time = clock_text(hour)
        cycle = text_of(item.select_one("span.extra-ciclo"))
        film_line = text_of(item.select_one(".textos-peli p:not(.azul)"))
        note = text_of(item.select_one("p.azul"))
        parts = [part for part in (film_line, f"Ciclo: {cycle}" if cycle else "", note) if part]
        weekday = WEEKDAYS_SHORT[when.weekday()]
        records.append(
            build_record(
                source=SOURCE,
                title=title,
                url=str(heading.get("href") or ""),
                start_date=when,
                date_text=f"{weekday} {day} {text_of(box.select_one('.mes'))} · {hour}".rstrip(" ·"),
                start_time=start_time,
                category="cine",
                description=" · ".join(parts),
                venue=place.split("-", 1)[1].strip() if "-" in place else place,
                city=CITY_VALENCIA,
                metadata={"cycle": cycle, "film": film_line, "ticket_url": ticket_url(item)},
            )
        )
    return records


def fetch(logger: logging.Logger | None = None) -> list[dict[str, Any]]:
    """Fetch the listing once and return its screenings."""
    log = logger or logging.getLogger(__name__)
    log.info(f"Fetching Filmoteca listings from {LISTING_URL}")
    records = parse(fetch_page(LISTING_URL))
    log.info(f"Retrieved {len(records)} screenings from the Filmoteca")
    return records
