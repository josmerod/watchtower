"""Valencia Events Tab Component for Watchtower Dashboard"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, dash_table, html

# Import repository pattern (NEW)
from src.repositories import BaseRepository

# Set up logging
logger = logging.getLogger(__name__)

# Data file paths
VALENCIA_EVENTS_FILE = Path("data/valencia_events/valencia_events.json")
TECH_EVENTS_FILE = Path("data/tech_events/tech_events_valencia.json")

# NEW: Repository-based loading (SOLID Pattern)
class ValenciaEventsRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for Valencia events data."""

    def __init__(self, data_path: str):
        """Initialize Valencia events repository.

        Args:
            data_path: Path to events data file
        """
        super().__init__(
            data_path=Path(data_path),
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

# Create singleton instances for each source
valencia_events_repo = ValenciaEventsRepository(str(VALENCIA_EVENTS_FILE))
tech_events_repo = ValenciaEventsRepository(str(TECH_EVENTS_FILE))


def load_valencia_events() -> list[dict[str, Any]]:
    """Load Valencia events data using repository pattern (NEW)."""
    try:
        all_events = []

        # Load general Valencia events
        general_events = valencia_events_repo.get()
        if general_events:
            all_events.extend(general_events)

        # Load tech-specific events
        tech_events = tech_events_repo.get()
        if tech_events:
            all_events.extend(tech_events)

        logger.info(f"Total loaded {len(all_events)} Valencia events")
        return all_events
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
        cost = event.get("cost", 0.0)

        # Venue information
        venue_info = event.get("venue", {})
        if isinstance(venue_info, dict):
            venue_name = venue_info.get("name", "Location not specified")
            venue_address = venue_info.get("address", "")
            venue_city = venue_info.get("city", "Valencia")
        else:
            venue_name = str(venue_info) if venue_info else "Location not specified"
            venue_address = ""
            venue_city = "Valencia"

        # Format dates
        date_display = date_text if date_text else (f"{start_date} - {end_date}" if start_date and end_date else start_date if start_date else "Date TBC")

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

        # Cost badge
        cost_badge = dbc.Badge(
            "Free" if cost == 0 else f"€{cost}",
            color="success" if cost == 0 else "danger",
            className="ms-2",
        )

        card_header = dbc.CardHeader(
            [
                html.Div(
                    [
                        html.H5(title, className="mb-1"),
                        html.Div(
                            [
                                dbc.Badge(category, color=badge_color, className="me-2"),
                                cost_badge,
                            ]
                        ),
                    ]
                )
            ]
        )

        card_body_content = [
            html.P(description, className="card-text mb-3"),
            html.Div([html.Strong("📅 Date: "), html.Span(date_display)], className="mb-2"),
            html.Div(
                [
                    html.Strong("📍 Venue: "),
                    html.Span(venue_name),
                    html.Br() if venue_address else "",
                    (html.Small(venue_address, className="text-muted") if venue_address else ""),
                ],
                className="mb-2",
            ),
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


def create_events_table(events: list[dict[str, Any]]) -> dash_table.DataTable:
    """Create a table view of events"""
    try:
        if not events:
            return html.Div("No events available")

        # Convert to DataFrame
        df = pd.DataFrame(events)

        # Select and prepare columns for display
        display_columns = ["title", "category", "date_text", "source"]
        if "venue" in df.columns:
            # Extract venue name for table display
            df["venue_name"] = df["venue"].apply(lambda x: (x.get("name", "N/A") if isinstance(x, dict) else str(x) if x else "N/A"))
            display_columns.append("venue_name")

        # Filter existing columns
        existing_columns = [col for col in display_columns if col in df.columns]
        df_display = df[existing_columns].copy()

        # Rename columns for display
        rename_map = {
            "title": "Title",
            "category": "Category",
            "date_text": "Date",
            "source": "Source",
            "venue_name": "Venue",
        }
        df_display = df_display.rename(columns=rename_map)

        return dash_table.DataTable(
            data=df_display.to_dict("records"),
            columns=[{"name": col, "id": col} for col in df_display.columns],
            style_cell={
                "textAlign": "left",
                "padding": "12px",
                "fontSize": "14px",
                "fontFamily": "Arial, sans-serif",
                "maxWidth": "200px",
                "overflow": "hidden",
                "textOverflow": "ellipsis",
            },
            style_header={
                "backgroundColor": "rgb(230, 230, 230)",
                "fontWeight": "bold",
                "border": "1px solid #dee2e6",
            },
            style_data={
                "backgroundColor": "rgb(248, 249, 250)",
                "border": "1px solid #dee2e6",
                "whiteSpace": "normal",
                "height": "auto",
            },
            style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "rgb(255, 255, 255)"}],
            sort_action="native",
            filter_action="native",
            page_action="native",
            page_current=0,
            page_size=15,
            tooltip_data=[{column: {"value": str(value), "type": "text"} for column, value in row.items()} for row in df_display.to_dict("records")],
            tooltip_duration=None,
        )

    except Exception as e:
        logger.error(f"Error creating events table: {e}")
        return html.Div(f"Error creating table: {e!s}")


