"""New Valencia Events Tab Component with Subtabs for Watchtower Dashboard"""

import json
import logging
from datetime import datetime, timedelta
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
        title = event.get("title", "Sin título")
        description = event.get("description", "Sin descripción disponible")
        category = event.get("category", "General")
        start_date = event.get("start_date", "")
        end_date = event.get("end_date", "")
        date_text = event.get("date_text", "")
        url = event.get("url", "")
        source = event.get("source", "Valencia")

        # Format dates
        date_display = date_text if date_text else (f"{start_date} - {end_date}" if start_date and end_date else start_date if start_date else "Fecha por confirmar")

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
                                dbc.Badge(category, color=badge_color, className="me-2"),
                            ]
                        ),
                    ]
                )
            ]
        )

        card_body_content = [
            html.P(description, className="card-text mb-3"),
            html.Div([html.Strong("📅 Fecha: "), html.Span(date_display)], className="mb-2"),
            html.Div([html.Strong("🏷️ Fuente: "), html.Span(source)], className="mb-3"),
            # Action button
            (
                dbc.Button(
                    "Ver más información",
                    href=url,
                    target="_blank",
                    color="outline-primary",
                    size="sm",
                    disabled=not url,
                )
                if url
                else html.Span("No hay enlace disponible", className="text-muted")
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
            return dbc.Alert("No hay eventos disponibles", color="info")

        # Table Header
        table_header = [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Título"),
                        html.Th("Categoría"),
                        html.Th("Fecha"),
                        html.Th("Fuente"),
                        html.Th("Enlace"),
                    ]
                )
            )
        ]

        # Table Body
        table_body_rows = []
        for event in events:
            title = event.get("title", "Sin título")
            description = event.get("description", "")
            category = event.get("category", "General")
            date_text = event.get("date_text") or event.get("start_date", "N/A")
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

            table_body_rows.append(
                html.Tr(
                    [
                        html.Td(
                            [
                                html.Div(title, className="fw-bold"),
                                html.Small(description[:100] + "..." if len(description) > 100 else description, className="text-muted")
                            ]
                        ),
                        html.Td(dbc.Badge(category, color=badge_color)),
                        html.Td(date_text),
                        html.Td(source),
                        html.Td(
                            dbc.Button(
                                "Ver",
                                href=url,
                                target="_blank",
                                color="link",
                                size="sm",
                                className="text-decoration-none"
                            ) if url else "N/A"
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
        return dbc.Alert(f"Error creando tabla: {e!s}", color="danger")


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
                                "No hay eventos de Valencia disponibles",
                                className="alert-heading",
                            ),
                            html.P("No se encontraron datos de eventos. Ejecuta el ETL de Valencia para poblar los datos."),
                            html.Hr(),
                            html.P(
                                f"Ubicación esperada: {VALENCIA_EVENTS_FILE}",
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
        upcoming_events_count = len(upcoming_events_data)
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
                                        html.P("Total Eventos", className="card-text"),
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
                                        html.P("Categorías", className="card-text"),
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
                                        html.H4(
                                            str(tech_events_count),
                                            className="card-title",
                                        ),
                                        html.P("Eventos Tech", className="card-text"),
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
                                        html.P("Eventos Gratuitos", className="card-text"),
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

        # Filter data for different views - already done above

        # Create subtabs
        subtabs = dbc.Tabs(
            [
                dbc.Tab(
                    label="Todos los Eventos",
                    tab_id="all-events",
                    children=[
                        html.Div(
                            [
                                html.Div(
                                    create_events_table(events_data),
                                    id="all-table-container",
                                    className="mt-3"
                                ),
                            ]
                        )
                    ],
                ),
                dbc.Tab(
                    label="Próximos Eventos",
                    tab_id="upcoming-events",
                    children=[
                        html.Div(
                            [
                                html.Div(
                                    create_events_table(upcoming_events_data),
                                    id="upcoming-table-container",
                                    className="mt-3"
                                )
                                if upcoming_events_data
                                else dbc.Alert(
                                    "No hay eventos próximos disponibles",
                                    color="info",
                                    className="mt-3 text-center"
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
                                html.H2("🌆 Eventos Valencia", className="mb-3"),
                                html.P(
                                    "Eventos locales y tecnológicos en Valencia y alrededores",
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
            [dbc.Alert(f"Error cargando eventos de Valencia: {e!s}", color="danger")],
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
