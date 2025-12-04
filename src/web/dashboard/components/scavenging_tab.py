"""Scavenging Tab Component for Watchtower Dashboard"""

import logging
from pathlib import Path

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, dash_table, dcc, html

# Set up logging
logger = logging.getLogger(__name__)

DATA_DIR = Path("data/scavenging")


def load_category_file(json_path: Path) -> pd.DataFrame:
    """Load a single JSON file into a DataFrame"""
    try:
        if not json_path.exists():
            return pd.DataFrame()

        data = pd.read_json(json_path)
        if not data.empty and "published" in data.columns:
            # Ensure published column is datetime for sorting
            data["published"] = pd.to_datetime(data["published"], errors="coerce")
        return data
    except ValueError as e:
        logger.error(f"Error loading {json_path}: {e}")
        return pd.DataFrame()


def discover_categories() -> dict[str, Path]:
    """Return a mapping of category name -> aggregated JSON path"""
    try:
        if not DATA_DIR.exists():
            return {}

        # Get RSS entries files
        files = DATA_DIR.glob("*_rss_entries.json")
        categories = {f.stem.replace("_rss_entries", ""): f for f in files}

        # Add Gumroad data if it exists
        gumroad_file = DATA_DIR / "gumroad_free_products.json"
        if gumroad_file.exists():
            categories["gumroad_free"] = gumroad_file

        # Add Viajeros Piratas data if it exists
        viajeros_file = DATA_DIR / "viajeros_piratas_deals.json"
        if viajeros_file.exists():
            categories["viajeros_piratas"] = viajeros_file

        logger.info(f"Discovered {len(categories)} scavenging categories: {list(categories.keys())}")
        return categories
    except Exception as e:
        logger.error(f"Error discovering categories: {e}")
        return {}


def create_category_table(category: str, df: pd.DataFrame) -> html.Div:
    """Create a table for a specific category's data"""
    try:
        if df.empty:
            return dbc.Alert(
                f"No entries available for {category}.",
                color="warning",
                className="alert-warning",
            )

        # Sort newest first
        if "published" in df.columns:
            df = df.sort_values(by="published", ascending=False)

        # Prepare columns for display
        rename_map = {
            "title": "Título",
            "link": "Enlace",
            "published": "Publicado",
            "summary": "Resumen",
            "source": "Fuente",
            "price": "Precio",
            "seller": "Vendedor",
            "category": "Categoría",
            "deal_type": "Tipo de Oferta",
            "currency": "Moneda",
        }

        existing_columns = [c for c in rename_map if c in df.columns]
        df_display = df[existing_columns].copy()

        # Format published dates
        if "published" in df_display.columns:
            df_display["published"] = df_display["published"].dt.strftime("%Y-%m-%d %H:%M")

        # Rename columns
        df_display = df_display.rename(columns=rename_map)

        # Create table with dark theme styling
        table = dash_table.DataTable(
            id=f"scavenging-table-{category}",
            data=df_display.to_dict("records"),
            columns=[
                {
                    "name": col,
                    "id": col,
                    "type": "text",
                    "presentation": "markdown" if col == "Enlace" else "input",
                }
                for col in df_display.columns
            ],
            style_cell={
                "textAlign": "left",
                "padding": "12px 16px",
                "fontSize": "14px",
                "fontFamily": "Poppins, sans-serif",
                "maxWidth": "200px",
                "overflow": "hidden",
                "textOverflow": "ellipsis",
                "backgroundColor": "#2D2B55",
                "color": "#CDD6F4",
                "border": "1px solid #3C3970",
            },
            style_header={
                "backgroundColor": "#3C3970",
                "color": "#E2E8F0",
                "fontWeight": "600",
                "borderBottom": "2px solid #A37FFF",
                "textTransform": "uppercase",
                "fontSize": "0.85em",
                "letterSpacing": "0.5px",
            },
            style_data={
                "backgroundColor": "#2D2B55",
                "color": "#CDD6F4",
                "border": "1px solid #3C3970",
                "whiteSpace": "normal",
                "height": "auto",
            },
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#252343"},
                {
                    "if": {"state": "selected"},
                    "backgroundColor": "#A37FFF",
                    "color": "#1E1E2E",
                },
            ],
            style_cell_conditional=[
                {
                    "if": {"column_id": "Título"},
                    "minWidth": "200px",
                    "width": "200px",
                    "maxWidth": "300px",
                },
                {
                    "if": {"column_id": "Enlace"},
                    "minWidth": "100px",
                    "width": "100px",
                    "maxWidth": "100px",
                },
                {
                    "if": {"column_id": "Resumen"},
                    "minWidth": "300px",
                    "width": "300px",
                    "maxWidth": "400px",
                },
                {
                    "if": {"column_id": "Precio"},
                    "minWidth": "80px",
                    "width": "80px",
                    "maxWidth": "80px",
                },
                {
                    "if": {"column_id": "Vendedor"},
                    "minWidth": "120px",
                    "width": "120px",
                    "maxWidth": "150px",
                },
                {
                    "if": {"column_id": "Categoría"},
                    "minWidth": "100px",
                    "width": "100px",
                    "maxWidth": "120px",
                },
                {
                    "if": {"column_id": "Tipo de Oferta"},
                    "minWidth": "100px",
                    "width": "100px",
                    "maxWidth": "120px",
                },
                {
                    "if": {"column_id": "Moneda"},
                    "minWidth": "60px",
                    "width": "60px",
                    "maxWidth": "60px",
                },
            ],
            sort_action="native",
            filter_action="native",
            page_action="native",
            page_current=0,
            page_size=15,
            tooltip_data=[{column: {"value": str(value), "type": "text"} for column, value in row.items()} for row in df_display.to_dict("records")],
            tooltip_duration=None,
        )

        # Download buttons
        download_section = dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Button(
                            "📥 Descargar CSV",
                            id=f"download-csv-{category}",
                            color="primary",
                            size="sm",
                            className="me-2",
                        ),
                        dcc.Download(id=f"download-csv-data-{category}"),
                    ],
                    width="auto",
                ),
                dbc.Col(
                    [
                        dbc.Button(
                            "📥 Descargar JSON",
                            id=f"download-json-{category}",
                            color="secondary",
                            size="sm",
                        ),
                        dcc.Download(id=f"download-json-data-{category}"),
                    ],
                    width="auto",
                ),
            ],
            className="mb-3",
        )

        return html.Div(
            [
                html.H5(f"📁 {category.capitalize()}", className="mb-3"),
                html.P(
                    f"Mostrando {len(df_display)} elementos",
                    className="text-muted mb-3",
                ),
                table,
                html.Hr(className="my-4"),
                download_section,
            ]
        )

    except Exception as e:
        logger.error(f"Error creating category table for {category}: {e}")
        return dbc.Alert(
            f"Error loading data for category {category}: {e!s}",
            color="danger",
            className="alert-danger",
        )


