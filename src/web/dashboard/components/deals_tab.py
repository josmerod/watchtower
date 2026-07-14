import json
import logging
import sys
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.services.data_loader import (
    DEALS_SOURCES_CONFIG,
    get_sortable_date,
    load_data_from_file,
)
from src.services.data_loader import (
    format_article_date as format_article_date_shared,
)
from src.web.dashboard.search_utils import (
    create_search_input,
    filter_content,
)

# Configure logging
logger = logging.getLogger(__name__)

# --- Data Loading ---


def get_all_deals_data():
    """Load fresh deals data from all configured sources."""
    import time

    global _DEALS_CACHE
    now = time.time()
    try:
        if _DEALS_CACHE and now - _DEALS_CACHE.get("ts", 0) < 60:
            return _DEALS_CACHE["data"]
    except NameError:
        pass

    data = {source_key: load_data_from_file(config["path"]) for source_key, config in DEALS_SOURCES_CONFIG.items()}
    _DEALS_CACHE = {"ts": now, "data": data}
    return data


def format_deal_date(deal):
    """Wrapper for shared formatting."""
    return format_article_date_shared(deal)


# --- Layout Generation ---

MAX_DEALS_PER_SOURCE = 50


def create_deals_source_tab_content(source_keys, combined_name=None):
    """Creates the content for a deals tab as a table with search functionality."""
    if isinstance(source_keys, str):
        source_keys = [source_keys]
        source_display_name = DEALS_SOURCES_CONFIG[source_keys[0]]["name"]
        tab_search_id = f"v2-deals-search-{'-'.join(source_keys)}"

    all_deals_data = get_all_deals_data()
    all_deals_for_tab = []

    for key in source_keys:
        deals_from_source = all_deals_data.get(key, [])
        for deal in deals_from_source:
            deal["source_display_name"] = deal.get("source", DEALS_SOURCES_CONFIG[key]["name"])
        all_deals_for_tab.extend(deals_from_source)

    all_deals_for_tab.sort(key=get_sortable_date, reverse=True)

    deals_data_store = dcc.Store(
        data=json.dumps(all_deals_for_tab[:MAX_DEALS_PER_SOURCE]),
        id=f"{tab_search_id}-data",
    )

    if not all_deals_for_tab:
        return dbc.Alert(f"No deals available for {source_display_name}.", color="info")

    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Deal Title"),
                    html.Th("Categories"),
                    html.Th("Date Added"),
                ]
            )
        )
    ]

    table_body_rows = []
    for deal in all_deals_for_tab[:MAX_DEALS_PER_SOURCE]:
        title = deal.get("title", "No Title")
        url = deal.get("url") or deal.get("link")
        categories = deal.get("categories", [])
        categories_display = ", ".join(categories) if categories else "General"
        date_display = format_deal_date(deal)

        table_body_rows.append(
            html.Tr(
                [
                    html.Td(html.A(str(title), href=url, target="_blank") if url else str(title)),
                    html.Td(dbc.Badge(str(categories_display), color="info", className="me-1")),
                    html.Td(str(date_display)),
                ]
            )
        )

    table = dbc.Table(
        table_header + [html.Tbody(table_body_rows)],
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        size="sm",
        color="dark",
        className="mb-0",
    )

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        create_search_input(
                            input_id=tab_search_id,
                            placeholder=f"Filter {source_display_name} by term...",
                            clear_button=True,
                        ),
                        width=True,
                    ),
                ],
                className="mb-3",
            ),
            deals_data_store,
            html.Div(
                table,
                id=f"{tab_search_id}-results",
                style={"maxHeight": "800px", "overflowY": "auto"},
            ),
        ]
    )


def register_deals_callbacks(app):
    """Register search callbacks for deals tabs."""
    # Add IDs for potential multiple deal sources
    search_ids = ["v2-deals-search-lifetimo"]

    for search_id in search_ids:

        @app.callback(
            Output(f"{search_id}-results", "children"),
            [Input(search_id, "value")],
            State(f"{search_id}-data", "data"),
        )
        def update_deals_search(search_term, deals_data_json, current_search_id=search_id):
            if not deals_data_json:
                source_key = current_search_id.replace("v2-deals-search-", "")
                all_deals_data = get_all_deals_data()
                deals_data = all_deals_data.get(source_key, [])
            else:
                deals_data = json.loads(deals_data_json) if isinstance(deals_data_json, str) else deals_data_json

            if search_term:
                searchable_fields = ["title", "description", "categories"]
                filtered_deals = filter_content(search_term, deals_data, searchable_fields)
            else:
                filtered_deals = deals_data[:MAX_DEALS_PER_SOURCE]

            table_body_rows = []
            for deal in filtered_deals:
                title = deal.get("title", "No Title")
                url = deal.get("url") or deal.get("link")
                categories = deal.get("categories", [])
                categories_display = ", ".join(categories) if categories else "General"
                date_display = format_deal_date(deal)

                table_body_rows.append(
                    html.Tr(
                        [
                            html.Td(html.A(str(title), href=url, target="_blank") if url else str(title)),
                            html.Td(dbc.Badge(str(categories_display), color="info", className="me-1")),
                            html.Td(str(date_display)),
                        ]
                    )
                )

            table = dbc.Table(
                [html.Thead(html.Tr([html.Th("Deal Title"), html.Th("Categories"), html.Th("Date Added")])), html.Tbody(table_body_rows)],
                bordered=True,
                hover=True,
                responsive=True,
                striped=True,
                size="sm",
                color="dark",
            )

            return table

        @app.callback(
            Output(search_id, "value", allow_duplicate=True),
            Input(f"{search_id}-clear", "n_clicks"),
            prevent_initial_call=True,
        )
        def clear_deals_search(n_clicks):
            if n_clicks:
                return ""
            return dash.no_update


def render_deals_tab():
    """Render the Deals tab with Lifetimo sub-tab."""
    tab_definitions = [
        {"label": "Lifetimo Lifetime Deals", "keys": "lifetimo", "id": "lifetimo"},
    ]

    tabs_children = []
    for tab_def in tab_definitions:
        content = create_deals_source_tab_content(tab_def["keys"], combined_name=tab_def["label"])
        tabs_children.append(
            dbc.Tab(
                label=tab_def["label"],
                tab_id=f"deals-tab-{tab_def['id']}",
                children=content,
            )
        )

    return html.Div(
        [
            html.H3("Exclusive Lifetime Deals", className="mb-3"),
            dbc.Tabs(id="deals-source-tabs", children=tabs_children, active_tab="deals-tab-lifetimo"),
        ]
    )
