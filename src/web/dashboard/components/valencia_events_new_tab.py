"""New Valencia Events Tab Component with Subtabs for Watchtower Dashboard"""

import json
import logging
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dash_bootstrap_components as dbc
from dash import html

# Import repository pattern (NEW)
from src.repositories import BaseRepository
from src.web.dashboard.utils import get_data_path

# Set up logging
logger = logging.getLogger(__name__)

# Data file paths
VALENCIA_EVENTS_FILE = Path(get_data_path("valencia_events", "valencia_events.json"))


# NEW: Repository-based loading (SOLID Pattern)
class ValenciaEventsNewRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for Valencia events data (new tab)."""

    def __init__(self):
        """Initialize Valencia events repository (new tab)."""
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
    """Load Valencia events data using repository pattern (NEW)."""
    try:
        events = valencia_events_new_repo.get()
        logger.info(f"Loaded {len(events)} Valencia events from {VALENCIA_EVENTS_FILE}")
        return events
    except Exception as e:
        logger.error(f"Error loading Valencia events: {e}")
        return []


# Events are shown in the local time of the city. Meetup prints its start
# times in UTC ("2026-11-27T19:30:00.000Z"); visitvalencia and Eventbrite
# give calendar dates, which need no conversion.
_MADRID = ZoneInfo("Europe/Madrid")
_WEEKDAYS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")


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


def sort_events_by_start(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order events by start; the ones without a date keep their order at the end."""
    return sorted(events, key=lambda event: _event_start(event) or datetime.max)


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


def create_event_card(event: dict[str, Any]) -> dbc.Card:
    """Create a card component for a single event"""
    try:
        title = event.get("title", "Untitled")
        description = event.get("description", "No description available")
        category = event.get("category", "General")
        date_display = _format_event_date(event)
        url = event.get("url", "")
        source = event.get("source", "Valencia")

        # Determine event type badge color
        badge_color = "primary"
        if category.lower() in ["tecnología", "tech", "technology"]:
            badge_color = "info"
        elif category.lower() in ["música", "music"]:
            badge_color = "success"
        elif category.lower() in ["gastronomía", "food"]:
            badge_color = "warning"
        elif category.lower() in ["exposición", "exhibition"]:
            badge_color = "secondary"

        card_header = dbc.CardHeader(
            [
                html.Div(
                    [
                        html.H5(title, className="mb-1"),
                        html.Div(
                            [
                                dbc.Badge(category, color=badge_color, pill=True, className="me-2 px-2 py-1 text-uppercase small"),
                            ]
                        ),
                    ]
                )
            ]
        )

        card_body_content = [
            html.P(description, className="card-text mb-3"),
            html.Div([html.Strong("📅 Date: "), html.Span(date_display)], className="mb-2"),
            html.Div([html.Strong("🏷️ Source: "), html.Span(source)], className="mb-3"),
            # Action button
            (
                dbc.Button(
                    "View more information",
                    href=url,
                    target="_blank",
                    color="outline-primary",
                    size="sm",
                    disabled=not url,
                )
                if url
                else html.Span("No link available", className="text-muted")
            ),
        ]

        return dbc.Card([card_header, dbc.CardBody(card_body_content)], className="mb-3 h-100")

    except Exception as e:
        logger.error(f"Error creating event card: {e}")
        return dbc.Card(
            dbc.CardBody(
                [
                    html.H4("Error Loading Event", className="card-title"),
                    html.P(f"Error: {e!s}", className="card-text"),
                ]
            ),
            className="mb-3",
        )


