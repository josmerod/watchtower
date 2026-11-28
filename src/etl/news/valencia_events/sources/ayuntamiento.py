"""Agenda de la ciudad of the Ayuntamiento de València (valencia.es).

`https://www.valencia.es/cas/agenda-de-la-ciudad` — HTML, one request. The
Liferay portlet embeds its whole dataset in the page as
``var eventosInicio = [ {...}, ...];``: title, category, start and end as
epoch milliseconds at Valencia midnight, a slug for the detail page. No venue,
time or price on the listing (the detail page has them, one request away each).

Much of the array is not made of events. Each cultural centre of the city has
a "Programación" entry that stands for its whole season or its month, and the
museums have a year-round entry. Those are dropped here — they would sit on
every day of the calendar.

A plain HTTP client gets the data (verified 2026-11-28: 200, 164 KB, 81 entries).
"""

import json
import logging
import re
from datetime import date, datetime
from typing import Any

from src.etl.news.valencia_events.dates import MADRID
from src.etl.news.valencia_events.http import fetch_page
from src.etl.news.valencia_events.records import CITY_VALENCIA, build_record

AGENDA_URL = "https://www.valencia.es/cas/agenda-de-la-ciudad"
DETAIL_URL = AGENDA_URL + "/-/content/"
SOURCE = "valencia.es"
LABEL = "Ayuntamiento de València"

_EVENTS_RE = re.compile(r"var eventosInicio = (\[.*?\]);\s*\n", re.S)
# "Escalante - Programación", "Palau de la Música - Programación de noviembre": a title that
# says "programación" stands for a whole programme, whatever its length.
_PROGRAMME_RE = re.compile(r"programaci[oó]n", re.IGNORECASE)
# "Bioparc - Agenda de actividades", "Oficina de l'Energia: actividades gratuitas".
_AGENDA_RE = re.compile(r"\bagenda de actividades\b|\bactividades\b", re.IGNORECASE)
# A "programación"/"actividades" entry this long is a container; any entry this long is not an event.
_PROGRAMME_MIN_DAYS = 180
# An entry that lasts the whole year is a permanent facility (a museum, a visit open all
# year): it would sit on every day of the calendar, so it is left out.
_PERMANENT_MIN_DAYS = 360

CATEGORY_MAP = {
    "EXPOSICIONES": "arte",
    "MUSEOS MUNICIPALES": "arte",
    "MÚSICA": "música",
    "TEATRO": "teatro",
    "CIRCO": "teatro",
    "DANZA": "danza",
    "CINE": "cine",
    "AGENDA INFANTIL": "infantil",
    "OCIO ALTERNATIVO": "otro",
    "FERIAS": "ferias",
    "CONGRESOS": "ferias",
    "CONFERENCIAS": "charlas y talleres",
    "CURSOS": "charlas y talleres",
    "JORNADAS": "charlas y talleres",
    "TALLERES": "charlas y talleres",
    "ENCUENTROS": "otro",
    "VISITAS GUIADAS": "visitas y rutas",
    "RUTAS CULTURALES": "visitas y rutas",
    "NAVIDAD": "fiestas",
    "NAVIDAD DESTACADA": "fiestas",
    "FIESTAS": "fiestas",
}


def _epoch_date(value: Any) -> date | None:
    """Epoch milliseconds as the Valencia calendar day; None for anything else."""
    text = str(value or "").strip()
    if not text.isdigit():
        return None
    try:
        return datetime.fromtimestamp(int(text) / 1000, MADRID).date()
    except (OverflowError, OSError, ValueError):
        return None


def _start_date(entry: dict[str, Any]) -> date | None:
    """Start day of an entry: the epoch value, else the YYYY-MM-DD sort field."""
    day = _epoch_date(entry.get("startDate"))
    if day is not None:
        return day
    text = str(entry.get("startDateSort") or "").strip()
    try:
        return date.fromisoformat(text) if text else None
    except ValueError:
        return None


def is_programme_container(title: str, start: date, end: date) -> bool:
    """True for an entry that is not one event: a "Programación" of any length, a long "actividades" programme, or a permanent year-long facility."""
    span_days = (end - start).days
    if span_days >= _PERMANENT_MIN_DAYS or _PROGRAMME_RE.search(title):
        return True
    return span_days >= _PROGRAMME_MIN_DAYS and bool(_AGENDA_RE.search(title))


def parse(html: bytes) -> list[dict[str, Any]]:
    """Read the events array embedded in the agenda page.

    Args:
        html: Raw body of the agenda page.

    Returns:
        Raw records; empty when the page no longer embeds the array. The
        programme and permanent entries are left out (see
        :func:`is_programme_container`).
    """
    text = html.decode("utf-8", errors="replace")
    match = _EVENTS_RE.search(text)
    if not match:
        return []
    try:
        entries = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    records: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("content") or "").strip()
        start = _start_date(entry)
        if not title or start is None:
            continue
        end = _epoch_date(entry.get("endDate")) or start
        if end < start:
            end = start
        if is_programme_container(title, start, end):
            continue
        raw_category = str(entry.get("categoria") or "").strip()
        span_days = (end - start).days
        records.append(
            build_record(
                source=SOURCE,
                title=title,
                url=DETAIL_URL + str(entry.get("url") or "").strip(),
                start_date=start,
                end_date=end,
                date_text=f"Del {start:%d/%m/%Y} al {end:%d/%m/%Y}" if span_days else f"{start:%d/%m/%Y}",
                category=CATEGORY_MAP.get(raw_category.upper(), ""),
                city=CITY_VALENCIA,
                metadata={"source_category": raw_category, "agenda_id": str(entry.get("id") or ""), "span_days": span_days},
            )
        )
    return records


def fetch(logger: logging.Logger | None = None) -> list[dict[str, Any]]:
    """Fetch the agenda once and return its events."""
    log = logger or logging.getLogger(__name__)
    log.info(f"Fetching agenda from {AGENDA_URL}")
    records = parse(fetch_page(AGENDA_URL))
    log.info(f"Retrieved {len(records)} events from {AGENDA_URL}")
    return records
