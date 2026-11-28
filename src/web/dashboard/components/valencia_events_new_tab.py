"""The Valencia Events tab (T-143): what is on in Valencia, with the filters it takes to use it.

The tab reads ``data/valencia_events/valencia_events.json`` through a repository and shows one
paged table of the events that start in a window of days (the next 7 by default; today, the
weekend, the month or a custom range), narrowed by a search term, the category, the zone and
"solo gratis", in the order chosen. Every change goes through one controller callback, and the
date of an event is the readable local form the ETL wrote (T-178): ``start_local`` for the files
of T-143 and later, the rule of :func:`_format_event_date` for the older ones.

"Nuevos desde tu ultima visita" is shared by the server and ``assets/js/valencia_state.js``:
the script keeps the moment the tab was last opened in ``localStorage`` (``wt_valencia_last_visit``)
and hands it to the server through the ``valencia-last-visit`` store; the server answers with the
events first detected after it. Rows carry ``data-valencia-detected`` so the script can badge them.
The labels are in Spanish.
"""

import json
import logging
import unicodedata
from collections import Counter
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dash
import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from src.repositories import BaseRepository
from src.utils.text import plain_excerpt
from src.web.dashboard.components.shared.table import paginate, pagination_controls, render_items_table
from src.web.dashboard.search_utils import create_search_input
from src.web.dashboard.utils import get_data_path

logger = logging.getLogger(__name__)

# Data file paths
VALENCIA_EVENTS_FILE = Path(get_data_path("valencia_events", "valencia_events.json"))
# How every source fared in the last run, written next to the events by the ETL.
VALENCIA_SOURCES_STATUS_FILE = Path(get_data_path("valencia_events", "sources_status.json"))


class ValenciaEventsNewRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for Valencia events data."""

    def __init__(self):
        """Initialize Valencia events repository."""
        super().__init__(
            data_path=VALENCIA_EVENTS_FILE,
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform JSON data into list of events.

        Args:
            raw_data: Raw JSON data

        Returns:
            List of event dictionaries
        """
        if isinstance(raw_data, list):
            return raw_data
        elif isinstance(raw_data, dict):
            return [raw_data]
        else:
            return []


# Create singleton instance
valencia_events_new_repo = ValenciaEventsNewRepository()


def load_valencia_events() -> list[dict[str, Any]]:
    """Load Valencia events data using repository pattern."""
    try:
        events = valencia_events_new_repo.get()
        logger.info(f"Loaded {len(events)} Valencia events from {VALENCIA_EVENTS_FILE}")
        return events
    except Exception as e:
        logger.error(f"Error loading Valencia events: {e}")
        return []