def create_events_table(events: list[dict[str, Any]]) -> dbc.Table:
    """Create a table view of events (News Tab Style)"""
    try:
        if not events:
            return dbc.Alert("No events available", color="info")

        # Table Header
        table_header = [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Title"),
                        html.Th("Category"),
                        html.Th("Date"),
                        html.Th("Venue"),
                        html.Th("Price"),
                        html.Th("Source"),
                        html.Th("Link"),
                    ]
                )
            )
        ]

        # Table Body
        table_body_rows = []
        for event in events:
            title = event.get("title", "Untitled")
            description = event.get("description", "")
            category = event.get("category", "General")
            date_text_short = _format_event_date(event)
            source = event.get("source", "Valencia")
            url = event.get("url", "#")

            # Determine badge color
            badge_color = "primary"
            cat_lower = category.lower()
            if "tech" in cat_lower or "tecnología" in cat_lower:
                badge_color = "info"
            elif "música" in cat_lower or "music" in cat_lower:
                badge_color = "success"
            elif "gastronomía" in cat_lower:
                badge_color = "warning"
            elif "exposición" in cat_lower or "exhibition" in cat_lower:
                badge_color = "secondary"

            # Truncate long descriptions
            desc_short = (description[:100] + "…") if len(description) > 100 else description

            # Venue + price (T-080): venue comes from the JSON-LD Place name;
            # price is only claimed when the source exposed offers (is_free
            # set) — absent data stays an honest "—" instead of a fake Gratis.
            venue = str(event.get("venue") or "").strip()
            price_info = str(event.get("price_info") or "").strip()

            table_body_rows.append(
                html.Tr(
                    [
                        html.Td(
                            [
                                html.Div(title, className="fw-bold", style={"maxWidth": "350px"}),
                                html.Small(desc_short, className="text-muted d-inline-block", style={"maxWidth": "350px"}),
                            ]
                        ),
                        html.Td(dbc.Badge(category, color=badge_color, pill=True, className="px-2 py-1 text-uppercase small")),
                        html.Td(html.Span(date_text_short, className="text-nowrap small")),
                        html.Td(html.Span(venue, className="small") if venue else html.Span("—", className="text-muted")),
                        html.Td(
                            dbc.Badge("Gratis", color="success", pill=True, className="px-2 py-1 text-uppercase small")
                            if event.get("is_free") is True
                            else html.Span(price_info, className="text-nowrap small text-muted")
                            if price_info
                            else html.Span("—", className="text-muted")
                        ),
                        html.Td(html.Span(source, className="small")),
                        html.Td(
                            dbc.Button(
                                "🔗 View",
                                href=url,
                                target="_blank",
                                color="outline-primary",
                                size="sm",
                            )
                            if url
                            else html.Span("—", className="text-muted")
                        ),
                    ]
                )
            )

        table_body = [html.Tbody(table_body_rows)]

        return dbc.Table(
            table_header + table_body,
            bordered=True,
            hover=True,
            responsive=True,
            striped=True,
            size="sm",
            color="dark",
            className="table-responsive mb-0",
        )

    except Exception as e:
        logger.error(f"Error creating events table: {e}")
        return dbc.Alert(f"Error creating table: {e!s}", color="danger")


