"""Palau de les Arts Reina Sofía: the dated productions of the season.

`https://www.lesarts.com/es/programacion.html` — HTML, one request. One
``.box_product`` per production: title, subtitle, date box (``SA 28.11.26`` or
``Del DO 29.11.26 al DO 14.02.27``, with a two-digit year), start time, hall
and category. Boxes without a date box are programmes without sessions
("no-funcions") and are skipped.

The time is the one printed; a missing one leaves the production undated in
time (all-day), it is not filled in. No price on the listing. A plain HTTP
client gets the data (verified 2026-11-28: 200, 546 KB, 25 dated productions).
"""

import logging
from typing import Any

from bs4 import BeautifulSoup, Tag

from src.etl.news.valencia_events.dates import date_tokens, resolve_years
from src.etl.news.valencia_events.dom import text_of
from src.etl.news.valencia_events.http import fetch_page
from src.etl.news.valencia_events.records import CITY_VALENCIA, build_record, clock_text

LISTING_URL = "https://www.lesarts.com/es/programacion.html"
SOURCE = "lesarts.com"
LABEL = "Palau de les Arts"
VENUE = "Palau de les Arts"

# "Per a tots" means for every audience and says nothing about the kind of show: the title decides.
CATEGORY_MAP = {
    "Dansa": "danza",
    "Òpera": "música",
    "Lied": "música",
    "Simfònic": "música",
    "Barroc i Música Antiga": "música",
    "Músiques Valencianes": "música",
    "Grans veus": "música",
    "Flamenco": "música",
    "Familiar": "infantil",
    "Educación": "charlas y talleres",
}


def parse(html: bytes) -> list[dict[str, Any]]:
    """Read the productions that carry a date box.

    Args:
        html: Raw body of the programme page.

    Returns:
        Raw records in page order; a date box whose year or day cannot be read
        is skipped.
    """
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []
    for box in soup.select(".box_product"):
        data = box.select_one(".data")
        if data is None:
            continue
        date_text = text_of(data)
        tokens = date_tokens(date_text)
        if not tokens or tokens[0].year is None:
            continue
        resolved = resolve_years(tokens)
        if len(resolved) != len(tokens) or resolved[0] is None:
            continue
        start = resolved[0]
        end = resolved[-1] if len(resolved) > 1 else None
        link = box.select_one("a.titol[href]")
        title = text_of(box.select_one("a.titol"))
        if link is None or not title:
            continue
        raw_category = text_of(box.select_one("span.categoria"))
        hour = text_of(box.select_one("span.hora"))
        subtitle = text_of(box.select_one(".subtitol"))
        records.append(
            build_record(
                source=SOURCE,
                title=title,
                url=str(link.get("href") or ""),
                start_date=start,
                end_date=end,
                date_text=date_text,
                start_time=clock_text(hour),
                category=CATEGORY_MAP.get(raw_category, ""),
                description=subtitle,
                venue=text_of(box.select_one(".espai")) or VENUE,
                city=CITY_VALENCIA,
                metadata={"source_category": raw_category, "subtitle": subtitle, "show_id": class_value(box, "id_"), "default_category": "música"},
            )
        )
    return records


def class_value(box: Tag, prefix: str) -> str:
    """Value of the first class of the box that starts with ``prefix`` ("id_1357" → "1357")."""
    for name in box.get("class") or []:
        if str(name).startswith(prefix):
            return str(name)[len(prefix) :]
    return ""


def fetch(logger: logging.Logger | None = None) -> list[dict[str, Any]]:
    """Fetch the programme once and return its dated productions."""
    log = logger or logging.getLogger(__name__)
    log.info(f"Fetching Palau de les Arts programme from {LISTING_URL}")
    records = parse(fetch_page(LISTING_URL))
    log.info(f"Retrieved {len(records)} productions from Palau de les Arts")
    return records