def render_scavenging_tab() -> html.Div:
    """Render the scavenging tab"""
    try:
        categories_map = discover_categories()

        if not categories_map:
            return html.Div(
                [
                    dbc.Alert(
                        [
                            html.H4(
                                "No Scavenging Data Available",
                                className="alert-heading",
                            ),
                            html.P("No scavenging data found. Run the Scavenging ETL to populate data."),
                            html.Hr(),
                            html.P(
                                f"Expected data location: {DATA_DIR}/*_rss_entries.json",
                                className="mb-0",
                            ),
                        ],
                        color="info",
                        className="alert-info",
                    )
                ],
                className="p-4",
            )

        # Create tabs for each category
        category_tabs = []
        category_content = []

        for category in sorted(categories_map.keys()):
            tab_id = f"scavenging-{category}"

            # Load data for this category
            df = load_category_file(categories_map[category])

            # Create tab content
            category_content.append(
                dcc.Tab(
                    id=tab_id,
                    value=tab_id,
                    label=category.capitalize(),
                    children=[html.Div([create_category_table(category, df)], className="p-3")],
                )
            )

        return html.Div(
            [
                # Header
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H2("⛏️ Scavenging RSS Feeds", className="mb-3"),
                                html.P(
                                    f"Displaying RSS entries across {len(categories_map)} categories",
                                    className="text-muted",
                                ),
                            ]
                        )
                    ],
                    className="mb-4",
                ),
                # Tabs for different categories
                dcc.Tabs(
                    id="scavenging-categories-tabs",
                    value=(f"scavenging-{sorted(categories_map.keys())[0]}" if categories_map else ""),
                    children=category_content,
                    style={"marginBottom": "20px"},
                ),
            ],
            className="p-4",
            id="scavenging-tab-content",
        )

    except Exception as e:
        logger.error(f"Error rendering scavenging tab: {e}")
        return html.Div(
            [
                dbc.Alert(
                    f"Error loading scavenging tab: {e!s}",
                    color="danger",
                    className="alert-danger",
                )
            ],
            className="p-4",
        )


def register_scavenging_callbacks(app):
    """Register callbacks for scavenging tab"""
    # Get categories for callback registration
    categories_map = discover_categories()

    # Register download callbacks for each category
    for category in categories_map.keys():
        # CSV Download callback
        @app.callback(
            Output(f"download-csv-data-{category}", "data"),
            Input(f"download-csv-{category}", "n_clicks"),
            prevent_initial_call=True,
        )
        def download_csv(n_clicks, cat=category):
            if n_clicks:
                df = load_category_file(categories_map[cat])
                if not df.empty:
                    return dcc.send_data_frame(df.to_csv, f"{cat}_scavenging.csv", index=False)
            return None

        # JSON Download callback
        @app.callback(
            Output(f"download-json-data-{category}", "data"),
            Input(f"download-json-{category}", "n_clicks"),
            prevent_initial_call=True,
        )
        def download_json(n_clicks, cat=category):
            if n_clicks:
                df = load_category_file(categories_map[cat])
                if not df.empty:
                    json_str = df.to_json(orient="records", indent=2, force_ascii=False)
                    return dict(
                        content=json_str,
                        filename=f"{cat}_scavenging.json",
                        type="application/json",
                    )
            return None
