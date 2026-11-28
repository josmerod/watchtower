"""The raw record every source hands to the composer.

A source only reports what its page says: the dates it prints, the clock time
when it prints one, the venue when it names one. Nothing here is derived or
guessed — that is the job of :mod:`normalise`, in one place, with tests.
"""

from collections.abc import Sequence
from datetime import date
from typing import Any

from src.etl.news.valencia_events.dates import parse_clock

CITY_VALENCIA = "València"


def iso_day(day: date | None) -> str:
    """A date as YYYY-MM-DD, "" for None."""
    return day.isoformat() if day else ""


def clock_text(raw: str | None) -> str:
    """``19:30 h`` → ``19:30``; "" when the text carries no clock."""
    clock = parse_clock(raw)
    return clock.strftime("%H:%M") if clock else ""


def build_record(
    *,
    source: str,
    title: str,
    url: str = "",
    start_date: date | None = None,
    end_date: date | None = None,
    date_text: str = "",
    start_time: str = "",
    end_time: str = "",
    category: str = "",
    description: str = "",
    venue: str = "",
    address: str = "",
    city: str = "",
    price_info: str = "",
    is_free: bool | None = None,
    tags: Sequence[str] = (),
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble one raw record in the shape ``process_valencia_events`` reads.

    Args:
        source: Stable source id, stored as ``source`` (it also groups records
            for the carry-over of a failed source).
        title: Event title, plain text.
        url: Link to the event page.
        start_date: First day, when the source gives one.
        end_date: Last day when the source gives a range; None for one day.
        date_text: The date exactly as the page prints it (kept for reference).
        start_time: Clock text such as ``19:30``; empty for an all-day event.
        end_time: Clock text for the end, when the source gives one.
        category: A vocabulary value or a hint the normaliser maps.
        description: Plain text.
        venue: Venue name, when the source names one.
        address: Address text, when the source prints one.
        city: Municipality, when the source states it.
        price_info: Price text as the source states it ("" when it states none).
        is_free: True/False when the source states it; None otherwise.
        tags: Extra labels.
        metadata: Source-specific details.

    Returns:
        The record. ``end_date`` later than ``start_date`` is kept; one day is
        stored as ``end_date=""``.
    """
    if end_date is not None and start_date is not None and end_date <= start_date:
        end_date = None
    return {
        "title": title,
        "url": url,
        "source": source,
        "category": category,
        "description": description,
        "start_date": iso_day(start_date),
        "end_date": iso_day(end_date),
        "date_text": date_text,
        "start_time": start_time,
        "end_time": end_time,
        "all_day": not start_time,
        "venue": venue,
        "address": address,
        "city": city,
        "price_info": price_info,
        "is_free": is_free,
        "tags": list(tags),
        "metadata": dict(metadata or {}),
    }
