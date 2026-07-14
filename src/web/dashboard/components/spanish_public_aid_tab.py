"""Spanish Public Aid Dashboard Component."""

from datetime import datetime
from pathlib import Path
from typing import Any

import dash
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dash_table, dcc, html

# Import repository pattern (NEW)
from src.repositories import BaseRepository

# Import shared utilities
from src.web.dashboard.utils import get_data_path, parse_date_universal

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
                        html.P("Total Aid", className="card-text"),
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
                        html.P("Active Aid", className="card-text"),
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
                        html.P("Closing Soon", className="card-text"),
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
                        html.P("Main Category", className="card-text"),
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
        return dcc.Graph(figure={"data": [], "layout": {"title": "No data available"}})

    # Count aids by category
    category_counts = {}
    for aid in aids_data:
        category = aid.get("category", "otros")
        category_counts[category] = category_counts.get(category, 0) + 1

    # Create pie chart
    fig = px.pie(
        values=list(category_counts.values()),
        names=list(category_counts.keys()),
        title="Distribution by Category",
    )

    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(showlegend=True, height=400, margin={"t": 50, "b": 50, "l": 50, "r": 50})

    return dcc.Graph(figure=fig)


def create_scope_chart(aids_data: list[dict]) -> dcc.Graph:
    """Create a bar chart showing aids by geographic scope."""
    if not aids_data:
        return dcc.Graph(figure={"data": [], "layout": {"title": "No data available"}})

    # Count aids by scope
    scope_counts = {}
    for aid in aids_data:
        scope = aid.get("scope", {}).get("scope", "nacional")
        scope_name = {
            "nacional": "National",
            "autonomica": "Regional",
            "provincial": "Provincial",
            "local": "Local",
            "europea": "European",
        }.get(scope, scope.title())

        scope_counts[scope_name] = scope_counts.get(scope_name, 0) + 1

    # Create bar chart
    fig = px.bar(
        x=list(scope_counts.keys()),
        y=list(scope_counts.values()),
        title="Distribution by Geographic Scope",
        labels={"x": "Scope", "y": "Number of Aid"},
    )

    fig.update_layout(height=400, margin={"t": 50, "b": 50, "l": 50, "r": 50})

    return dcc.Graph(figure=fig)


def create_status_timeline(aids_data: list[dict]) -> dcc.Graph:
    """Create a timeline showing aids closing dates."""
    if not aids_data:
        return dcc.Graph(figure={"data": [], "layout": {"title": "No data available"}})

    # Filter aids with closing dates
    aids_with_dates = []
    for aid in aids_data:
        closing_date = aid.get("closing_date")
        if closing_date:
            parsed_date = parse_aid_date(closing_date)
            if parsed_date:
                aids_with_dates.append(
                    {
                        "title": aid.get("title", "Untitled")[:50] + "...",
                        "closing_date": parsed_date,
                        "category": aid.get("category", "otros"),
                        "status": aid.get("status", "abierta"),
                    }
                )

    if not aids_with_dates:
        return dcc.Graph(
            figure={
                "data": [],
                "layout": {"title": "No aid with closing dates available"},
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
                marker={"size": 10, "color": color},
                name=aid["category"],
                showlegend=False,
            )
        )

    fig.update_layout(
        title="Upcoming Closing Dates",
        xaxis_title="Closing Date",
        yaxis_title="Aid",
        height=600,
        yaxis={"showticklabels": False},
        margin={"t": 50, "b": 50, "l": 50, "r": 200},
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
                            html.Label("Filter by Category:"),
                            dcc.Dropdown(
                                id="category-filter",
                                options=[
                                    {"label": "All", "value": "all"},
                                    {"label": "Housing", "value": "vivienda"},
                                    {"label": "Employment", "value": "empleo"},
                                    {"label": "Education", "value": "educacion"},
                                    {"label": "Health", "value": "salud"},
                                    {"label": "Youth", "value": "juventud"},
                                    {"label": "Family", "value": "familia"},
                                    {"label": "Emergency", "value": "emergencia"},
                                    {"label": "Business", "value": "empresa"},
                                    {"label": "Other", "value": "otros"},
                                ],
                                value="all",
                                multi=False,
                            ),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Filter by Status:"),
                            dcc.Dropdown(
                                id="status-filter",
                                options=[
                                    {"label": "All", "value": "all"},
                                    {"label": "Open", "value": "abierta"},
                                    {"label": "Closed", "value": "cerrada"},
                                    {
                                        "label": "Under Evaluation",
                                        "value": "en_evaluacion",
                                    },
                                    {"label": "Resolved", "value": "resuelta"},
                                    {"label": "Upcoming", "value": "proxima"},
                                ],
                                value="abierta",
                                multi=False,
                            ),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Filter by Scope:"),
                            dcc.Dropdown(
                                id="scope-filter",
                                options=[
                                    {"label": "All", "value": "all"},
                                    {"label": "National", "value": "nacional"},
                                    {"label": "Regional", "value": "autonomica"},
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
                            html.Label("Only urgent (< 7 days):"),
                            dcc.Checklist(
                                id="urgent-filter",
                                options=[{"label": "Only urgent", "value": "urgent"}],
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
        return dbc.Alert("No aid data available.", color="info")

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
                amount_info = f"Up to €{amount['max_amount']}"
            elif amount.get("min_amount"):
                amount_info = f"From €{amount['min_amount']}"

        table_data.append(
            {
                "title": aid.get("title", "Untitled"),
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
                "name": "Title",
                "id": "title",
                "type": "text",
                "presentation": "markdown",
            },
            {"name": "Category", "id": "category", "type": "text"},
            {"name": "Status", "id": "status", "type": "text"},
            {"name": "Scope", "id": "scope", "type": "text"},
            {"name": "Entity", "id": "organizing_entity", "type": "text"},
            {"name": "Closing Date", "id": "closing_date", "type": "datetime"},
            {"name": "Days Remaining", "id": "days_left", "type": "numeric"},
            {"name": "Amount", "id": "amount", "type": "text"},
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
                "backgroundColor": "#3e2723",  # Dark reddish background for urgency
                "color": "#ffcdd2",  # Light red text
            },
            {
                "if": {"filter_query": "{status} = Cerrada"},
                "backgroundColor": "#212121",
                "color": "#757575",
            },
        ],
        tooltip_data=[{column: {"value": str(row[column]), "type": "markdown"} for column in row} for row in table_data],
        css=[
            {
                "selector": ".dash-table-tooltip",
                "rule": "background-color: grey; font-family: monospace; color: white",
            }
        ],
    )

    return html.Div([html.H5("Public Aid Table", className="mb-3"), table])


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
                                        placeholder="Search aid by title, description or keywords...",
                                        type="text",
                                    ),
                                    dbc.Button(
                                        "Search",
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
                                "Clear Filters",
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
                                "Update Data",
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
                        html.H4("No data available", className="alert-heading"),
                        html.P("No Spanish public aid data found."),
                        html.Hr(),
                        html.P(
                            "Make sure to run the Spanish public aid ETL first:",
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
            html.H3("Spanish Public Aid", className="mb-4"),
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
                                    "Last updated: ",
                                    html.Span(
                                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        id="last-updated-time",
                                    ),
                                    " | ",
                                    html.A(
                                        "View source code",
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
            return dbc.Alert("No data available.", color="info")

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
