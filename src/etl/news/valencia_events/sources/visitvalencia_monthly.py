"""Monthly agenda of visitvalencia.com: everything on for a month, one page per month.

`https://www.visitvalencia.com/agenda-valencia/agenda-mensual?date=YYYY-MM` —
HTML, one request per month (current and next). Every event is one or more
``div.card--event`` cards carrying the event's node id, its title, a link and a
date span printed as Spanish text ("Del 16/06/2025 al 31/12/2026", "30/11/2026").
A session of a recurring event is a card of its own; cards of one event that
touch or overlap are merged into one span, so a weekly tour does not become
forty records. Two separate sessions stay two records.

No category, venue or price on the listing: the record says so by leaving
them empty. A plain HTTP client gets the data (verified 2026-11-28: 200,
318 cards / 104 events for November, 479 / 153 for December).
"""

import logging
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any

from bs4 import BeautifulSoup, Tag

from src.etl.news.valencia_events.dates import parse_written_range
from src.etl.news.valencia_events.dom import absolute_url, text_of
from src.etl.news.valencia_events.http import fetch_page, pause
from src.etl.news.valencia_events.records import CITY_VALENCIA, build_record

BASE_URL = "https://www.visitvalencia.com"
AGENDA_URL = BASE_URL + "/agenda-valencia/agenda-mensual"
SOURCE = "visitvalencia.com/agenda-mensual"
LABEL = "Visit València · agenda mensual"


def month_url(month: str) -> str:
    """Agenda URL for a month given as YYYY-MM."""
    return f"{AGENDA_URL}?date={month}"


def merge_intervals(intervals: Iterable[tuple[date, date]]) -> list[tuple[date, date]]:
    """Fold spans that overlap or touch (the next starts the day after the previous ends) into one."""
    merged: list[tuple[date, date]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1] + timedelta(days=1):
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _event_path(card: Tag) -> str:
    about = str(card.get("about") or "")
    if about:
        return about
    for link in card.select("a[href]"):
        href = str(link.get("href") or "")
        if "/agenda-valencia/" in href:
            return href
    return ""


def collect(pages: Iterable[bytes]) -> list[dict[str, Any]]:
    """Read the monthly agenda pages into records, one per event and merged span.

    Args:
        pages: Raw bodies of one or more monthly agenda pages.

    Returns:
        Raw records. Cards whose date text carries no date are skipped, and a
        page without cards adds nothing.
    """
    spans: dict[str, list[tuple[date, date]]] = {}
    titles: dict[str, str] = {}
    paths: dict[str, str] = {}
    card_count = 0
    for html in pages:
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("div.card--event"):
            card_count += 1
            heading = card.select_one(".card__heading")
            title = text_of(heading)
            node_id = str(card.get("data-history-node-id") or "")
            date_text = text_of(card.select_one(".card__date"))
            start, end = parse_written_range(date_text)
            if not title or start is None or not node_id:
                continue
            key = node_id
            if key not in titles or (not paths.get(key) and _event_path(card)):
                paths[key] = _event_path(card)
            titles.setdefault(key, title)
            spans.setdefault(key, []).append((start, end or start))
    records: list[dict[str, Any]] = []
    for key, intervals in spans.items():
        for start, end in merge_intervals(intervals):
            single = start == end
            records.append(
                build_record(
                    source=SOURCE,
                    title=titles[key],
                    url=absolute_url(paths.get(key, ""), BASE_URL),
                    start_date=start,
                    end_date=None if single else end,
                    date_text=f"Del {start:%d/%m/%Y} al {end:%d/%m/%Y}" if not single else f"{start:%d/%m/%Y}",
                    city=CITY_VALENCIA,
                    metadata={"node_id": key, "sessions": len(intervals)},
                )
            )
    return records


def fetch(months: Iterable[str], logger: logging.Logger | None = None) -> list[dict[str, Any]]:
    """Fetch the agenda of each month (pausing between requests) and return its events."""
    log = logger or logging.getLogger(__name__)
    pages: list[bytes] = []
    for index, month in enumerate(months):
        if index:
            pause()
        url = month_url(month)
        log.info(f"Fetching monthly agenda from {url}")
        pages.append(fetch_page(url))
    records = collect(pages)
    log.info(f"Retrieved {len(records)} events from the visitvalencia.com monthly agenda")
    return records