def render_valencia_events_tab() -> html.Div:
    """Render the Valencia events tab with subtabs"""
    try:
        # The sources list in their own order: the tab goes by start date.
        events_data = sort_events_by_start(load_valencia_events())

        if not events_data:
            return html.Div(
                [
                    dbc.Alert(
                        [
                            html.H4(
                                "No Valencia events available",
                                className="alert-heading",
                            ),
                            html.P("No event data found. Run the Valencia ETL to populate data."),
                            html.Hr(),
                            html.P(
                                f"Expected location: {VALENCIA_EVENTS_FILE}",
                                className="mb-0",
                            ),
                        ],
                        color="info",
                    )
                ],
                className="p-4",
            )

        # Filter data for different views
        tech_events_data = [e for e in events_data if "tech" in e.get("category", "").lower() or "tecnología" in e.get("category", "").lower()]

        _now = datetime.now()
        upcoming_events_data = [e for e in events_data if e.get("start_date") and _is_upcoming_event(e.get("start_date", ""), _now, _now + timedelta(days=30))]

        # Clientside .ics export payload (T-068): upcoming-from-today events
        # embedded as compact JSON for the assets/js/valencia_ics.js handler.
        ics_events = _exportable_upcoming_events(events_data, _now)
        ics_payload = json.dumps(_build_ics_payload(ics_events), ensure_ascii=False, separators=(",", ":"))

        # Statistics
        total_events = len(events_data)
        categories = {event.get("category", "General") for event in events_data}
        tech_events_count = len(tech_events_data)
        # is_free (T-080) is only set when the source actually exposes a price
        # via JSON-LD offers; a missing value must not count as free (or paid).
        free_events = len([e for e in events_data if e.get("is_free") is True]) if any(e.get("is_free") is not None for e in events_data) else None

        def _stat_card(value: str, label: str, icon: str) -> dbc.Card:
            return dbc.Card(
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.Span(icon, style={"fontSize": "1.6rem"}),
                                html.H4(value, className="card-title mb-0 ms-2 d-inline"),
                            ],
                            className="d-flex align-items-center mb-1",
                        ),
                        html.P(label, className="card-text text-muted small mb-0"),
                    ]
                ),
                className="h-100 border border-secondary text-light",
            )

        stats_cards = dbc.Row(
            [
                dbc.Col(_stat_card(str(total_events), "Total Events", "📋"), xs=6, md=3, className="mb-3"),
                dbc.Col(_stat_card(str(len(categories)), "Categories", "🏷️"), xs=6, md=3, className="mb-3"),
                dbc.Col(_stat_card(str(tech_events_count), "Tech Events", "💻"), xs=6, md=3, className="mb-3"),
                dbc.Col(_stat_card(str(free_events) if free_events is not None else "N/D", "Free Events", "🎟️"), xs=6, md=3, className="mb-3"),
            ],
            className="mb-4",
        )

        # Filter data for different views - already done above

        # Create subtabs
        subtabs = dbc.Tabs(
            [
                dbc.Tab(
                    label="All Events",
                    tab_id="all-events",
                    children=[
                        html.Div(
                            [
                                html.Div(create_events_table(events_data), id="all-table-container", className="mt-3"),
                            ]
                        )
                    ],
                ),
                dbc.Tab(
                    label="Upcoming Events",
                    tab_id="upcoming-events",
                    children=[
                        html.Div(
                            [
                                (
                                    html.Div(create_events_table(upcoming_events_data), id="upcoming-table-container", className="mt-3")
                                    if upcoming_events_data
                                    else dbc.Alert("No upcoming events available", color="info", className="mt-3 text-center")
                                ),
                            ]
                        )
                    ],
                ),
            ],
            id="valencia-events-subtabs",
            active_tab="all-events",
        )

        return html.Div(
            [
                # Header
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H2("🌆 Valencia Events", className="mb-3"),
                                html.P(
                                    "Local and tech events in Valencia and surroundings",
                                    className="text-muted",
                                ),
                            ]
                        ),
                        # Clientside .ics export (T-068): hidden payload Div always
                        # present; the button only renders when there is something
                        # to export. dbc rejects data-* kwargs, hence html.Div.
                        dbc.Col(
                            [
                                # data-* wildcard props are valid at runtime but absent from Dash's generated stubs
                                html.Div(id="valencia-ics-events", hidden=True, **{"data-events": ics_payload}),  # type: ignore[arg-type]
                                *(
                                    [
                                        dbc.Button(
                                            f"⬇ .ics ({len(ics_events)})",
                                            id="valencia-ics-export-btn",
                                            color="outline-secondary",
                                            size="sm",
                                            className="mb-3",
                                            title="Download upcoming events as a calendar file (.ics)",
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
                    className="mb-4",
                ),
                # Statistics
                stats_cards,
                # Subtabs
                subtabs,
            ],
            className="p-4",
        )

    except Exception as e:
        logger.error(f"Error rendering Valencia events tab: {e}")
        return html.Div(
            [dbc.Alert(f"Error loading Valencia events: {e!s}", color="danger")],
            className="p-4",
        )


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


def _exportable_upcoming_events(events: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    """Return the events eligible for the .ics export: parseable start date today or later.

    Unlike the 30-day window used by the "Upcoming Events" subtab, the calendar
    export keeps every future event ("from today", no upper cutoff). Events whose
    start_date cannot be parsed are skipped (they cannot become VEVENTs).

    Args:
        events: Raw event dictionaries from the repository.
        now: Reference datetime; events dated before its day are excluded.

    Returns:
        List of event dictionaries, original order preserved.
    """
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    exportable: list[dict[str, Any]] = []
    for event in events:
        parsed = _parse_event_date(str(event.get("start_date") or ""))
        if parsed is not None and parsed >= today:
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


def register_valencia_events_callbacks(app):
    """Register callbacks for Valencia events tab"""
    # No callbacks needed for static sorting in basic version,
    # but filter callbacks could be added here if needed.
    pass
