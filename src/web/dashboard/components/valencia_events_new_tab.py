"""New Valencia Events Tab Component with Subtabs for Watchtower Dashboard"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, dash_table, html

# Set up logging
logger = logging.getLogger(__name__)

# Data file paths
VALENCIA_EVENTS_FILE = Path("data/valencia_events/valencia_events.json")


def load_valencia_events() -> List[Dict[str, Any]]:
    """Load Valencia events data from JSON files"""
    try:
        if not VALENCIA_EVENTS_FILE.exists():
            logger.warning(f"Valencia events file not found: {VALENCIA_EVENTS_FILE}")
            return []

        with open(VALENCIA_EVENTS_FILE, "r", encoding="utf-8") as f:
            events = json.load(f)

        logger.info(f"Loaded {len(events)} Valencia events from {VALENCIA_EVENTS_FILE}")
        return events
    except Exception as e:
        logger.error(f"Error loading Valencia events: {e}")
        return []


def create_event_card(event: Dict[str, Any]) -> dbc.Card:
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
        date_display = (
            date_text
            if date_text
            else (
                f"{start_date} - {end_date}"
                if start_date and end_date
                else start_date
                if start_date
                else "Fecha por confirmar"
            )
        )

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
                                dbc.Badge(
                                    category, color=badge_color, className="me-2"
                                ),
                            ]
                        ),
                    ]
                )
            ]
        )

        card_body_content = [
            html.P(description, className="card-text mb-3"),
            html.Div(
                [html.Strong("📅 Fecha: "), html.Span(date_display)], className="mb-2"
            ),
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

        return dbc.Card(
            [card_header, dbc.CardBody(card_body_content)], className="mb-3 h-100"
        )

    except Exception as e:
        logger.error(f"Error creating event card: {e}")
        return dbc.Card(
            dbc.CardBody(
                [
                    html.H4("Error Loading Event", className="card-title"),
                    html.P(f"Error: {str(e)}", className="card-text"),
                ]
            ),
            className="mb-3",
        )


def create_events_table(events: List[Dict[str, Any]]) -> dash_table.DataTable:
    """Create a table view of events"""
    try:
        if not events:
            return html.Div("No hay eventos disponibles")

        # Convert to DataFrame
        df = pd.DataFrame(events)

        # Select and prepare columns for display
        display_columns = ["title", "category", "date_text", "source"]
        existing_columns = [col for col in display_columns if col in df.columns]
        df_display = df[existing_columns].copy()

        # Rename columns for Spanish interface
        rename_map = {
            "title": "Título",
            "category": "Categoría",
            "date_text": "Fecha",
            "source": "Fuente",
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
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "rgb(255, 255, 255)"}
            ],
            sort_action="native",
            filter_action="native",
            page_action="native",
            page_current=0,
            page_size=15,
            tooltip_data=[
                {
                    column: {"value": str(value), "type": "text"}
                    for column, value in row.items()
                }
                for row in df_display.to_dict("records")
            ],
            tooltip_duration=None,
        )

    except Exception as e:
        logger.error(f"Error creating events table: {e}")
        return html.Div(f"Error creando tabla: {str(e)}")


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
                            html.P(
                                "No se encontraron datos de eventos. Ejecuta el ETL de Valencia para poblar los datos."
                            ),
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

        # Statistics
        total_events = len(events_data)
        categories = set(event.get("category", "General") for event in events_data)
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
                                        html.H4(
                                            str(total_events), className="card-title"
                                        ),
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
                                        html.H4(
                                            str(len(categories)), className="card-title"
                                        ),
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
                                            str(tech_events_count), className="card-title"
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
                                        html.H4(
                                            str(free_events), className="card-title"
                                        ),
                                        html.P(
                                            "Eventos Gratuitos", className="card-text"
                                        ),
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

        # Filter data for different views
        if events_data:
            tech_events_data = [
                e for e in events_data
                if "tech" in e.get("category", "").lower()
                or "tecnología" in e.get("category", "").lower()
            ]

            upcoming_events_data = [
                e for e in events_data
                if e.get("start_date")
                and self._is_upcoming_event(e.get("start_date", ""), datetime.now() + timedelta(days=30))
            ]
        else:
            tech_events_data = []
            upcoming_events_data = []

        # Create subtabs
        subtabs = dbc.Tabs(
            [
                dbc.Tab(
                    label="Todos los Eventos",
                    tab_id="all-events",
                    children=[
                        html.Div(
                            [
                                # View toggle buttons
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button(
                                            "Vista de Tarjetas",
                                            id="all-cards-view-btn",
                                            color="primary",
                                            outline=True,
                                        ),
                                        dbc.Button(
                                            "Vista de Tabla", id="all-table-view-btn", color="primary", outline=True
                                        ),
                                    ],
                                    className="mb-4",
                                ),
                                # Content container
                                html.Div(
                                    [
                                        # Cards view (default)
                                        html.Div(
                                            [
                                                dbc.Row(
                                                    [
                                                        dbc.Col(card, width=4)
                                                        for card in [
                                                            create_event_card(event)
                                                            for event in events_data[:12]
                                                        ]
                                                    ],
                                                    className="mb-4"
                                                )
                                            ],
                                            id="all-cards-container",
                                            style={"display": "block"},
                                        ),
                                        # Table view (hidden by default)
                                        html.Div(
                                            create_events_table(events_data),
                                            id="all-table-container",
                                            style={"display": "none"},
                                        ),
                                    ],
                                    id="all-events-content",
                                ),
                            ]
                        )
                    ]
                ),
                dbc.Tab(
                    label="Eventos Tecnológicos",
                    tab_id="tech-events",
                    children=[
                        html.Div(
                            [
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button(
                                            "Vista de Tarjetas",
                                            id="tech-cards-view-btn",
                                            color="primary",
                                            outline=True,
                                        ),
                                        dbc.Button(
                                            "Vista de Tabla", id="tech-table-view-btn", color="primary", outline=True
                                        ),
                                    ],
                                    className="mb-4",
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                dbc.Row(
                                                    [
                                                        dbc.Col(card, width=4)
                                                        for card in [
                                                            create_event_card(event)
                                                            for event in tech_events_data[:12]
                                                        ]
                                                    ],
                                                    className="mb-4"
                                                )
                                            ],
                                            id="tech-cards-container",
                                            style={"display": "block"},
                                        ),
                                        html.Div(
                                            create_events_table(tech_events_data),
                                            id="tech-table-container",
                                            style={"display": "none"},
                                        ),
                                    ],
                                    id="tech-events-content",
                                ) if tech_events_data else html.Div("No hay eventos tecnológicos disponibles", className="text-center p-4")
                            ]
                        )
                    ]
                ),
                dbc.Tab(
                    label="Próximos Eventos",
                    tab_id="upcoming-events",
                    children=[
                        html.Div(
                            [
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button(
                                            "Vista de Tarjetas",
                                            id="upcoming-cards-view-btn",
                                            color="primary",
                                            outline=True,
                                        ),
                                        dbc.Button(
                                            "Vista de Tabla", id="upcoming-table-view-btn", color="primary", outline=True
                                        ),
                                    ],
                                    className="mb-4",
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                dbc.Row(
                                                    [
                                                        dbc.Col(card, width=4)
                                                        for card in [
                                                            create_event_card(event)
                                                            for event in upcoming_events_data[:12]
                                                        ]
                                                    ],
                                                    className="mb-4"
                                                )
                                            ],
                                            id="upcoming-cards-container",
                                            style={"display": "block"},
                                        ),
                                        html.Div(
                                            create_events_table(upcoming_events_data),
                                            id="upcoming-table-container",
                                            style={"display": "none"},
                                        ),
                                    ],
                                    id="upcoming-events-content",
                                ) if upcoming_events_data else html.Div("No hay eventos próximos disponibles", className="text-center p-4")
                            ]
                        )
                    ]
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
            [
                dbc.Alert(
                    f"Error cargando eventos de Valencia: {str(e)}", color="danger"
                )
            ],
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

    # All events view toggle
    @app.callback(
        [
            Output("all-cards-container", "style"),
            Output("all-table-container", "style"),
            Output("all-cards-view-btn", "outline"),
            Output("all-table-view-btn", "outline"),
        ],
        [
            Input("all-cards-view-btn", "n_clicks"),
            Input("all-table-view-btn", "n_clicks"),
        ],
    )
    def toggle_all_events_view(cards_clicks, table_clicks):
        """Toggle between cards and table view for all events"""
        if table_clicks and (not cards_clicks or table_clicks > cards_clicks):
            return (
                {"display": "none"},
                {"display": "block"},
                True,
                False,
            )
        else:
            return (
                {"display": "block"},
                {"display": "none"},
                False,
                True,
            )

    # Tech events view toggle
    @app.callback(
        [
            Output("tech-cards-container", "style"),
            Output("tech-table-container", "style"),
            Output("tech-cards-view-btn", "outline"),
            Output("tech-table-view-btn", "outline"),
        ],
        [
            Input("tech-cards-view-btn", "n_clicks"),
            Input("tech-table-view-btn", "n_clicks"),
        ],
    )
    def toggle_tech_events_view(cards_clicks, table_clicks):
        """Toggle between cards and table view for tech events"""
        if table_clicks and (not cards_clicks or table_clicks > cards_clicks):
            return (
                {"display": "none"},
                {"display": "block"},
                True,
                False,
            )
        else:
            return (
                {"display": "block"},
                {"display": "none"},
                False,
                True,
            )

    # Upcoming events view toggle
    @app.callback(
        [
            Output("upcoming-cards-container", "style"),
            Output("upcoming-table-container", "style"),
            Output("upcoming-cards-view-btn", "outline"),
            Output("upcoming-table-view-btn", "outline"),
        ],
        [
            Input("upcoming-cards-view-btn", "n_clicks"),
            Input("upcoming-table-view-btn", "n_clicks"),
        ],
    )
    def toggle_upcoming_events_view(cards_clicks, table_clicks):
        """Toggle between cards and table view for upcoming events"""
        if table_clicks and (not cards_clicks or table_clicks > cards_clicks):
            return (
                {"display": "none"},
                {"display": "block"},
                True,
                False,
            )
        else:
            return (
                {"display": "block"},
                {"display": "none"},
                False,
                True,
            )
