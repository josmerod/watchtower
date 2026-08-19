"""Scavenging Tab Component for Watchtower Dashboard
Improved with premium table layout, clickable links, and search functionality.
"""

import logging
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

from src.services.data_loader import (
    format_article_date as format_article_date_shared,
)
from src.services.data_loader import (
    get_sortable_date,
    load_data_from_file,
)
from src.web.dashboard.components.shared.table import (
    render_items_table,
    text_cell,
    title_cell,
)
from src.web.dashboard.search_utils import (
    create_search_input,
    filter_content,
)
from src.web.dashboard.utils import get_data_path

# Set up logging
logger = logging.getLogger(__name__)

DATA_DIR = Path(get_data_path("scavenging"))

# --- Data Loading ---


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

        # Add Humble Books data if it exists
        humble_file = DATA_DIR / "humble_books.json"
        if humble_file.exists():
            categories["humble_books"] = humble_file

        # Add Epic Games free promotions if they exist
        epic_file = DATA_DIR / "epic_free_games.json"
        if epic_file.exists():
            categories["epic_free"] = epic_file

        logger.info(f"Discovered {len(categories)} scavenging categories: {list(categories.keys())}")
        return categories
    except Exception as e:
        logger.error(f"Error discovering categories: {e}")
        return {}


def get_scavenging_data(category_key):
    """Load data for a specific category."""
    categories_map = discover_categories()
    if category_key not in categories_map:
        return []
    return load_data_from_file(str(categories_map[category_key]))


# --- Layout Generation ---

MAX_ITEMS_PER_TAB = 100


def create_scavenging_table(items, search_term: str = ""):
    """Create the scavenging table via the shared builder (spec 15 M1).

    Title/summary cells render with real highlight marks when searching
    (see search_utils.highlight_segments).
    """
    columns = [
        {
            "header": "Title / Resource",
            "cell": lambda item: title_cell(
                item,
                search_term,
                title_fields=("title",),
                url_fields=("link", "url"),
                subtitle=f"Source: {item['source']}" if item.get("source") else None,
            ),
        },
        {
            "header": "Details",
            "cell": lambda item: text_cell(
                item.get("summary") if isinstance(item.get("summary"), str) else str(item.get("summary", "")), search_term, className="small", style={"maxWidth": "400px", "whiteSpace": "normal"}
            ),
        },
        {"header": "Price/Type", "cell": _scavenging_price_badges},
        {"header": "Date Added", "cell": lambda item: str(format_article_date_shared(item)), "td_kwargs": {"className": "text-nowrap font-monospace small"}},
    ]
    return render_items_table(items, columns, empty_message="No entries found matching your criteria.", wrap_scroll=False)


def _scavenging_price_badges(item):
    """Price + deal-type badges for the scavenging table."""
    badges = []
    price = item.get("price", "N/A")
    if price and price != "N/A":
        badges.append(dbc.Badge(f"💰 {price}", color="success", className="me-1"))
    deal_type = item.get("deal_type") or item.get("category", "General")
    if deal_type:
        badges.append(dbc.Badge(str(deal_type).upper(), color="primary", className="me-1"))
    return html.Div(badges)


def render_scavenging_tab() -> html.Div:
    """Render the main Scavenging tab layout."""
    categories_map = discover_categories()

    if not categories_map:
        return dbc.Alert("No scavenging data found. Please run the ETL processes.", color="warning", className="m-4")

    category_tabs = []
    for category in sorted(categories_map.keys()):
        source_display_name = category.replace("_", " ").capitalize()
        tab_search_id = f"scavenging-search-{category}"

        # Initial data for store
        initial_data = get_scavenging_data(category)
        initial_data.sort(key=get_sortable_date, reverse=True)

        tab_content = html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                create_search_input(
                                    input_id=tab_search_id,
                                    placeholder=f"Search in {source_display_name}...",
                                    clear_button=True,
                                )
                            ],
                            width=True,
                        )
                    ],
                    className="mb-3 mt-3",
                ),
                # Full dataset in the Store so search reaches history beyond
                # the display cap; the cap is applied at render time only.
                dcc.Store(id=f"{tab_search_id}-data", data=initial_data),
                html.Div(create_scavenging_table(initial_data[:MAX_ITEMS_PER_TAB]), id=f"{tab_search_id}-results", style={"maxHeight": "800px", "overflowY": "auto"}),
            ],
            className="p-3",
        )

        category_tabs.append(dbc.Tab(label=source_display_name, tab_id=f"tab-scavenging-{category}", children=tab_content))

    return html.Div(
        [
            html.H3("⛏️ Project Scavenging", className="mb-4"),
            html.P("Automated monitoring of free resources, audiobooks, and deal alerts.", className="text-muted"),
            dbc.Tabs(id="scavenging-main-tabs", children=category_tabs, active_tab=f"tab-scavenging-{sorted(categories_map.keys())[0]}"),
        ],
        className="p-4",
    )


def register_scavenging_callbacks(app):
    """Register search and filter callbacks for Scavenging."""
    # We discover categories again to register callbacks for all of them
    categories_map = discover_categories()

    for category in categories_map:
        search_id = f"scavenging-search-{category}"

        @app.callback(
            Output(f"{search_id}-results", "children"),
            [Input(search_id, "value")],
            State(f"{search_id}-data", "data"),
        )
        def update_scavenging_search(search_term, cached_data, current_search_id=search_id):
            if not cached_data:
                return dbc.Alert("No data loaded.", color="info")

            if search_term:
                searchable_fields = ["title", "summary", "source", "seller", "deal_type", "category"]
                filtered_items = filter_content(search_term, cached_data, searchable_fields)
                table = create_scavenging_table(filtered_items, search_term=search_term)
                return html.Div(
                    [
                        dbc.Alert(f"⛏️ Found {len(filtered_items)} items matching '{search_term}'", color="success", className="mb-3"),
                        table,
                    ]
                )

            return create_scavenging_table(cached_data[:MAX_ITEMS_PER_TAB])

        @app.callback(
            Output(search_id, "value", allow_duplicate=True),
            Input(f"{search_id}-clear", "n_clicks"),
            prevent_initial_call=True,
        )
        def clear_scavenging_search(n_clicks):
            if n_clicks:
                return ""
            return dash.no_update
