"""The sources of Valencia events: one module each, listed once here.

A source module exposes its public URL, a stable ``SOURCE`` id (it is stored as
``source`` on every record and groups them in the report), a human ``LABEL``
and a ``fetch(logger)`` that returns raw records (see :mod:`records`) or raises.
Each source does one plain GET per page it needs and pauses between its pages;
none needs an API key.

:data:`SOURCES` is the order the composer asks them in. The three legacy
sources come first, unchanged, so the records the tab had before are still
there; the rest were added with T-143.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from src.etl.news.valencia_events.http import pause
from src.etl.news.valencia_events.sources import (
    ayuntamiento,
    escalante,
    eventbrite,
    feriavalencia,
    filmoteca,
    ivam,
    larambleta,
    lesarts,
    meetup,
    meetup_tech,
    teatre_principal,
    visitvalencia,
    visitvalencia_monthly,
)

Fetch = Callable[..., list[dict]]


@dataclass(frozen=True)
class Source:
    """One agenda: where it is read, how it is named and what fetches it."""

    key: str
    """Stable id stored as ``source`` on every record."""
    label: str
    """Human name, shown in the report."""
    urls: tuple[str, ...]
    """The public pages a run reads."""
    fetch: Fetch
    """``fetch(logger)`` returning the raw records."""
    legacy: bool = False
    """True for a source that ran before T-143, moved here unchanged."""


def months_now_and_next(now: datetime | None = None) -> tuple[str, str]:
    """The month of ``now`` and the next one, as YYYY-MM."""
    now = now or datetime.now()
    next_month = datetime(now.year + (now.month == 12), now.month % 12 + 1, 1)
    return f"{now.year}-{now.month:02d}", f"{next_month.year}-{next_month.month:02d}"


def _fetch_featured(logger: logging.Logger | None = None) -> list[dict]:
    """Featured agenda of the current and the next month: the two requests the ETL always made."""
    log = logger or logging.getLogger(__name__)
    records: list[dict] = []
    for index, month in enumerate(months_now_and_next()):
        if index:
            pause()
        records.extend(visitvalencia.fetch_month(month, log))
    return records


def _fetch_monthly(logger: logging.Logger | None = None) -> list[dict]:
    """Monthly agenda of the current and the next month."""
    return visitvalencia_monthly.fetch(months_now_and_next(), logger)


SOURCES: tuple[Source, ...] = (
    Source(visitvalencia.SOURCE, "Visit València", (visitvalencia.BASE_URL + "/agenda-valencia",), _fetch_featured, legacy=True),
    Source(meetup.SOURCE, "Meetup", (meetup.FIND_URL,), meetup.fetch_events, legacy=True),
    Source(eventbrite.SOURCE, "Eventbrite", (eventbrite.LISTING_URL,), eventbrite.fetch_events, legacy=True),
    Source(ayuntamiento.SOURCE, ayuntamiento.LABEL, (ayuntamiento.AGENDA_URL,), ayuntamiento.fetch),
    Source(visitvalencia_monthly.SOURCE, visitvalencia_monthly.LABEL, (visitvalencia_monthly.AGENDA_URL,), _fetch_monthly),
    Source(filmoteca.SOURCE, filmoteca.LABEL, (filmoteca.LISTING_URL,), filmoteca.fetch),
    Source(lesarts.SOURCE, lesarts.LABEL, (lesarts.LISTING_URL,), lesarts.fetch),
    Source(teatre_principal.SOURCE, teatre_principal.LABEL, (teatre_principal.LISTING_URL,), teatre_principal.fetch),
    Source(escalante.SOURCE, escalante.LABEL, (escalante.LISTING_URL,), escalante.fetch),
    Source(larambleta.SOURCE, larambleta.LABEL, (larambleta.HOME_URL,), larambleta.fetch),
    Source(feriavalencia.SOURCE, feriavalencia.LABEL, (feriavalencia.CALENDAR_URL,), feriavalencia.fetch),
    Source(ivam.SOURCE, ivam.LABEL, (ivam.ACTIVITIES_URL, ivam.EXHIBITIONS_URL), ivam.fetch),
    Source(meetup_tech.SOURCE, meetup_tech.LABEL, (meetup_tech.FIND_URL,), meetup_tech.fetch),
)

SOURCE_BY_KEY: dict[str, Source] = {source.key: source for source in SOURCES}
LEGACY_SOURCE_KEYS: frozenset[str] = frozenset(source.key for source in SOURCES if source.legacy)