def render_valencia_events_tab() -> html.Div:
    """Render the Valencia events tab"""
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
                                f"Expected location: {VALENCIA_EVENTS_FILE} or {TECH_EVENTS_FILE}",
                                className="mb-0",
                            ),
                        ],
                        color="info",
                    )
                ],
                className="p-4",
            )

        # Get last modification time for display
        last_updated = "Never"
        if VALENCIA_EVENTS_FILE.exists():
            file_mtime = VALENCIA_EVENTS_FILE.stat().st_mtime
            last_updated = datetime.fromtimestamp(file_mtime).strftime("%d/%m/%Y %H:%M")

        # Statistics
        total_events = len(events_data)
        categories = {event.get("category", "General") for event in events_data}
        tech_events = len([e for e in events_data if "tech" in e.get("category", "").lower() or "tecnología" in e.get("category", "").lower()])
        free_events = len([e for e in events_data if e.get("cost", 0) == 0])

        stats_cards = dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H4(str(total_events), className="card-title"),
                                        html.P("Total Events", className="card-text"),
                                    ]
                                )
                            ]
                        )
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H4(str(len(categories)), className="card-title"),
                                        html.P("Categories", className="card-text"),
                                    ]
                                )
                            ]
                        )
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H4(str(tech_events), className="card-title"),
                                        html.P("Tech Events", className="card-text"),
                                    ]
                                )
                            ]
                        )
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H4(str(free_events), className="card-title"),
                                        html.P("Free Events", className="card-text"),
                                    ]
                                )
                            ]
                        )
                    ],
                    width=3,
                ),
            ],
            className="mb-4",
        )

        # View toggle buttons
        view_toggle = dbc.ButtonGroup(
            [
                dbc.Button(
                    "Card View",
                    id="cards-view-btn",
                    color="primary",
                    outline=True,
                ),
                dbc.Button("Table View", id="table-view-btn", color="primary", outline=True),
            ],
            className="mb-4",
        )

        # Create event cards (limit to first 12 for performance)
        event_cards = []
        for event in events_data[:12]:
            event_cards.append(create_event_card(event))

        # Create grid layout for cards
        card_columns = []
        for i in range(0, len(event_cards), 3):  # 3 cards per row
            row_cards = event_cards[i : i + 3]
            card_columns.append(dbc.Row([dbc.Col(card, width=4) for card in row_cards], className="mb-4"))

        # Create table view
        events_table = create_events_table(events_data)

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
                                html.Small(
                                    f"Last updated: {last_updated}",
                                    className="text-muted",
                                ),
                            ]
                        )
                    ],
                    className="mb-4",
                ),
                # Statistics
                stats_cards,
                # View toggle
                view_toggle,
                # Content container
                html.Div(
                    [
                        # Cards view (default)
                        html.Div(
                            card_columns,
                            id="cards-container",
                            style={"display": "block"},
                        ),
                        # Table view (hidden by default)
                        html.Div(
                            events_table,
                            id="table-container",
                            style={"display": "none"},
                        ),
                    ],
                    id="events-content",
                ),
            ],
            className="p-4",
        )

    except Exception as e:
        logger.error(f"Error rendering Valencia events tab: {e}")
        return html.Div(
            [dbc.Alert(f"Error loading Valencia events: {e!s}", color="danger")],
            className="p-4",
        )


def register_valencia_events_callbacks(app):
    """Register callbacks for Valencia events tab"""

    @app.callback(
        [
            Output("cards-container", "style"),
            Output("table-container", "style"),
            Output("cards-view-btn", "outline"),
            Output("table-view-btn", "outline"),
        ],
        [
            Input("cards-view-btn", "n_clicks"),
            Input("table-view-btn", "n_clicks"),
        ],
    )
    def toggle_events_view(cards_clicks, table_clicks):
        """Toggle between cards and table view for events"""
        if table_clicks and (not cards_clicks or table_clicks > cards_clicks):
            # Show table view
            return (
                {"display": "none"},  # cards-container
                {"display": "block"},  # table-container
                True,  # cards-view-btn outline
                False,  # table-view-btn outline
            )
        else:
            # Show cards view (default)
            return (
                {"display": "block"},  # cards-container
                {"display": "none"},  # table-container
                False,  # cards-view-btn outline
                True,  # table-view-btn outline
            )

    @app.callback(
        [
            Output("cinema-cards-container", "style"),
            Output("cinema-table-container", "style"),
            Output("cinema-cards-view-btn", "outline"),
            Output("cinema-table-view-btn", "outline"),
        ],
        [
            Input("cinema-cards-view-btn", "n_clicks"),
            Input("cinema-table-view-btn", "n_clicks"),
        ],
    )
    def toggle_cinema_view(cards_clicks, table_clicks):
        """Toggle between cards and table view for cinema"""
        if table_clicks and (not cards_clicks or table_clicks > cards_clicks):
            # Show table view
            return (
                {"display": "none"},  # cinema-cards-container
                {"display": "block"},  # cinema-table-container
                True,  # cinema-cards-view-btn outline
                False,  # cinema-table-view-btn outline
            )
        else:
            # Show cards view (default)
            return (
                {"display": "block"},  # cinema-cards-container
                {"display": "none"},  # cinema-table-container
                False,  # cinema-cards-view-btn outline
                True,  # cinema-table-view-btn outline
            )
