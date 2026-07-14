"""New Valencia Events Tab Component with Subtabs for Watchtower Dashboard"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
from dash import html

# Import repository pattern (NEW)
from src.repositories import BaseRepository

# Set up logging
logger = logging.getLogger(__name__)

# Data file paths
VALENCIA_EVENTS_FILE = Path("data/valencia_events/valencia_events.json")


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


def create_event_card(event: dict[str, Any]) -> dbc.Card:
    """Create a card component for a single event"""
    try:
        title = event.get("title", "Untitled")
        description = event.get("description", "No description available")
        category = event.get("category", "General")
        start_date = event.get("start_date", "")
        end_date = event.get("end_date", "")
        date_text = event.get("date_text", "")
        url = event.get("url", "")
        source = event.get("source", "Valencia")

        # Format dates — shorten bulky prefixes
        raw_date = date_text if date_text else (f"{start_date} - {end_date}" if start_date and end_date else start_date if start_date else "Date TBC")
        date_display = raw_date.replace("Del ", "").replace(" al ", " – ")

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
            raw_date = event.get("date_text") or event.get("start_date", "N/A")
            # Shorten bulky date prefixes
            date_text_short = raw_date.replace("Del ", "").replace(" al ", " – ") if isinstance(raw_date, str) else raw_date
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
        events_data = load_valencia_events()

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

        upcoming_events_data = [e for e in events_data if e.get("start_date") and _is_upcoming_event(e.get("start_date", ""), datetime.now() + timedelta(days=30))]

        # Statistics
        total_events = len(events_data)
        categories = {event.get("category", "General") for event in events_data}
        tech_events_count = len(tech_events_data)
        len(upcoming_events_data)
        free_events = len([e for e in events_data if e.get("cost", 0) == 0])

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
                dbc.Col(_stat_card(str(free_events), "Free Events", "🎟️"), xs=6, md=3, className="mb-3"),
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
                        )
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


def _is_upcoming_event(date_str: str, cutoff_date: datetime) -> bool:
    """Check if an event date is within the next 30 days."""
    try:
        if not date_str or "/" not in date_str:
            return False

        # Parse DD/MM/YYYY format
        parts = date_str.split("/")
        if len(parts) == 3:
            day, month, year = parts
            event_date = datetime(int(year), int(month), int(day))

            return event_date <= cutoff_date
    except Exception:
        pass

    return False


def register_valencia_events_callbacks(app):
    """Register callbacks for Valencia events tab"""
    # No callbacks needed for static sorting in basic version,
    # but filter callbacks could be added here if needed.
    pass