def load_sources_status() -> dict[str, Any]:
    """How every source fared in the last run; ``{}`` when the file is absent or unreadable."""
    try:
        data = json.loads(VALENCIA_SOURCES_STATUS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


# Events are shown in the local time of the city. Meetup prints its start
# times in UTC ("2026-11-27T19:30:00.000Z"); visitvalencia and Eventbrite
# give calendar dates, which need no conversion.
_MADRID = ZoneInfo("Europe/Madrid")
_WEEKDAYS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
# Where an event without a date goes in an order by date: last.
_FAR_FUTURE = datetime.max.replace(tzinfo=_MADRID)

# Ids of the tab. They are global in the page, so they carry the tab slug; valencia_state.js reads the same names.
SEARCH_ID = "valencia-search"
SEARCH_CLEAR_ID = f"{SEARCH_ID}-clear"
PERIOD_ID = "valencia-period"
FROM_ID = "valencia-from"
TO_ID = "valencia-to"
RANGE_ROW_ID = "valencia-range-row"
CATEGORY_ID = "valencia-category"
ZONE_ID = "valencia-zone"
FREE_ID = "valencia-free"
ONLY_NEW_ID = "valencia-only-new"
ONGOING_ID = "valencia-ongoing"
SORT_ID = "valencia-sort"
PER_PAGE_ID = "valencia-per-page"
CLEAR_ID = "valencia-clear"
RESULTS_ID = "valencia-results"
PAGER_ID = "valencia-pager"
PREV_ID, NEXT_ID = "valencia-prev", "valencia-next"
PAGE_STORE_ID = "valencia-page"
LAST_VISIT_ID = "valencia-last-visit"
NEW_BOX_ID = "valencia-new-box"
NOTICE_ID = "valencia-new-notice"
SHOW_ALL_ID = "valencia-new-show-all"
MARK_SEEN_ID = "valencia-mark-seen"

# The period choices; the value is what the select holds.
DEFAULT_PERIOD = "week7"
PERIODS = [
    {"label": "Próximos 7 días", "value": "week7"},
    {"label": "Hoy", "value": "today"},
    {"label": "Este fin de semana", "value": "weekend"},
    {"label": "Esta semana", "value": "this_week"},
    {"label": "Este mes", "value": "this_month"},
    {"label": "Rango personalizado", "value": "custom"},
    {"label": "Todas las fechas", "value": "all"},
]
DEFAULT_SORT = "start"
SORTS = [
    {"label": "Fecha: más cercano primero", "value": "start"},
    {"label": "Fecha: más lejano primero", "value": "start_desc"},
    {"label": "Precio: más barato primero", "value": "price"},
    {"label": "Precio: más caro primero", "value": "price_desc"},
    {"label": "Detectados hace menos tiempo", "value": "newest"},
]
PER_PAGE_OPTIONS = (25, 50, 100)
DEFAULT_PER_PAGE = 25
ALL = "all"
NO_ZONE = "(sin zona)"
FREE_VALUE, NEW_VALUE, ONGOING_VALUE = "free", "new", "ongoing"
# Events listed by the "Nuevos desde tu ultima visita" notice; the rest is behind its button.
NEW_NOTICE_LIMIT = 8
# How long after its start an event may end and still be shown as one session (a night that ends past midnight).
_SAME_SESSION = timedelta(hours=18)
DESCRIPTION_LIMIT = 180

# The filters as the tab opens.
DEFAULT_CONTROLS: dict[str, Any] = {
    SEARCH_ID: "",
    PERIOD_ID: DEFAULT_PERIOD,
    FROM_ID: None,
    TO_ID: None,
    CATEGORY_ID: ALL,
    ZONE_ID: ALL,
    FREE_ID: [],
    ONLY_NEW_ID: [],
    ONGOING_ID: [],
    SORT_ID: DEFAULT_SORT,
}
# The filters the "see the new ones in the table" button applies: every date, only the new ones, newest first.
NEW_VIEW_CONTROLS: dict[str, Any] = {**DEFAULT_CONTROLS, PERIOD_ID: "all", ONLY_NEW_ID: [NEW_VALUE], SORT_ID: "newest"}

_CATEGORY_COLORS = {
    "música": "success",
    "fiestas": "success",
    "deporte": "success",
    "teatro": "primary",
    "danza": "primary",
    "humor": "primary",
    "tech": "info",
    "charlas y talleres": "info",
    "infantil": "warning",
    "ferias": "danger",
    "gastronomía": "danger",
}


def _now() -> datetime:
    """The current moment in Valencia; tests replace it."""
    return datetime.now(_MADRID)


def _parse_event_moment(raw: Any) -> datetime | None:
    """Parse a timestamp that carries a time of day; anything else gives None.

    Args:
        raw: ISO timestamp with or without a zone ("...T19:30:00.000Z",
            "...T19:00:00+02:00", "...T19:30:00").

    Returns:
        The datetime, aware when the text carries a zone, or None.
    """
    text = str(raw or "").strip()
    if "T" not in text:
        return None
    # A zone name in brackets ("+02:00[Europe/Madrid]") adds nothing to the offset before it.
    try:
        return datetime.fromisoformat(text.split("[")[0].replace("Z", "+00:00"))
    except ValueError:
        return None


def _aware(moment: datetime) -> datetime:
    """A moment of Valencia: a naive one is wall-clock time there."""
    return moment.replace(tzinfo=_MADRID) if moment.tzinfo is None else moment.astimezone(_MADRID)


def _event_start(event: dict[str, Any]) -> datetime | None:
    """Return when an event starts, as a Madrid wall-clock datetime.

    A source that gives a time of day keeps it; a bare date starts at
    midnight. A UTC evening that is already the next day in Spain starts
    on that next day.

    Args:
        event: Raw event dictionary from the repository.

    Returns:
        Naive datetime in Madrid time, or None when the event has no date.
    """
    for raw in (event.get("date_text"), event.get("start_date")):
        moment = _parse_event_moment(raw)
        if moment is not None:
            # A timestamp without a zone is taken as local time.
            return moment.astimezone(_MADRID).replace(tzinfo=None) if moment.tzinfo else moment
    return _parse_event_date(str(event.get("start_date") or ""))


def _start(event: dict[str, Any]) -> datetime | None:
    """When the event starts, aware: ``start_at`` when the ETL wrote it, else the rule of the older files."""
    moment = _parse_event_moment(event.get("start_at"))
    if moment is None:
        moment = _event_start(event)
    return _aware(moment) if moment is not None else None


def _end(event: dict[str, Any]) -> datetime | None:
    """When it ends, aware: the midnight after the last day for a span; None when the source gave no end."""
    moment = _parse_event_moment(event.get("end_at"))
    if moment is not None:
        return _aware(moment)
    start, last = _start(event), _parse_event_date(str(event.get("end_date") or ""))
    if start is None or last is None or last.date() <= start.date():
        return None  # an older file: end_date is the last day, and one day is no span
    return datetime.combine(last.date() + timedelta(days=1), time(0, 0), tzinfo=_MADRID)


def _is_over(event: dict[str, Any], now: datetime) -> bool:
    """Whether the event is over at ``now``; an event without a date never is."""
    end = _end(event)
    if end is not None:
        return end <= now
    start = _start(event)
    # A timed event whose end the source did not give lasts its day.
    return start is not None and start.date() < now.date()


def _is_past(event: dict[str, Any], now: datetime) -> bool:
    """Whether the event belongs to a day before today and is over. One dated today is listed all day (T-160)."""
    start = _start(event)
    return start is not None and start.date() < now.date() and _is_over(event, now)


def _is_ongoing(event: dict[str, Any], first_day: date) -> bool:
    """Whether the event began before ``first_day`` and is still on when that day starts (an exhibition, a festival)."""
    start = _start(event)
    return start is not None and start.date() < first_day and not _is_over(event, datetime.combine(first_day, time(0, 0), tzinfo=_MADRID))


def _parse_event_date(date_str: str) -> datetime | None:
    """Parse an event date in DD/MM/YYYY or ISO (YYYY-MM-DD) format."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        # ISO format first (start_date may be YYYY-MM-DD or full ISO)
        iso_part = date_str.split("T")[0]
        if "-" in iso_part:
            parts = iso_part.split("-")
            if len(parts) == 3:
                return datetime(int(parts[0]), int(parts[1]), int(parts[2]))
        # Spanish DD/MM/YYYY
        if "/" in date_str:
            parts = date_str.split("/")
            if len(parts) == 3:
                return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
    except (ValueError, TypeError):
        pass
    return None


def _is_upcoming_event(date_str: str, now: datetime, cutoff_date: datetime) -> bool:
    """Check if an event happens between now and the cutoff date."""
    event_date = _parse_event_date(date_str)
    if event_date is None:
        return False
    # start_date is a calendar date (midnight): an event dated today is still
    # upcoming at 23:00, so the window is compared day by day (T-160).
    return now.date() <= event_date.date() <= cutoff_date.date()


def _window(period: str, today: date, date_from: Any, date_to: Any) -> tuple[date, date | None]:
    """The days a period covers: the first one, and the last one or ``None`` for no upper end.

    A custom range with one end only is open on the other side; with none it is the default week.
    """
    if period == "today":
        return today, today
    if period == "weekend":
        # Saturday to Sunday of the current week; on Sunday that is yesterday and today.
        saturday = today - timedelta(days=1) if today.weekday() == 6 else today + timedelta(days=(5 - today.weekday()) % 7)
        return saturday, saturday + timedelta(days=1)
    if period == "this_week":
        return today, today + timedelta(days=6 - today.weekday())
    if period == "this_month":
        next_month = date(today.year + (today.month == 12), today.month % 12 + 1, 1)
        return today, next_month - timedelta(days=1)
    if period == "all":
        return today, None
    if period == "custom":
        first, last = _parse_event_date(str(date_from or "")), _parse_event_date(str(date_to or ""))
        if first is None and last is None:
            return today, today + timedelta(days=6)
        first_day = first.date() if first else today
        last_day = last.date() if last else None
        if last_day is not None and last_day < first_day:
            first_day, last_day = last_day, first_day
        return first_day, last_day
    return today, today + timedelta(days=6)  # "week7", and anything unknown


def _first_detected(event: dict[str, Any]) -> datetime | None:
    """The run that first saw the event, aware; None for the files written before T-143."""
    moment = _parse_event_moment(event.get("first_detected_at"))
    return _aware(moment) if moment is not None else None


def _category(event: dict[str, Any]) -> str:
    return str(event.get("category") or "otro")


def _zone(event: dict[str, Any]) -> str:
    return str(event.get("zone") or "").strip() or NO_ZONE


def _price(event: dict[str, Any]) -> float | None:
    """The price as a number: 0 when it is free, None when no source states one."""
    price = event.get("price")
    if price is None and event.get("is_free") is True:
        return 0.0  # an older file: the source said it is free and printed no amount
    return float(price) if isinstance(price, (int, float)) and not isinstance(price, bool) else None


def _fold(text: Any) -> str:
    """Lower-case and accent-free ("Música" -> "musica"); the length does not change, so a match maps back."""
    plain = unicodedata.normalize("NFD", str(text or "").lower())
    return "".join(ch for ch in plain if not unicodedata.combining(ch))


def _metadata(event: dict[str, Any]) -> dict[str, Any]:
    """What the source added to the record (its label, whether it was carried over...)."""
    metadata = event.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _search_text(event: dict[str, Any]) -> str:
    """Where a search term is looked for: the name, the description, the place, the category and the source."""
    parts = [
        event.get("title"),
        event.get("description"),
        event.get("venue"),
        event.get("address"),
        event.get("zone"),
        _category(event),
        event.get("source"),
        _metadata(event).get("source_label"),
        " ".join(str(tag) for tag in event.get("tags") or []),
    ]
    return _fold(" ".join(str(part) for part in parts if part))


def _matches(term: str, folded: str) -> bool:
    """Every word of the term appears somewhere: "musica rusafa" finds a concert in Ruzafa."""
    return all(word in folded for word in _fold(term).split())


def _highlight(text: str, term: str) -> Any:
    """``html.Mark`` around the first word of ``term`` found in ``text``, accent-insensitively."""
    folded = _fold(text)
    for word in _fold(term).split():
        index = folded.find(word)
        if index >= 0:
            return [text[:index], html.Mark(text[index : index + len(word)]), text[index + len(word) :]]
    return text


def new_since(events: list[dict[str, Any]], stamp: datetime | None, now: datetime) -> list[dict[str, Any]]:
    """The events first detected after ``stamp`` that are still on; nothing when there is no stamp (a first visit)."""
    if stamp is None:
        return []
    return [event for event in events if (detected := _first_detected(event)) is not None and detected > stamp and not _is_past(event, now)]


def apply_filters(
    events: list[dict[str, Any]],
    *,
    now: datetime,
    period: str = DEFAULT_PERIOD,
    date_from: Any = None,
    date_to: Any = None,
    include_ongoing: bool = False,
    category: str = ALL,
    zone: str = ALL,
    free_only: bool = False,
    new_only: bool = False,
    last_visit: datetime | None = None,
    term: str = "",
) -> list[dict[str, Any]]:
    """The events the filters let through, in the order of the file (see :func:`sort_events`).

    An event is kept when it starts inside the window of the period. One that began earlier
    and is still on (an exhibition, a festival) is kept only with ``include_ongoing``; one
    that is over is never kept. An event without a date fits no window: it is kept only when
    the window has no last day ("Todas las fechas", or a custom range open at the end).

    Args:
        events: Raw event dictionaries from the repository.
        now: The current moment, aware.
        period: A value of :data:`PERIODS`.
        date_from: The first day of a custom range (ISO text), when chosen.
        date_to: The last day of a custom range (ISO text), when chosen.
        include_ongoing: Keep what began before the window and is still on.
        category: One category, or ``ALL``.
        zone: One zone, ``NO_ZONE`` or ``ALL``.
        free_only: Keep the free events only.
        new_only: Keep the events first detected after ``last_visit``.
        last_visit: The moment of the previous visit, aware.
        term: The search term.

    Returns:
        The matching events.
    """
    first_day, last_day = _window(period, now.date(), date_from, date_to)
    folded = _fold(term)
    fresh = {id(event) for event in new_since(events, last_visit, now)} if new_only else set()
    kept = []
    for event in events:
        start = _start(event)
        if start is None:
            # Without a date it fits no window: "Todas las fechas" only.
            in_window = last_day is None
        else:
            in_window = first_day <= start.date() and (last_day is None or start.date() <= last_day)
            if _is_past(event, now):
                continue
            in_window = in_window or (include_ongoing and _is_ongoing(event, first_day))
        if not in_window:
            continue
        if category != ALL and _category(event) != category:
            continue
        if zone != ALL and _zone(event) != zone:
            continue
        if free_only and _price(event) != 0:
            continue
        if new_only and id(event) not in fresh:
            continue
        if folded and not _matches(folded, _search_text(event)):
            continue
        kept.append(event)
    return kept


def _price_key(event: dict[str, Any]) -> tuple[float, float]:
    top = event.get("price_max")
    return (_price(event) or 0.0, float(top) if isinstance(top, (int, float)) and not isinstance(top, bool) else 0.0)


def _last_day_of(event: dict[str, Any]) -> date | None:
    """The last day an event is on, when it is known: an all-day span ends at the midnight after it."""
    end = _end(event)
    if end is None:
        return None
    return end.date() - timedelta(days=1) if end.time() == time(0, 0) else end.date()


def sort_events(events: list[dict[str, Any]], sort_by: str, *, first_day: date, now: datetime) -> list[dict[str, Any]]:
    """Order the filtered events.

    By date, the ones that start inside the window come first (nearest or farthest first),
    then what began earlier and is still on, the ones closing first, and the events without
    a date last. By price, the free and cheap ones first or the expensive ones first, and the
    events whose price no source states always last. "Newest" is by first detection.

    Args:
        events: Events that passed :func:`apply_filters`.
        sort_by: A value of :data:`SORTS`.
        first_day: The first day of the window, to tell what began earlier.
        now: The current moment, aware.

    Returns:
        A new list; ``events`` is left as it is.
    """
    if sort_by in ("price", "price_desc"):
        sign = -1 if sort_by == "price_desc" else 1
        return sorted(events, key=lambda event: (_price(event) is None, sign * _price_key(event)[0], sign * _price_key(event)[1], _start(event) or datetime.max.replace(tzinfo=_MADRID)))
    if sort_by == "newest":
        # Many events share a detection (one run): they keep the order by date of a first pass.
        by_date = sort_events(events, DEFAULT_SORT, first_day=first_day, now=now)
        return sorted(by_date, key=lambda event: (_first_detected(event) is not None, _first_detected(event) or datetime.min.replace(tzinfo=_MADRID)), reverse=True)
    undated = [event for event in events if _start(event) is None]
    running = [event for event in events if _start(event) is not None and _is_ongoing(event, first_day)]
    starting = [event for event in events if _start(event) is not None and not _is_ongoing(event, first_day)]
    starting.sort(key=lambda event: _start(event) or _FAR_FUTURE, reverse=sort_by == "start_desc")
    running.sort(key=lambda event: (_end(event) or _start(event), _start(event)))
    return starting + running + undated


def _format_event_date(event: dict[str, Any]) -> str:
    """Build the date shown for an event, the same way for every source.

    A calendar date prints as the weekday and DD/MM/YYYY ("vie 27/11/2026"),
    a timed start adds its Madrid hour ("sáb 28/11/2026, 15:00") and the end
    date follows when it differs from the start. Without a parseable date the
    text of the source is kept, or "N/A" when there is none.
    """
    start = _event_start(event)
    if start is None:
        raw = str(event.get("date_text") or "").strip()
        return raw.replace("Del ", "").replace(" al ", " – ") if raw else "N/A"
    text = f"{_WEEKDAYS[start.weekday()]} {start.strftime('%d/%m/%Y')}"
    if start.time() != time(0, 0):
        text += f" · {start.strftime('%H:%M')}"
    end = _parse_event_date(str(event.get("end_date") or ""))
    if end and end > start:
        text += f" – {end.strftime('%d/%m/%Y')}"
    return text


def sort_events_by_start(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order events by start; the ones without a date keep their order at the end."""
    return sorted(events, key=lambda event: _event_start(event) or datetime.max)


def _when_text(event: dict[str, Any]) -> str:
    """The date and hour shown in the table: the readable local form, and how long it runs."""
    text = str(event.get("start_local") or "").strip()
    if not text:
        return _format_event_date(event)  # an older file: the rule that always applied
    start, end = _start(event), _end(event)
    if start is None or end is None:
        return text
    if end.time() == time(0, 0):
        last_day = end.date() - timedelta(days=1)  # an all-day span ends at the midnight after its last day
        return f"{text} – {last_day:%d/%m/%Y}" if last_day > start.date() else text
    if end.date() == start.date() or end - start <= _SAME_SESSION:
        return f"{text} – {end:%H:%M}"  # the same day, or a night that ends after midnight: still one session
    return f"{text} – {end:%d/%m/%Y %H:%M}"


def format_local_short(moment: datetime) -> str:
    """``sáb 28/11/2026 · 18:00``: the readable Valencia form the ETL writes too."""
    return f"{_WEEKDAYS[moment.weekday()]} {moment:%d/%m/%Y} · {moment:%H:%M}"


def _format_amount(value: float, currency: str = "EUR") -> str:
    """A price the Spanish way: ``12,5 €``, ``1.234 €``, ``15 $``."""
    whole, _, decimals = f"{value:.2f}".partition(".")
    whole = f"{int(whole):,}".replace(",", ".")
    decimals = decimals.rstrip("0")
    amount = f"{whole},{decimals}" if decimals else whole
    symbol = {"EUR": "€", "USD": "$", "GBP": "£"}.get(str(currency or "EUR").upper(), "")
    return f"{amount} {symbol}" if symbol else f"{amount} {currency}".strip()


def _truncate(text: str, limit: int = DESCRIPTION_LIMIT) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _event_cell(event: dict[str, Any], term: str = "") -> html.Div:
    """Title, description and source; the wrapper carries the first detection for valencia_state.js."""
    title = str(event.get("title") or "Sin título")
    url = str(event.get("url") or "")
    body: Any = _highlight(title, term)
    metadata = _metadata(event)
    children: list[Any] = [html.A(body, href=url, target="_blank", rel="noopener", className="fw-bold text-decoration-none text-info") if url else html.Span(body, className="fw-bold")]
    # Plain text whatever an older file holds: markup would show as tags.
    description = plain_excerpt(str(event.get("description") or ""), DESCRIPTION_LIMIT)
    if description:
        children.append(html.Div(description, className="small text-muted"))
    labels: list[Any] = []
    if metadata.get("carried_over"):
        labels.append(dbc.Badge("sin confirmar", color="secondary", pill=True, className="me-1", title="Su agenda no respondió en la última ejecución: dato de la anterior."))
    source = str(metadata.get("source_label") or event.get("source") or "").strip()
    if source:
        labels.append(html.Span(f"Fuente: {source}", className="small text-muted"))
    if labels:
        children.append(html.Div(labels))
    detected = str(event.get("first_detected_at") or "")
    attributes: dict[str, Any] = {"data-valencia-detected": detected} if detected else {}
    return html.Div(children, className="wt-valencia-event", **attributes)


def _ongoing_note(event: dict[str, Any], now: datetime) -> Any:
    """``en curso hasta 20/01/2027`` for what began before today and is still on."""
    if not _is_ongoing(event, now.date()):
        return None
    last_day = _last_day_of(event)
    return html.Span(" · en curso" + (f" hasta {last_day:%d/%m/%Y}" if last_day else ""), className="text-info")


def _when_cell(event: dict[str, Any], now: datetime) -> html.Div:
    return html.Div([html.Span(_when_text(event), className="text-nowrap"), _ongoing_note(event, now)], className="small")


def _where_cell(event: dict[str, Any], term: str = "") -> Any:
    """The venue, its zone and the address the source prints; a dash when it names no place."""
    venue = str(event.get("venue") or "").strip()
    address = str(event.get("address") or "").strip()
    zone = str(event.get("zone") or "").strip()
    if not (venue or address or zone):
        return html.Span("—", className="text-muted")
    children: list[Any] = [html.Div(_highlight(venue, term)) if venue else html.Div("—", className="text-muted")]
    if address and address != venue:
        children.append(html.Div(_truncate(address, 80), className="small text-muted"))
    if zone:
        children.append(dbc.Badge(zone, color="secondary", pill=True, className="small"))
    return html.Div(children)


def _price_cell(event: dict[str, Any]) -> Any:
    """The price the source states; a dash when none does, never a guess."""
    value = _price(event)
    if value == 0:
        return dbc.Badge("Gratis", color="success", pill=True, className="px-2 py-1 text-uppercase small")
    if value is not None:
        currency = str(event.get("currency") or "EUR")
        top = event.get("price_max")
        text = f"{_format_amount(value, currency)} – {_format_amount(float(top), currency)}" if isinstance(top, (int, float)) and top > value else _format_amount(value, currency)
        return html.Span(text, className="text-nowrap")
    info = str(event.get("price_info") or "").strip()
    if info:
        return html.Span(info, className="text-nowrap small text-muted")
    return html.Span("—", className="text-muted", title="La fuente no indica el precio")


def _category_cell(event: dict[str, Any]) -> dbc.Badge:
    category = _category(event)
    return dbc.Badge(category, color=_CATEGORY_COLORS.get(category, "secondary"), pill=True, className="px-2 py-1 text-uppercase small")


def build_events_table(events: list[dict[str, Any]], term: str = "", now: datetime | None = None) -> Any:
    """The table of one page of events; an alert when the page is empty."""
    now = now or _now()
    columns = [
        {"header": "Evento", "cell": lambda event: _event_cell(event, term)},
        {"header": "Cuándo", "cell": lambda event: _when_cell(event, now)},
        {"header": "Dónde", "cell": lambda event: _where_cell(event, term)},
        {"header": "Precio", "cell": _price_cell},
        {"header": "Categoría", "cell": _category_cell},
    ]
    return render_items_table(events, columns, empty_message="Ningún evento en esta página.", size="sm")


def _count_line(total: int, free: int) -> html.Div:
    """How many events the filters let through, and how many of them are free."""
    text = f"{total} eventos" if total != 1 else "1 evento"
    return html.Div([html.Strong(text), html.Span(f" · {free} gratis", className="text-muted")], className="mb-2")


def _empty_state(*, only_new: bool, last_visit: datetime | None) -> dbc.Alert:
    """What to say when nothing matches."""
    if only_new and last_visit is None:
        return dbc.Alert(
            [
                html.H5("Todavía no hay una visita anterior", className="alert-heading"),
                html.P("Este navegador aún no guardó cuándo abriste la pestaña por última vez. La próxima vez que la abras aparecerán aquí los eventos detectados desde entonces.", className="mb-0"),
            ],
            color="info",
            className="mt-3",
        )
    return dbc.Alert(
        [
            html.H5("Ningún evento con estos filtros", className="alert-heading"),
            html.P("Prueba a ampliar las fechas o a quitar algún filtro. «Limpiar filtros» los deja como al abrir la pestaña.", className="mb-0"),
        ],
        color="info",
        className="mt-3",
    )


def _no_data_alert() -> dbc.Alert:
    return dbc.Alert(
        [
            html.H4("Todavía no hay eventos de València", className="alert-heading"),
            html.P("El ETL de eventos aún no ha guardado nada. Vuelve a abrir la pestaña después de la siguiente ejecución del ciclo.", className="mb-0"),
        ],
        color="info",
    )


def _error_alert(action: str, error: Exception) -> dbc.Alert:
    return dbc.Alert([html.H5(f"No se pudo {action}", className="alert-heading"), html.P(str(error), className="mb-0 small")], color="danger", className="mt-3")


def build_new_notice(events: list[dict[str, Any]], stamp: datetime | None, now: datetime) -> tuple[Any, str]:
    """The "Nuevos desde tu última visita" notice: what to show, and the label of the button that shows the rest.

    Args:
        events: Raw event dictionaries from the repository.
        stamp: The moment of the previous visit, aware; None when this is the first one.
        now: The current moment, aware.

    Returns:
        ``(children, button_label)``: the list of the new events (at most :data:`NEW_NOTICE_LIMIT`,
        then how many more) and the label of the button that lists them all in the table; empty
        strings when there is nothing new or no earlier visit.
    """
    fresh = new_since(events, stamp, now)
    if stamp is None or not fresh:
        return "", ""
    items = []
    for event in fresh[:NEW_NOTICE_LIMIT]:
        url = str(event.get("url") or "")
        parts: list[Any] = [
            html.A(str(event.get("title") or "Sin título"), href=url, target="_blank", rel="noopener", className="text-info text-decoration-none") if url else html.Span(str(event.get("title") or "Sin título"))
        ]
        when = _when_text(event)
        if when:
            parts.append(html.Span(when, className="text-muted"))
        venue = str(event.get("venue") or "").strip()
        if venue:
            parts.append(html.Span(venue, className="text-muted"))
        if _price(event) == 0:
            parts.append(dbc.Badge("Gratis", color="success", pill=True, className="small"))
        items.append(html.Li(_join(parts, " · ")))
    more = len(fresh) - NEW_NOTICE_LIMIT
    header = html.Div([html.Span("🆕 "), html.Strong(f"Nuevos desde tu última visita: {len(fresh)} {'evento' if len(fresh) == 1 else 'eventos'}")], className="mb-2")
    children: list[Any] = [header, html.Ul(items, className="mb-0 ps-3")]
    if more > 0:
        children.append(html.Div(f"… y {more} más", className="small text-muted mt-1"))
    return children, "Ver el nuevo en la tabla" if len(fresh) == 1 else f"Ver los {len(fresh)} nuevos en la tabla"


def _join(parts: list[Any], separator: str) -> list[Any]:
    """``[a, b, c]`` with the separator between the parts that are not None."""
    joined: list[Any] = []
    for part in parts:
        if part is None:
            continue
        joined += [separator, part] if joined else [part]
    return joined


def _source_status_note() -> Any:
    """Which agendas answered in the last run, in one muted line; nothing when the ETL wrote no status."""
    status = load_sources_status()
    sources = [source for source in status.get("sources", []) if isinstance(source, dict)] if isinstance(status.get("sources"), list) else []
    if not sources:
        return ""
    silent = [str(source.get("label") or "?") for source in sources if source.get("status") != "ok"]
    text = f"{len(sources) - len(silent)} de {len(sources)} agendas respondieron"
    updated = _parse_event_moment(status.get("updated_at"))
    if updated is not None:
        text += f" · datos del {format_local_short(_aware(updated))}"
    if silent:
        return html.Div([text, " · ", html.Span("sin datos de: " + ", ".join(silent), className="text-warning")], className="small")
    return html.Div(text, className="small text-muted")


def _stat_cards(events: list[dict[str, Any]], now: datetime) -> dbc.Row:
    """Four counts over every event still on, whatever the filters say."""
    live = [event for event in events if not _is_past(event, now)]
    prices = [_price(event) for event in live]
    any_price = any(price is not None for price in prices)
    saturday = _window("weekend", now.date(), None, None)[0]

    def _starts(first: date, last: date) -> int:
        return sum(1 for event in live if (start := _start(event)) is not None and first <= start.date() <= last)

    # "Gratis" counts only when some source states a price: without one, a 0 would read as "nothing is free".
    stats = [
        (str(len(live)), "Eventos próximos"),
        (str(prices.count(0.0)) if any_price else "—", "Gratis" if any_price else "Gratis (sin datos de precio)"),
        (str(_starts(now.date(), now.date())), "Empiezan hoy"),
        (str(_starts(saturday, saturday + timedelta(days=1))), "Este fin de semana"),
    ]
    cards = [
        dbc.Col(
            dbc.Card(dbc.CardBody([html.H4(value, className="card-title mb-0"), html.P(label, className="card-text text-muted small mb-0")]), className="h-100 border border-secondary text-light"),
            xs=6,
            md=3,
            className="mb-3",
        )
        for value, label in stats
    ]
    return dbc.Row(cards, className="mb-3 g-3")


def _select(control_id: str, label: str, options: list[dict[str, Any]], value: Any) -> html.Div:
    return html.Div([html.Label(label, className="small text-muted mb-1", htmlFor=control_id), dbc.Select(id=control_id, options=options, value=value)])


def _date_input(control_id: str, label: str, today: date) -> html.Div:
    return html.Div([html.Label(label, className="small text-muted mb-1", htmlFor=control_id), dbc.Input(id=control_id, type="date", min=today.isoformat(), debounce=True)])


def _options_with_counts(counter: Counter, everything: str, *, last: str = "") -> list[dict[str, Any]]:
    """``"Todas las categorías"``, then every value with its count, the most frequent first."""
    by_count = sorted(counter.items(), key=lambda item: (-item[1], _fold(item[0])))
    if last and last in counter:
        by_count = [item for item in by_count if item[0] != last] + [(last, counter[last])]
    return [{"label": everything, "value": ALL}] + [{"label": f"{name} ({count})", "value": name} for name, count in by_count]


def _filters_bar(events: list[dict[str, Any]], now: datetime) -> html.Div:
    """Search, dates, order, page size, category, zone, the three switches and the clear button."""
    live = [event for event in events if not _is_past(event, now)]
    today = now.date()
    search = create_search_input(SEARCH_ID, placeholder="Nombre, lugar, categoría… (vale sin tildes)", debounce=400)
    search.className = ""  # inside the bar the row sets the spacing, not the group
    label = "small text-muted mb-1"
    switches = [
        dbc.Checklist(id=control_id, options=[{"label": text, "value": value}], value=[], switch=True, className="mb-0")
        for control_id, text, value in ((FREE_ID, "Solo gratis", FREE_VALUE), (ONLY_NEW_ID, "Solo los nuevos desde mi última visita", NEW_VALUE), (ONGOING_ID, "Incluir lo que ya ha empezado", ONGOING_VALUE))
    ]
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col([html.Label("Buscar", className=label, htmlFor=SEARCH_ID), search], xs=12, lg=5),
                    dbc.Col(_select(PERIOD_ID, "Cuándo", PERIODS, DEFAULT_PERIOD), xs=6, lg=3),
                    dbc.Col(_select(SORT_ID, "Orden", SORTS, DEFAULT_SORT), xs=6, lg=2),
                    dbc.Col(_select(PER_PAGE_ID, "Por página", [{"label": str(number), "value": number} for number in PER_PAGE_OPTIONS], DEFAULT_PER_PAGE), xs=6, lg=2),
                ],
                className="g-3 mb-2",
            ),
            html.Div(
                dbc.Row([dbc.Col(_date_input(FROM_ID, "Desde", today), xs=6, md=3), dbc.Col(_date_input(TO_ID, "Hasta", today), xs=6, md=3)], className="g-3"), id=RANGE_ROW_ID, hidden=True, className="mb-2"
            ),
            dbc.Row(
                [
                    dbc.Col(_select(CATEGORY_ID, "Categoría", _options_with_counts(Counter(_category(event) for event in live), "Todas las categorías"), ALL), xs=12, md=4),
                    dbc.Col(_select(ZONE_ID, "Zona", _options_with_counts(Counter(_zone(event) for event in live), "Todas las zonas", last=NO_ZONE), ALL), xs=12, md=4),
                    dbc.Col(html.Div(switches, className="d-flex flex-column gap-1 pt-1 h-100"), xs=12, md=3),
                    dbc.Col(dbc.Button("Limpiar filtros", id=CLEAR_ID, color="outline-secondary", size="sm"), xs=12, md=1, className="d-flex align-items-end"),
                ],
                className="g-3",
            ),
        ],
        className="valencia-filters border rounded-3 p-3 mb-3",
    )


