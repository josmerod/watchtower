"""Feria Valencia: the calendar of the fairs and events held at its venue.

`https://www.feriavalencia.com/calendario-proximos-eventos/` — HTML, one
request. One ``.evento`` per event (an Elementor loop item): title, the
official site link, sector classes (``sector-deporte``, ``sector-tecnologia``,
``perfil-publico``...) and two date lines printed without a year
(``27 Nov`` / ``29 Nov``). Everything takes place at the Feria Valencia venue.

The year is not on the page. The list is in ascending order and starts with the
event in progress or the next one, so the year follows from the order: it rolls
over when an event starts in an earlier month than the previous one
(``26 Dic / 4 Ene``). That is only trusted when the first event falls near the
day of the fetch; otherwise nothing is returned rather than dated by guesswork
(T-193). No price on the calendar. A plain HTTP client gets the data (verified
2026-11-28: 200, 244 KB, 25 events from 27 November to 28 October next year).
"""

import logging
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any

from bs4 import BeautifulSoup

from src.etl.news.valencia_events.dates import DateToken, month_number, resolve_years
from src.etl.news.valencia_events.dom import text_of
from src.etl.news.valencia_events.http import fetch_page
from src.etl.news.valencia_events.records import build_record

CALENDAR_URL = "https://www.feriavalencia.com/calendario-proximos-eventos/"
SOURCE = "feriavalencia.com"
LABEL = "Feria Valencia"
VENUE = "Feria Valencia"
CITY = "València"

# The first event of the list may already be running or start a little ahead.
_FIRST_EVENT_PAST_DAYS = 14
_FIRST_EVENT_AHEAD_DAYS = 120


def classes_with(prefix: str, node: Any) -> list[str]:
    """Class names of a node that start with ``prefix``, without it."""
    return [str(name)[len(prefix) :] for name in node.get("class") or [] if str(name).startswith(prefix)]


def category_of(sectors: Iterable[str]) -> str:
    """Vocabulary category from the sector classes; the fair itself is the default."""
    sectors = set(sectors)
    if "deporte" in sectors or any(sector.startswith("competicion") for sector in sectors):
        return "deporte"
    if sectors & {"tecnologia", "drones"}:
        return "tech"
    if sectors & {"actividades-para-ninos", "ocio-familiar", "hinchables"}:
        return "infantil"
    if sectors and sectors <= {"administracion-publica", "institucional"}:
        return "otro"  # an election or an official act held at the venue, not a fair
    return "ferias"


def item_date_tokens(date_lines: Iterable[str]) -> list[DateToken]:
    """Day-and-month tokens of the two date lines, in order ("27 Nov", "/ 29 Nov")."""
    tokens: list[DateToken] = []
    for line in date_lines:
        parts = line.replace("/", " ").split()
        if len(parts) < 2:
            continue
        month = month_number(parts[1])
        if month is not None and parts[0].isdigit():
            tokens.append(DateToken(month, int(parts[0]), None))
    return tokens


def parse(html: bytes, today: date | None = None) -> list[dict[str, Any]]:
    """Read the calendar into records, each dated with the year its position in the list implies.

    Args:
        html: Raw body of the calendar page.
        today: Day of the fetch; the current day when None.

    Returns:
        Raw records in page order. Empty when the page has no dated events or
        when the first one does not fall near ``today``: then the list is not
        the ascending calendar this parser expects, and no year is invented.
    """
    soup = BeautifulSoup(html, "html.parser")
    reference = today or date.today()
    earliest = reference - timedelta(days=_FIRST_EVENT_PAST_DAYS)
    latest = reference + timedelta(days=_FIRST_EVENT_AHEAD_DAYS)
    year: int | None = None
    records: list[dict[str, Any]] = []
    previous_start: date | None = None
    for item in soup.select(".evento"):
        link = item.select_one("a[href]")
        title = text_of(item.select_one(".elementor-heading-title"))
        lines = [text_of(li) for li in item.select(".elementor-post-info li")]
        tokens = item_date_tokens(lines)
        if link is None or not title or not tokens:
            continue
        if year is None:
            first = _first_event_start(tokens, reference, earliest, latest)
            if first is None:
                return []
            year = first.year
        resolved = resolve_years(tokens, year)
        if not resolved or resolved[0] is None:
            continue
        start = resolved[0]
        crossed_new_year = previous_start is not None and (start.month, start.day) < (previous_start.month, previous_start.day) and year < reference.year + 1
        if crossed_new_year:
            # A later card that starts in an earlier month: the list has crossed New Year.
            year += 1
            resolved = resolve_years(tokens, year)
            if not resolved or resolved[0] is None:
                continue
            start = resolved[0]
        previous_start = start
        sectors = classes_with("sector-", item)
        records.append(
            build_record(
                source=SOURCE,
                title=title,
                url=str(link.get("href") or ""),
                start_date=start,
                end_date=resolved[-1],
                date_text=" / ".join(line.strip(" /") for line in lines if line.strip(" /")),
                category=category_of(sectors),
                venue=VENUE,
                city=CITY,
                tags=["profesional"] if "profesional" in classes_with("perfil-", item) else [],  # codespell:ignore -- Spanish
                metadata={"sectors": sectors, "organizer": "Feria Valencia" if "organizador-feria-valencia" in classes_with("organizador-", item) else "externo"},
            )
        )
    return records


def _first_event_start(tokens: list[DateToken], reference: date, earliest: date, latest: date) -> date | None:
    """Start of the first event of the list, in the year that puts it near ``reference``; None when no year does."""
    for candidate_year in (reference.year, reference.year - 1, reference.year + 1):
        resolved = resolve_years(tokens, candidate_year)
        if resolved and resolved[0] is not None and earliest <= resolved[0] <= latest:
            return resolved[0]
    return None


def fetch(logger: logging.Logger | None = None) -> list[dict[str, Any]]:
    """Fetch the calendar once and return its events."""
    log = logger or logging.getLogger(__name__)
    log.info(f"Fetching Feria Valencia calendar from {CALENDAR_URL}")
    records = parse(fetch_page(CALENDAR_URL))
    log.info(f"Retrieved {len(records)} events from the Feria Valencia calendar")
    return records
