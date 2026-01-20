"""Spanish Public Aid Dashboard Component."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import dash
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dash_table, dcc, html

# Import shared utilities
from src.web.dashboard.utils import file_exists, get_data_path, parse_date_universal

# Import repository pattern (NEW)
from src.repositories import BaseRepository

# --- Data Loading ---

# NEW: Repository-based loading (SOLID Pattern)
class SpanishAidRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for Spanish public aid data."""

    def __init__(self):
        """Initialize Spanish aid repository."""
        data_path = get_data_path("spanish_public_aid", "output", "spanish_public_aid_latest.json")
        super().__init__(
            data_path=Path(data_path),
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform JSON data into list of aid items.

        Args:
            raw_data: Raw JSON data

        Returns:
            List of aid item dictionaries
        """
        if isinstance(raw_data, list):
            return raw_data
        elif isinstance(raw_data, dict):
            return [raw_data]
        else:
            return []

class SpanishAidStatsRepository(BaseRepository[dict[str, Any]]):
    """Repository for Spanish public aid statistics data."""

    def __init__(self):
        """Initialize Spanish aid stats repository."""
        data_path = get_data_path("spanish_public_aid", "output", "spanish_public_aid_stats_latest.json")
        super().__init__(
            data_path=Path(data_path),
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> dict[str, Any]:
        """Transform JSON data into stats dictionary.

        Args:
            raw_data: Raw JSON data

        Returns:
            Stats dictionary
        """
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, list):
            return {"items": raw_data}
        else:
            return {}

# Create singleton instances
spanish_aid_repo = SpanishAidRepository()
spanish_aid_stats_repo = SpanishAidStatsRepository()


def load_spanish_aid_data():
    """Load Spanish public aid data using repository pattern (NEW)."""
    aids_data = []
    stats_data = {}

    try:
        aids_data = spanish_aid_repo.get()
        if not aids_data:
            aids_data = []

        stats_data = spanish_aid_stats_repo.get()
        if not stats_data:
            stats_data = {}

    except Exception as e:
        print(f"Warning: Could not load Spanish aid data: {e}")

    return aids_data, stats_data


def parse_aid_date(date_str: str) -> datetime | None:
    """Parse date strings from aid data."""
    if not date_str:
        return None

    try:
        # Handle ISO format dates
        if "T" in date_str:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        else:
            return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        # Fallback to universal parser
        return parse_date_universal(date_str, "SpanishAid")


# --- Component Creation Functions ---


def create_aid_summary_cards(aids_data: list[dict], stats_data: dict) -> html.Div:
    """Create summary cards with key statistics."""
    total_aids = len(aids_data)
    active_aids = len([aid for aid in aids_data if aid.get("status") == "abierta"])
    closing_soon = len(
        [aid for aid in aids_data if aid.get("status") == "abierta" and aid.get("closing_date") and parse_aid_date(aid["closing_date"]) and (parse_aid_date(aid["closing_date"]) - datetime.now()).days <= 7]
    )

    # Get most common category
    categories = [aid.get("category", "otros") for aid in aids_data]
    most_common_category = max(set(categories), key=categories.count) if categories else "N/A"

    cards = [
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.H4(f"{total_aids}", className="card-title text-primary"),
                        html.P("Total Ayudas", className="card-text"),
                    ]
                )
            ],
            className="text-center mb-3",
        ),
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.H4(f"{active_aids}", className="card-title text-success"),
                        html.P("Ayudas Activas", className="card-text"),
                    ]
                )
            ],
            className="text-center mb-3",
        ),
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.H4(f"{closing_soon}", className="card-title text-warning"),
                        html.P("Cierran Pronto", className="card-text"),
                    ]
                )
            ],
            className="text-center mb-3",
        ),
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.H4(
                            most_common_category.title(),
                            className="card-title text-info",
                        ),
                        html.P("Categoría Principal", className="card-text"),
                    ]
                )
            ],
            className="text-center mb-3",
        ),
    ]

    return dbc.Row([dbc.Col(card, width=3) for card in cards])


def create_category_chart(aids_data: list[dict]) -> dcc.Graph:
    """Create a pie chart showing aids by category."""
    if not aids_data:
        return dcc.Graph(figure={"data": [], "layout": {"title": "No hay datos disponibles"}})

    # Count aids by category
    category_counts = {}
    for aid in aids_data:
        category = aid.get("category", "otros")
        category_counts[category] = category_counts.get(category, 0) + 1

    # Create pie chart
    fig = px.pie(
        values=list(category_counts.values()),
        names=list(category_counts.keys()),
        title="Distribución por Categoría",
    )

    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(showlegend=True, height=400, margin=dict(t=50, b=50, l=50, r=50))

    return dcc.Graph(figure=fig)


def create_scope_chart(aids_data: list[dict]) -> dcc.Graph:
    """Create a bar chart showing aids by geographic scope."""
    if not aids_data:
        return dcc.Graph(figure={"data": [], "layout": {"title": "No hay datos disponibles"}})

    # Count aids by scope
    scope_counts = {}
    for aid in aids_data:
        scope = aid.get("scope", {}).get("scope", "nacional")
        scope_name = {
            "nacional": "Nacional",
            "autonomica": "Autonómica",
            "provincial": "Provincial",
            "local": "Local",
            "europea": "Europea",
        }.get(scope, scope.title())

        scope_counts[scope_name] = scope_counts.get(scope_name, 0) + 1

    # Create bar chart
    fig = px.bar(
        x=list(scope_counts.keys()),
        y=list(scope_counts.values()),
        title="Distribución por Ámbito Geográfico",
        labels={"x": "Ámbito", "y": "Número de Ayudas"},
    )

    fig.update_layout(height=400, margin=dict(t=50, b=50, l=50, r=50))

    return dcc.Graph(figure=fig)


def create_status_timeline(aids_data: list[dict]) -> dcc.Graph:
    """Create a timeline showing aids closing dates."""
    if not aids_data:
        return dcc.Graph(figure={"data": [], "layout": {"title": "No hay datos disponibles"}})

    # Filter aids with closing dates
    aids_with_dates = []
    for aid in aids_data:
        closing_date = aid.get("closing_date")
        if closing_date:
            parsed_date = parse_aid_date(closing_date)
            if parsed_date:
                aids_with_dates.append(
                    {
                        "title": aid.get("title", "Sin título")[:50] + "...",
                        "closing_date": parsed_date,
                        "category": aid.get("category", "otros"),
                        "status": aid.get("status", "abierta"),
                    }
                )

    if not aids_with_dates:
        return dcc.Graph(
            figure={
                "data": [],
                "layout": {"title": "No hay ayudas con fechas de cierre disponibles"},
            }
        )

    # Sort by closing date
    aids_with_dates.sort(key=lambda x: x["closing_date"])

    # Take next 20 closing aids
    upcoming_aids = aids_with_dates[:20]

    # Create timeline
    fig = go.Figure()

    for i, aid in enumerate(upcoming_aids):
        color = "red" if (aid["closing_date"] - datetime.now()).days <= 7 else "blue"

        fig.add_trace(
            go.Scatter(
                x=[aid["closing_date"]],
                y=[i],
                mode="markers+text",
                text=[aid["title"]],
                textposition="middle right",
                marker=dict(size=10, color=color),
                name=aid["category"],
                showlegend=False,
            )
        )

    fig.update_layout(
        title="Próximas Fechas de Cierre",
        xaxis_title="Fecha de Cierre",
        yaxis_title="Ayudas",
        height=600,
        yaxis=dict(showticklabels=False),
        margin=dict(t=50, b=50, l=50, r=200),
    )

    return dcc.Graph(figure=fig)


def create_aids_filter_controls() -> html.Div:
    """Create filter controls for aids."""
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Filtrar por Categoría:"),
                            dcc.Dropdown(
                                id="category-filter",
                                options=[
                                    {"label": "Todas", "value": "all"},
                                    {"label": "Vivienda", "value": "vivienda"},
                                    {"label": "Empleo", "value": "empleo"},
                                    {"label": "Educación", "value": "educacion"},
                                    {"label": "Salud", "value": "salud"},
                                    {"label": "Juventud", "value": "juventud"},
                                    {"label": "Familia", "value": "familia"},
                                    {"label": "Emergencia", "value": "emergencia"},
                                    {"label": "Empresa", "value": "empresa"},
                                    {"label": "Otros", "value": "otros"},
                                ],
                                value="all",
                                multi=False,
                            ),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Filtrar por Estado:"),
                            dcc.Dropdown(
                                id="status-filter",
                                options=[
                                    {"label": "Todos", "value": "all"},
                                    {"label": "Abierta", "value": "abierta"},
                                    {"label": "Cerrada", "value": "cerrada"},
                                    {
                                        "label": "En Evaluación",
                                        "value": "en_evaluacion",
                                    },
                                    {"label": "Resuelta", "value": "resuelta"},
                                    {"label": "Próxima", "value": "proxima"},
                                ],
                                value="abierta",
                                multi=False,
                            ),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Filtrar por Ámbito:"),
                            dcc.Dropdown(
                                id="scope-filter",
                                options=[
                                    {"label": "Todos", "value": "all"},
                                    {"label": "Nacional", "value": "nacional"},
                                    {"label": "Autonómica", "value": "autonomica"},
                                    {"label": "Local", "value": "local"},
                                ],
                                value="all",
                                multi=False,
                            ),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Solo urgentes (< 7 días):"),
                            dcc.Checklist(
                                id="urgent-filter",
                                options=[{"label": "Solo urgentes", "value": "urgent"}],
                                value=[],
                                inline=True,
                            ),
                        ],
                        width=3,
                    ),
                ],
                className="mb-3",
            )
        ]
    )


def create_aids_table(aids_data: list[dict]) -> html.Div:
    """Create a table showing aids with filtering capabilities."""
    if not aids_data:
        return dbc.Alert("No hay datos de ayudas disponibles.", color="info")

    # Prepare data for table
    table_data = []
    for aid in aids_data:
        closing_date_str = "N/A"
        days_left = "N/A"

        if aid.get("closing_date"):
            closing_date = parse_aid_date(aid["closing_date"])
            if closing_date:
                closing_date_str = closing_date.strftime("%Y-%m-%d")
                days_left = max(0, (closing_date - datetime.now()).days)

        # Get amount information
        amount_info = "N/A"
        if aid.get("amount"):
            amount = aid["amount"]
            if amount.get("fixed_amount"):
                amount_info = f"€{amount['fixed_amount']}"
            elif amount.get("max_amount"):
                amount_info = f"Hasta €{amount['max_amount']}"
            elif amount.get("min_amount"):
                amount_info = f"Desde €{amount['min_amount']}"

        table_data.append(
            {
                "title": aid.get("title", "Sin título"),
                "category": aid.get("category", "otros").title(),
                "status": aid.get("status", "abierta").title(),
                "scope": aid.get("scope", {}).get("scope", "nacional").title(),
                "organizing_entity": aid.get("organizing_entity", "N/A"),
                "closing_date": closing_date_str,
                "days_left": days_left,
                "amount": amount_info,
                "source_url": aid.get("source_url", "#"),
            }
        )

    # Create DataTable
    table = dash_table.DataTable(
        id="aids-table",
        data=table_data,
        columns=[
            {
                "name": "Título",
                "id": "title",
                "type": "text",
                "presentation": "markdown",
            },
            {"name": "Categoría", "id": "category", "type": "text"},
            {"name": "Estado", "id": "status", "type": "text"},
            {"name": "Ámbito", "id": "scope", "type": "text"},
            {"name": "Organismo", "id": "organizing_entity", "type": "text"},
            {"name": "Fecha Cierre", "id": "closing_date", "type": "datetime"},
            {"name": "Días Restantes", "id": "days_left", "type": "numeric"},
            {"name": "Cuantía", "id": "amount", "type": "text"},
        ],
        page_size=20,
        sort_action="native",
        filter_action="native",
        style_cell={
            "textAlign": "left",
            "fontSize": "14px",
            "fontFamily": "Arial, sans-serif",
            "padding": "10px",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "maxWidth": 0,
        },
        style_header={
            "backgroundColor": "rgb(30, 30, 30)",
            "color": "white",
            "fontWeight": "bold",
            "border": "1px solid #444",
        },
        style_data={
            "backgroundColor": "#2c2c2c",
            "color": "white",
            "border": "1px solid #444",
        },
        style_data_conditional=[
            {
                "if": {"column_id": "title"},
                "width": "50%",  # Explicit width for Title
            },
            {
                "if": {"filter_query": "{days_left} <= 7 && {days_left} > 0"},
                "backgroundColor": "#3e2723", # Dark reddish background for urgency
                "color": "#ffcdd2", # Light red text
            },
            {
                "if": {"filter_query": "{status} = Cerrada"},
                "backgroundColor": "#212121",
                "color": "#757575",
            },
        ],
        tooltip_data=[{column: {"value": str(row[column]), "type": "markdown"} for column in row.keys()} for row in table_data],
        css=[
            {
                "selector": ".dash-table-tooltip",
                "rule": "background-color: grey; font-family: monospace; color: white",
            }
        ],
    )

    return html.Div([html.H5("Tabla de Ayudas Públicas", className="mb-3"), table])


def create_search_component() -> html.Div:
    """Create search component for aids."""
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.InputGroup(
                                [
                                    dbc.Input(
                                        id="search-input",
                                        placeholder="Buscar ayudas por título, descripción o palabras clave...",
                                        type="text",
                                    ),
                                    dbc.Button(
                                        "Buscar",
                                        id="search-button",
                                        color="primary",
                                        n_clicks=0,
                                    ),
                                ]
                            )
                        ],
                        width=8,
                    ),
                    dbc.Col(
                        [
                            dbc.Button(
                                "Limpiar Filtros",
                                id="clear-filters-button",
                                color="secondary",
                                outline=True,
                                n_clicks=0,
                            )
                        ],
                        width=2,
                    ),
                    dbc.Col(
                        [
                            dbc.Button(
                                "Actualizar Datos",
                                id="refresh-data-button",
                                color="success",
                                outline=True,
                                n_clicks=0,
                            )
                        ],
                        width=2,
                    ),
                ],
                className="mb-4",
            )
        ]
    )


# --- Main Tab Rendering Function ---


def render_spanish_public_aid_tab():
    """Render the main Spanish Public Aid tab."""
    # Load data
    aids_data, stats_data = load_spanish_aid_data()

    if not aids_data:
        return dbc.Container(
            [
                dbc.Alert(
                    [
                        html.H4("No hay datos disponibles", className="alert-heading"),
                        html.P("No se encontraron datos de ayudas públicas españolas."),
                        html.Hr(),
                        html.P(
                            "Asegúrate de ejecutar el ETL de ayudas públicas españolas primero:",
                            className="mb-0",
                        ),
                        html.Code("uv run python src/etl/spanish_public_aid/spanish_public_aid_etl.py"),
                    ],
                    color="warning",
                    className="mt-3",
                )
            ],
            fluid=True,
        )

    return html.Div(
        [
            html.H3("Ayudas Públicas Españolas", className="mb-4"),
            # Summary cards
            create_aid_summary_cards(aids_data, stats_data),
            html.Hr(),
            # Search component
            create_search_component(),
            # Filter controls
            create_aids_filter_controls(),
            html.Hr(),
            # Charts row
            dbc.Row(
                [
                    dbc.Col([create_category_chart(aids_data)], width=6),
                    dbc.Col([create_scope_chart(aids_data)], width=6),
                ],
                className="mb-4",
            ),
            # Timeline
            dbc.Row(
                [
                    dbc.Col([create_status_timeline(aids_data)], width=12),
                ],
                className="mb-4",
            ),
            html.Hr(),
            # Aids table
            html.Div(id="filtered-aids-table", children=[create_aids_table(aids_data)]),
            # Last updated info
            html.Div(
                [
                    html.Hr(),
                    html.P(
                        [
                            html.Small(
                                [
                                    "Última actualización: ",
                                    html.Span(
                                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        id="last-updated-time",
                                    ),
                                    " | ",
                                    html.A(
                                        "Ver código fuente",
                                        href="https://github.com/your-repo/watchtower/tree/main/src/etl/spanish_public_aid",
                                        target="_blank",
                                    ),
                                ],
                                className="text-muted",
                            )
                        ],
                        className="text-center",
                    ),
                ]
            ),
        ]
    )


# --- Callbacks for Interactivity ---


def register_spanish_aid_callbacks(app):
    """Register callbacks for Spanish Public Aid tab."""

    @app.callback(
        Output("filtered-aids-table", "children"),
        [
            Input("category-filter", "value"),
            Input("status-filter", "value"),
            Input("scope-filter", "value"),
            Input("urgent-filter", "value"),
            Input("search-input", "value"),
            Input("search-button", "n_clicks"),
            Input("refresh-data-button", "n_clicks"),
        ],
    )
    def update_aids_table(
        category_filter,
        status_filter,
        scope_filter,
        urgent_filter,
        search_text,
        search_clicks,
        refresh_clicks,
    ):
        """Update the aids table based on filters."""
        # Load fresh data
        aids_data, _ = load_spanish_aid_data()

        if not aids_data:
            return dbc.Alert("No hay datos disponibles.", color="info")

        # Apply filters
        filtered_data = aids_data.copy()

        # Category filter
        if category_filter and category_filter != "all":
            filtered_data = [aid for aid in filtered_data if aid.get("category") == category_filter]

        # Status filter
        if status_filter and status_filter != "all":
            filtered_data = [aid for aid in filtered_data if aid.get("status") == status_filter]

        # Scope filter
        if scope_filter and scope_filter != "all":
            filtered_data = [aid for aid in filtered_data if aid.get("scope", {}).get("scope") == scope_filter]

        # Urgent filter
        if "urgent" in (urgent_filter or []):
            urgent_aids = []
            for aid in filtered_data:
                if aid.get("closing_date"):
                    closing_date = parse_aid_date(aid["closing_date"])
                    if closing_date and (closing_date - datetime.now()).days <= 7:
                        urgent_aids.append(aid)
            filtered_data = urgent_aids

        # Search filter
        if search_text:
            search_lower = search_text.lower()
            search_filtered = []
            for aid in filtered_data:
                if search_lower in aid.get("title", "").lower() or search_lower in aid.get("description", "").lower() or any(search_lower in keyword.lower() for keyword in aid.get("keywords", [])):
                    search_filtered.append(aid)
            filtered_data = search_filtered

        return create_aids_table(filtered_data)

    @app.callback(
        [
            Output("category-filter", "value"),
            Output("status-filter", "value"),
            Output("scope-filter", "value"),
            Output("urgent-filter", "value"),
            Output("search-input", "value"),
        ],
        Input("clear-filters-button", "n_clicks"),
    )
    def clear_filters(n_clicks):
        """Clear all filters."""
        if n_clicks and n_clicks > 0:
            return "all", "all", "all", [], ""

        # Return current values (no change)
        return (
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
        )


# --- Standalone Testing ---

if __name__ == "__main__":
    # For testing this component independently
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

    app_test.layout = dbc.Container(
        [
            html.H1("Spanish Public Aid Tab Test (Standalone)"),
            render_spanish_public_aid_tab(),
        ],
        fluid=True,
        className="py-4",
    )

    print("Running standalone test for spanish_public_aid_tab.py...")
    print("Expected data files: data/spanish_public_aid/spanish_public_aid_latest.json")
    print("Run the ETL first if no data is available.")

    app_test.run_server(debug=True, port=8053)