def _header(ics_events: list[dict[str, Any]], ics_payload: str, *, with_payload: bool = True) -> dbc.Row:
    """Title, and the clientside .ics export (T-068): a hidden payload Div when there is data, the button when there is something to export."""
    return dbc.Row(
        [
            dbc.Col(
                [
                    html.H2("🌆 Eventos en València", className="mb-1"),
                    html.P("Qué hacer en València los próximos días, reunido de agendas públicas: música, teatro, arte, tech, ferias, deporte y más.", className="text-muted mb-0"),
                ],
                md=8,
            ),
            dbc.Col(
                [
                    # data-* wildcard props are valid at runtime but absent from Dash's generated stubs
                    *([html.Div(id="valencia-ics-events", hidden=True, **{"data-events": ics_payload})] if with_payload else []),  # type: ignore[arg-type]
                    *(
                        [
                            dbc.Button(
                                f"⬇ .ics ({len(ics_events)})",
                                id="valencia-ics-export-btn",
                                color="outline-secondary",
                                size="sm",
                                className="mb-3",
                                title="Descargar los eventos desde hoy como archivo de calendario (.ics)",
                            )
                        ]
                        if ics_events
                        else []
                    ),
                ],
                width="auto",
                className="d-flex align-items-end ms-md-auto",
            ),
        ],
        className="mb-3 g-3",
    )


