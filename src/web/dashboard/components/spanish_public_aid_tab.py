"""Spanish Public Aid Dashboard Component."""

import logging
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

logger = logging.getLogger(__name__)

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


class BdnsConvocatoriasRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for BDNS convocatorias data (SNPSAP API ETL output)."""

    def __init__(self):
        """Initialize BDNS convocatorias repository."""
        data_path = get_data_path("spanish_public_aid", "output", "bdns_convocatorias_latest.json")
        super().__init__(
            data_path=Path(data_path),
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform JSON data into list of BDNS convocatoria items.

        Args:
            raw_data: Raw JSON data

        Returns:
            List of convocatoria dictionaries
        """
        if isinstance(raw_data, list):
            return [item for item in raw_data if isinstance(item, dict)]
        elif isinstance(raw_data, dict):
            items = raw_data.get("items")
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        return []


# Create singleton instance
bdns_convocatorias_repo = BdnsConvocatoriasRepository()


def load_bdns_convocatorias(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Load BDNS convocatorias data using the repository pattern."""
    try:
        items = bdns_convocatorias_repo.get(force_refresh=force_refresh)
        return items or []
    except Exception as e:
        logger.warning(f"Could not load BDNS convocatorias data: {e}")
        return []


def get_bdns_last_updated() -> str:
    """Return the mtime of the BDNS convocatorias file as a freshness signal."""
    path = Path(get_data_path("spanish_public_aid", "output", "bdns_convocatorias_latest.json"))
    if path.exists():
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    return "no data file"


def load_spanish_aid_data(force_refresh: bool = False):
    """Load Spanish public aid data using repository pattern (NEW)."""
    aids_data = []
    stats_data = {}

    try:
        aids_data = spanish_aid_repo.get(force_refresh=force_refresh)
        if not aids_data:
            aids_data = []

        stats_data = spanish_aid_stats_repo.get(force_refresh=force_refresh)
        if not stats_data:
            stats_data = {}

    except Exception as e:
        logger.warning(f"Could not load Spanish aid data: {e}")

    return aids_data, stats_data


def get_data_last_updated() -> str:
    """Return the mtime of the aids data file as an honest freshness signal."""
    path = Path(get_data_path("spanish_public_aid", "output", "spanish_public_aid_latest.json"))
    if path.exists():
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    return "no data file"


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

    # Per-source stats from the ETL (spanish_public_aid_stats_latest.json):
    # how many sources contributed and how fresh each run was.
    source_stats = stats_data.get("sources", {}) if isinstance(stats_data, dict) else {}
    contributing_sources = len([s for s, v in source_stats.items() if isinstance(v, dict) and v.get("count")])

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
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.H4(f"{contributing_sources or '—'}", className="card-title text-secondary"),
                        html.P("ETL Sources", className="card-text"),
                    ]
                )
            ],
            className="text-center mb-3",
        ),
    ]

    return dbc.Row([dbc.Col(card, width=3) for card in cards], className="g-2")


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
            ),
            # Beneficiary-type filter row (personal / NGO / business)
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Beneficiary:"),
                            dcc.Dropdown(
                                id="beneficiary-filter",
                                # Values match SpanishPublicAidModel.beneficiary_type enum
                                options=[
                                    {"label": "All", "value": "all"},
                                    {"label": "👤 Individuals (persona física)", "value": "persona_fisica"},
                                    {"label": "🏢 Business / Company", "value": "empresa"},
                                    {"label": "🤝 NGO / Non-profit", "value": "ong"},
                                    {"label": "🏛️ Public body", "value": "entidad_publica"},
                                    {"label": "🎓 Educational institution", "value": "institucion_educativa"},
                                    {"label": "🔀 Mixed", "value": "mixto"},
                                ],
                                value="all",
                                multi=False,
                            ),
                        ],
                        width=4,
                    ),
                ],
                className="mb-3",
            ),
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


def _format_bdns_amount(item: dict) -> str:
    """Format the BDNS budget for the table (Spanish style, dash when unknown)."""
    amounts = item.get("amounts") or {}
    budget = amounts.get("total_budget")
    if budget is None:
        return "—"
    text = f"{budget:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{text} €"


def _bdns_days_left(item: dict) -> int | str:
    """Days until the BDNS application deadline, or dash when unknown."""
    deadline = parse_aid_date(str(item.get("deadline_date") or ""))
    if not deadline:
        return "—"
    return max(0, (deadline - datetime.now()).days)


def create_bdns_section(convocatorias: list[dict]) -> html.Div:
    """Create the BDNS recent convocatorias section (spec 09 M1).

    Shows convocatorias fetched from the public SNPSAP API with real dates
    and amounts — data the scraped sources cannot provide.

    Args:
        convocatorias: Normalized BDNS convocatoria items.

    Returns:
        Dash layout for the section.
    """
    if not convocatorias:
        return html.Div(
            [
                html.Hr(),
                html.H4("🏛️ BDNS — Convocatorias recientes"),
                dbc.Alert(
                    [
                        "Sin datos de BDNS todavía. Ejecuta el ETL: ",
                        html.Code("uv run python src/etl/spanish_public_aid/bdns_convocatorias_etl.py"),
                    ],
                    color="info",
                ),
            ]
        )

    total = len(convocatorias)
    with_deadline = len([c for c in convocatorias if c.get("deadline_date")])
    with_budget = len([c for c in convocatorias if (c.get("amounts") or {}).get("total_budget") is not None])
    closing_soon = len([c for c in convocatorias if isinstance(_bdns_days_left(c), int) and 0 < _bdns_days_left(c) <= 7])

    badges = dbc.Row(
        [
            dbc.Col(dbc.Badge(f"Total: {total}", color="primary", pill=True, className="me-2")),
            dbc.Col(dbc.Badge(f"Con plazo: {with_deadline}", color="info", pill=True, className="me-2")),
            dbc.Col(dbc.Badge(f"Con cuantía: {with_budget}", color="success", pill=True, className="me-2")),
            dbc.Col(dbc.Badge(f"Cierran ≤ 7 días: {closing_soon}", color="warning", pill=True, className="me-2")),
        ],
        className="mb-3 g-1",
    )

    table_data = []
    for item in convocatorias:
        title = item.get("title", "Sin título")
        url = item.get("url", "")
        deadline = parse_aid_date(str(item.get("deadline_date") or ""))
        deadline_str = deadline.strftime("%Y-%m-%d") if deadline else ("indefinido" if item.get("open_ended") else "—")
        registered = parse_aid_date(str(item.get("registered_date") or ""))
        table_data.append(
            {
                "title": f"[{title}]({url})" if url else title,
                "org": item.get("org", "N/A"),
                "scope": item.get("scope", "N/A"),
                "amount": _format_bdns_amount(item),
                "registered": registered.strftime("%Y-%m-%d") if registered else "—",
                "deadline": deadline_str,
                "days_left": _bdns_days_left(item),
                "bdns_id": item.get("bdns_id", ""),
            }
        )

    table = dash_table.DataTable(
        id="bdns-convocatorias-table",
        data=table_data,
        columns=[
            {"name": "Convocatoria", "id": "title", "type": "text", "presentation": "markdown"},
            {"name": "Organismo", "id": "org", "type": "text"},
            {"name": "Ámbito", "id": "scope", "type": "text"},
            {"name": "Cuantía", "id": "amount", "type": "text"},
            {"name": "Registro", "id": "registered", "type": "datetime"},
            {"name": "Fin de plazo", "id": "deadline", "type": "datetime"},
            {"name": "Días", "id": "days_left", "type": "numeric"},
            {"name": "BDNS", "id": "bdns_id", "type": "text"},
        ],
        page_size=15,
        sort_action="native",
        filter_action="native",
        style_cell={
            "textAlign": "left",
            "fontSize": "13px",
            "fontFamily": "Arial, sans-serif",
            "padding": "8px",
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
                "width": "45%",
            },
            {
                "if": {"filter_query": "{days_left} <= 7 && {days_left} > 0"},
                "backgroundColor": "#3e2723",
                "color": "#ffcdd2",
            },
        ],
        markdown_options={"link_target": "_blank"},
    )

    return html.Div(
        [
            html.Hr(),
            html.H4("🏛️ BDNS — Convocatorias recientes", className="mb-1"),
            html.P(
                [
                    "Últimas convocatorias registradas en la Base de Datos Nacional de Subvenciones (API pública SNPSAP), ",
                    "con plazos y cuantías reales. Fuente: ",
                    html.A("infosubvenciones", href="https://www.infosubvenciones.es/bdnstrans/GE/es/bdnstrans/convocatorias", target="_blank"),
                    f" · Datos actualizados: {get_bdns_last_updated()}",
                ],
                className="text-muted mb-2",
                style={"fontSize": "0.85rem"},
            ),
            badges,
            table,
        ]
    )


def _create_scope_tabs(aids_data: list[dict]) -> html.Div:
    """Create geographic-scope quick-filter buttons (local → global).

    Each button shows the count of aids for that scope so users can see at a
    glance how much aid is available at each geographic level.
    """
    scope_order = [
        ("burjassot", "🏠 Burjassot"),
        ("valencia", "🏛️ Valencia"),
        ("comunidad_valenciana", "🌅 Comunidad Valenciana"),
        ("nacional", "🇪🇸 España"),
    ]

    def _count_scope(scope_key: str) -> int:
        count = 0
        for aid in aids_data:
            aid_scope = aid.get("scope", {})
            if isinstance(aid_scope, dict):
                s = aid_scope.get("scope", "")
            else:
                s = str(aid_scope)
            if scope_key in s or (scope_key == "nacional" and "nacional" in s):
                count += 1
        return count

    buttons = []
    for key, label in scope_order:
        count = _count_scope(key)
        buttons.append(
            dbc.Button(
                [label, dbc.Badge(count, color="light", className="ms-2", pill=True)],
                id=f"scope-filter-{key}",
                color="outline-success",
                size="sm",
                className="me-2 mb-2",
            )
        )
    buttons.append(
        dbc.Button(
            ["📋 All", dbc.Badge(len(aids_data), color="light", className="ms-2", pill=True)],
            id="scope-filter-all",
            color="success",
            size="sm",
            className="me-2 mb-2",
        )
    )
    return html.Div(buttons, className="d-flex flex-wrap align-items-center")


def render_spanish_public_aid_tab():
    """Render the main Spanish Public Aid tab."""
    # Load data
    aids_data, stats_data = load_spanish_aid_data()
    bdns_convocatorias = load_bdns_convocatorias()

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
                ),
                # BDNS section still renders when only the API-based ETL has run
                *([] if not bdns_convocatorias else [create_bdns_section(bdns_convocatorias)]),
            ],
            fluid=True,
        )

    return html.Div(
        [
            html.H3(
                [html.I(className="fas fa-hand-holding-heart me-2 text-success"), "Ayudas Públicas"],
                className="mb-1",
            ),
            html.P(
                "Public grants and aid, organized from local to national scope: Burjassot → Valencia → Comunidad Valenciana → Spain.",
                className="text-muted mb-3",
                style={"fontSize": "0.9rem"},
            ),
            # Geographic scope quick-filter tabs (local → global)
            _create_scope_tabs(aids_data),
            html.Hr(className="mb-3"),
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
            # BDNS recent convocatorias (API data with real deadlines/amounts)
            create_bdns_section(bdns_convocatorias),
            # Last updated info (data file mtime — reflects actual data freshness)
            html.Div(
                [
                    html.Hr(),
                    html.P(
                        [
                            html.Small(
                                [
                                    "Last updated: ",
                                    html.Span(get_data_last_updated(), id="last-updated-time"),
                                    " | ",
                                    "Data: data/spanish_public_aid/output/spanish_public_aid_latest.json + bdns_convocatorias_latest.json (ETL runs via run_all_etl.sh)",
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
            Input("beneficiary-filter", "value"),
            # Geographic quick-filter buttons
            Input("scope-filter-burjassot", "n_clicks"),
            Input("scope-filter-valencia", "n_clicks"),
            Input("scope-filter-comunidad_valenciana", "n_clicks"),
            Input("scope-filter-nacional", "n_clicks"),
            Input("scope-filter-all", "n_clicks"),
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
        beneficiary_filter,
        burjassot_clicks,
        valencia_clicks,
        cv_clicks,
        nacional_clicks,
        all_clicks,
    ):
        """Update the aids table based on filters."""
        # Determine what triggered this callback
        ctx = dash.callback_context
        quick_scope = None
        force_refresh = False
        if ctx.triggered:
            trigger_prop = ctx.triggered[0]["prop_id"]
            trigger_id = trigger_prop.split(".")[0]
            if trigger_id.startswith("scope-filter-") and not trigger_id.startswith("scope-filter-all"):
                quick_scope = trigger_id.removeprefix("scope-filter-")
            elif trigger_id == "scope-filter-all":
                quick_scope = "all"
            elif trigger_id == "refresh-data-button":
                force_refresh = True

        # Load fresh data (bypass the repository cache when refreshing)
        aids_data, _ = load_spanish_aid_data(force_refresh=force_refresh)

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

        # Geographic quick-filter button (finer-grained than the dropdown)
        if quick_scope and quick_scope != "all":
            quick_filtered = []
            for aid in filtered_data:
                aid_scope = aid.get("scope", {})
                s = aid_scope.get("scope", "") if isinstance(aid_scope, dict) else str(aid_scope)
                if quick_scope in s:
                    quick_filtered.append(aid)
            filtered_data = quick_filtered
        elif scope_filter and scope_filter != "all":
            # Scope dropdown
            filtered_data = [aid for aid in filtered_data if aid.get("scope", {}).get("scope") == scope_filter]

        # Beneficiary filter (values match SpanishPublicAidModel.beneficiary_type)
        if beneficiary_filter and beneficiary_filter != "all":
            filtered_data = [aid for aid in filtered_data if aid.get("beneficiary_type") == beneficiary_filter]

        # Urgent filter: closing within the next 7 days (not already closed)
        if "urgent" in (urgent_filter or []):
            urgent_aids = []
            for aid in filtered_data:
                if aid.get("closing_date"):
                    closing_date = parse_aid_date(aid["closing_date"])
                    if closing_date and 0 <= (closing_date - datetime.now()).days <= 7:
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
            Output("beneficiary-filter", "value"),
        ],
        Input("clear-filters-button", "n_clicks"),
    )
    def clear_filters(n_clicks):
        """Clear all filters."""
        if n_clicks and n_clicks > 0:
            return "all", "all", "all", [], "", "all"

        # Return current values (no change)
        return (
            dash.no_update,
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