def _new_visit_box() -> html.Div:
    """The notice the server fills, and its two buttons. The whole box is hidden until the browser hands over the previous visit.

    Both buttons are always in the page (``hidden`` on the box, never removed): one is an Input of the
    controller, and a callback whose Input is missing never runs.
    """
    return html.Div(
        [
            html.Div(id=NOTICE_ID),
            html.Div(
                [
                    dbc.Button("Marcar como vistos", id=MARK_SEEN_ID, color="outline-secondary", size="sm", className="me-2", title="No volver a mostrar estos eventos como nuevos"),
                    dbc.Button("", id=SHOW_ALL_ID, color="secondary", size="sm"),
                ],
                className="mt-2",
            ),
        ],
        id=NEW_BOX_ID,
        hidden=True,
        className="valencia-new-box border-start border-4 rounded-3 p-3 mb-3",
        style={"borderColor": "#A37FFF"},
    )


def _per_page(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PER_PAGE
    return number if number in PER_PAGE_OPTIONS else DEFAULT_PER_PAGE


def _view(events: list[dict[str, Any]], *, now: datetime, controls: dict[str, Any], last_visit: datetime | None, page: int, per_page: int) -> tuple[list[Any], Any, int]:
    """What the results area shows for one set of filters: the count and the page, the pager, the page number."""
    only_new = NEW_VALUE in (controls[ONLY_NEW_ID] or [])
    matched = apply_filters(
        events,
        now=now,
        period=controls[PERIOD_ID],
        date_from=controls[FROM_ID],
        date_to=controls[TO_ID],
        include_ongoing=ONGOING_VALUE in (controls[ONGOING_ID] or []),
        category=controls[CATEGORY_ID] or ALL,
        zone=controls[ZONE_ID] or ALL,
        free_only=FREE_VALUE in (controls[FREE_ID] or []),
        new_only=only_new,
        last_visit=last_visit,
        term=str(controls[SEARCH_ID] or ""),
    )
    first_day = _window(controls[PERIOD_ID] or DEFAULT_PERIOD, now.date(), controls[FROM_ID], controls[TO_ID])[0]
    ordered = sort_events(matched, controls[SORT_ID] or DEFAULT_SORT, first_day=first_day, now=now)
    page_items, total_pages, page = paginate(ordered, page, per_page)
    if page_items:
        results: list[Any] = [_count_line(len(ordered), sum(1 for event in ordered if _price(event) == 0)), build_events_table(page_items, str(controls[SEARCH_ID] or ""), now)]
    elif events:
        results = [_empty_state(only_new=only_new, last_visit=last_visit)]
    else:
        results = [_no_data_alert()]
    if page_items:
        label = f"Mostrando {(page - 1) * per_page + 1}–{(page - 1) * per_page + len(page_items)} de {len(ordered)} · Página {page} de {total_pages}"
    else:
        label = "0 eventos"
    return results, pagination_controls("valencia", page, total_pages, len(page_items), len(ordered), id_prefix="valencia", label=label), page


def render_valencia_events_tab() -> html.Div:
    """Return the default view of the tab; called every time it is selected."""
    try:
        events = sort_events_by_start(load_valencia_events())
        now = _now()
        ics_events = _exportable_upcoming_events(events, now)
        ics_payload = json.dumps(_build_ics_payload(ics_events), ensure_ascii=False, separators=(",", ":"))
        if not events:
            return html.Div([_header([], "", with_payload=False), _no_data_alert()], className="p-4")
        results, pager, page = _view(events, now=now, controls=DEFAULT_CONTROLS, last_visit=None, page=1, per_page=DEFAULT_PER_PAGE)
        return html.Div(
            [
                _header(ics_events, ics_payload),
                _source_status_note(),
                _new_visit_box(),
                _stat_cards(events, now),
                _filters_bar(events, now),
                html.Div(results, id=RESULTS_ID),
                html.Div(pager, id=PAGER_ID),
                dcc.Store(id=PAGE_STORE_ID, data=page),
                dcc.Store(id=LAST_VISIT_ID),
            ],
            className="p-4",
        )
    except Exception as e:
        logger.error(f"Error rendering Valencia events tab: {e}")
        return html.Div([dbc.Alert(f"Error al cargar los eventos de València: {e!s}", color="danger")], className="p-4")


def _visit_stamp(data: Any) -> datetime | None:
    """The moment valencia_state.js hands over through the store: ``{"stamp": ISO, "n": n}``."""
    raw = data.get("stamp") if isinstance(data, dict) else data
    moment = _parse_event_moment(raw)
    return _aware(moment) if moment is not None else None


def _plan(triggered: Any, prev_clicks: Any, next_clicks: Any, clear_clicks: Any, show_all_clicks: Any, search_clear: Any, current_page: Any) -> tuple[int, dict[str, Any] | None]:
    """The page to show and, when a button asks for it, the filters to apply.

    Raises:
        PreventUpdate: When the call is not a user action (a button shown, not clicked).
    """
    if not dash.ctx.triggered:
        raise PreventUpdate
    page = int(current_page or 1)
    if triggered in (PREV_ID, NEXT_ID):
        if not (next_clicks if triggered == NEXT_ID else prev_clicks):
            raise PreventUpdate
        return page + (1 if triggered == NEXT_ID else -1), None
    if triggered == CLEAR_ID:
        if not clear_clicks:
            raise PreventUpdate
        return 1, dict(DEFAULT_CONTROLS)
    if triggered == SHOW_ALL_ID:
        if not show_all_clicks:
            raise PreventUpdate
        return 1, dict(NEW_VIEW_CONTROLS)
    if triggered == SEARCH_CLEAR_ID and not search_clear:
        raise PreventUpdate
    return 1, None  # any filter changed: back to the first page


def register_valencia_events_callbacks(app: Dash) -> None:
    """Wire the tab: one controller for the table and the filters, one callback for the "new since your last visit" notice."""

    @app.callback(
        Output(RESULTS_ID, "children"),
        Output(PAGER_ID, "children"),
        Output(PAGE_STORE_ID, "data"),
        Output(SEARCH_ID, "value"),
        Output(PERIOD_ID, "value"),
        Output(FROM_ID, "value"),
        Output(TO_ID, "value"),
        Output(RANGE_ROW_ID, "hidden"),
        Output(CATEGORY_ID, "value"),
        Output(ZONE_ID, "value"),
        Output(FREE_ID, "value"),
        Output(ONLY_NEW_ID, "value"),
        Output(ONGOING_ID, "value"),
        Output(SORT_ID, "value"),
        Input(SEARCH_ID, "value"),
        Input(SEARCH_CLEAR_ID, "n_clicks"),
        Input(PERIOD_ID, "value"),
        Input(FROM_ID, "value"),
        Input(TO_ID, "value"),
        Input(CATEGORY_ID, "value"),
        Input(ZONE_ID, "value"),
        Input(FREE_ID, "value"),
        Input(ONLY_NEW_ID, "value"),
        Input(ONGOING_ID, "value"),
        Input(SORT_ID, "value"),
        Input(PER_PAGE_ID, "value"),
        Input(PREV_ID, "n_clicks"),
        Input(NEXT_ID, "n_clicks"),
        Input(CLEAR_ID, "n_clicks"),
        Input(SHOW_ALL_ID, "n_clicks"),
        State(PAGE_STORE_ID, "data"),
        State(LAST_VISIT_ID, "data"),
        prevent_initial_call=True,
    )
    def update_results(
        search, search_clear, period, date_from, date_to, category, zone, free, only_new, ongoing, sort_by, per_page, prev_clicks, next_clicks, clear_clicks, show_all_clicks, current_page, last_visit
    ):
        """Rebuild the results for the filters as they stand. ``Limpiar filtros`` and the notice's button also reset the controls."""
        unchanged = dash.no_update
        # The "x" of the search box empties the term; the box itself holds it still.
        search_cleared = dash.ctx.triggered_id == SEARCH_CLEAR_ID
        try:
            page, new_controls = _plan(dash.ctx.triggered_id, prev_clicks, next_clicks, clear_clicks, show_all_clicks, search_clear, current_page)
            controls = (
                new_controls
                if new_controls is not None
                else {
                    SEARCH_ID: "" if search_cleared else (search or ""),
                    PERIOD_ID: period or DEFAULT_PERIOD,
                    FROM_ID: date_from,
                    TO_ID: date_to,
                    CATEGORY_ID: category or ALL,
                    ZONE_ID: zone or ALL,
                    FREE_ID: list(free or []),
                    ONLY_NEW_ID: list(only_new or []),
                    ONGOING_ID: list(ongoing or []),
                    SORT_ID: sort_by or DEFAULT_SORT,
                }
            )
            results, pager, page = _view(load_valencia_events(), now=_now(), controls=controls, last_visit=_visit_stamp(last_visit), page=page, per_page=_per_page(per_page))
        except PreventUpdate:
            raise
        except Exception as exc:  # show the failure in the tab instead of breaking the app
            logger.exception("Valencia events: the results could not be rebuilt")
            return (_error_alert("actualizar la lista de eventos", exc), *([unchanged] * 13))
        # A filter change leaves the controls as they are; the two buttons set them back.
        shown = [unchanged] * 10 if new_controls is None else [controls[key] for key in (SEARCH_ID, PERIOD_ID, FROM_ID, TO_ID, CATEGORY_ID, ZONE_ID, FREE_ID, ONLY_NEW_ID, ONGOING_ID, SORT_ID)]
        if search_cleared:
            shown[0] = ""
        return results, pager, page, *shown[:4], controls[PERIOD_ID] != "custom", *shown[4:]

    @app.callback(
        Output(NOTICE_ID, "children"),
        Output(NEW_BOX_ID, "hidden"),
        Output(SHOW_ALL_ID, "children"),
        Input(LAST_VISIT_ID, "data"),
        prevent_initial_call=True,
    )
    def update_new_notice(last_visit: Any) -> tuple[Any, ...]:
        """List the events first detected after the visit the browser hands over; "Marcar como vistos" hands over now."""
        stamp = _visit_stamp(last_visit)
        try:
            notice, label = build_new_notice(load_valencia_events(), stamp, _now())
        except Exception as exc:  # show the failure in the tab instead of breaking the app
            logger.exception("Valencia events: the notice could not be built")
            return _error_alert("calcular los eventos nuevos", exc), False, dash.no_update
        if not notice:
            return "", True, dash.no_update
        return notice, False, label


# --- the clientside .ics export (T-068) -------------------------------------------------------------


def _exportable_upcoming_events(events: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    """Return the events eligible for the .ics export: parseable start date today or later.

    Whatever the filters of the tab show, the calendar export keeps every
    future event ("from today", no upper cutoff). Events whose start_date
    cannot be parsed are skipped (they cannot become VEVENTs).

    Args:
        events: Raw event dictionaries from the repository.
        now: Reference datetime; events dated before its day are excluded.

    Returns:
        List of event dictionaries, original order preserved.
    """
    # Compared day by day: ``now`` may be aware (the tab's clock) and the parsed date never is.
    today = now.date()
    exportable: list[dict[str, Any]] = []
    for event in events:
        parsed = _parse_event_date(str(event.get("start_date") or ""))
        if parsed is not None and parsed.date() >= today:
            exportable.append(event)
    return exportable


def _build_ics_payload(events: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build the compact JSON payload consumed by the clientside .ics exporter.

    Only the fields the JS VCALENDAR builder needs are kept so the embedded
    data-events attribute stays small. The location prefers the extracted
    venue name (T-080), falling back to the event location or metadata
    (venue/location keys) when present.

    Args:
        events: Exportable event dictionaries (already filtered to upcoming).

    Returns:
        List of dicts with title/start_date/end_date/url and, when available,
        location.
    """
    payload: list[dict[str, str]] = []
    for event in events:
        metadata = event.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        location = str(event.get("venue") or event.get("location") or metadata.get("venue") or metadata.get("location") or "")
        item = {
            "title": str(event.get("title") or "Untitled"),
            "start_date": str(event.get("start_date") or ""),
            "end_date": str(event.get("end_date") or ""),
            "url": str(event.get("url") or ""),
        }
        if location:
            item["location"] = location
        payload.append(item)
    return payload
