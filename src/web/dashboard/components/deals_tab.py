import logging
import time
from typing import Any

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

from src.services.data_loader import (
    DEALS_SOURCES_CONFIG,
    get_sortable_date,
    load_data_from_file,
)
from src.services.data_loader import (
    format_article_date as format_article_date_shared,
)
from src.web.dashboard.components.shared.table import (
    badges_cell,
    render_items_table,
    title_cell,
)
from src.web.dashboard.search_utils import (
    create_search_input,
    filter_content,
)

# Configure logging
logger = logging.getLogger(__name__)

# --- Data Loading ---

MAX_DEALS_PER_SOURCE = 50

# Single source of truth for subtabs — search ids are derived from it so a
# new source can never end up with a dead search box.
DEALS_TAB_DEFINITIONS = [
    {"label": "Lifetimo Lifetime Deals", "keys": "lifetimo", "id": "lifetimo"},
]


def get_all_deals_data():
    """Load fresh deals data from all configured sources (60s TTL cache)."""
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


def _deals_search_id(tab_def: dict) -> str:
    keys = tab_def["keys"]
    if isinstance(keys, str):
        return f"v2-deals-search-{keys}"
    return f"v2-deals-search-{'-'.join(keys)}"


def create_deals_table(deals: list[dict[str, Any]], search_term: str = "") -> Any:
    """Render the deals table via the shared builder (real search highlights)."""
    columns = [
        {
            "header": "Deal Title",
            "cell": lambda deal: title_cell(
                deal,
                search_term,
                title_fields=("title",),
                url_fields=("url", "link"),
                subtitle=deal.get("description") or None,
            ),
        },
        {"header": "Categories", "cell": lambda deal: badges_cell(deal.get("categories", []), fallback="General", color="info")},
        {"header": "Date Added", "cell": lambda deal: str(format_deal_date(deal))},
    ]
    return render_items_table(deals, columns, empty_message="No deals found matching your criteria.", wrap_scroll=False)


def create_deals_source_tab_content(source_keys, combined_name=None):
    """Creates the content for a deals tab as a table with search functionality."""
    if isinstance(source_keys, str):
        source_keys = [source_keys]
    # Assign display name for BOTH single and combined sources (the list
    # branch used to raise NameError on source_display_name).
    source_display_name = combined_name or DEALS_SOURCES_CONFIG[source_keys[0]]["name"]
    tab_search_id = f"v2-deals-search-{'-'.join(source_keys)}"

    all_deals_data = get_all_deals_data()
    all_deals_for_tab = []

    for key in source_keys:
        deals_from_source = all_deals_data.get(key, [])
        for deal in deals_from_source:
            deal["source_display_name"] = deal.get("source", DEALS_SOURCES_CONFIG[key]["name"])
        all_deals_for_tab.extend(deals_from_source)

    all_deals_for_tab.sort(key=get_sortable_date, reverse=True)

    # Full dataset in the Store (search reaches beyond the display cap);
    # the cap is applied at render time only.
    deals_data_store = dcc.Store(
        data=all_deals_for_tab,
        id=f"{tab_search_id}-data",
    )

    if not all_deals_for_tab:
        return dbc.Alert(f"No deals available for {source_display_name}.", color="info")

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
                create_deals_table(all_deals_for_tab[:MAX_DEALS_PER_SOURCE]),
                id=f"{tab_search_id}-results",
                style={"maxHeight": "800px", "overflowY": "auto"},
            ),
        ]
    )


def register_deals_callbacks(app):
    """Register search callbacks for deals tabs."""
    search_ids = [_deals_search_id(tab_def) for tab_def in DEALS_TAB_DEFINITIONS]

    for search_id in search_ids:

        @app.callback(
            Output(f"{search_id}-results", "children"),
            [Input(search_id, "value")],
            State(f"{search_id}-data", "data"),
        )
        def update_deals_search(search_term, deals_data, current_search_id=search_id):
            try:
                if not deals_data:
                    source_key = current_search_id.replace("v2-deals-search-", "")
                    all_deals_data = get_all_deals_data()
                    deals_data = all_deals_data.get(source_key, [])

                if search_term:
                    searchable_fields = ["title", "description", "categories"]
                    filtered_deals = filter_content(search_term, deals_data, searchable_fields)
                    return html.Div(
                        [
                            dbc.Alert(f"🏷️ Found {len(filtered_deals)} deals matching '{search_term}'", color="success", className="mb-3"),
                            create_deals_table(filtered_deals, search_term=search_term),
                        ]
                    )

                return create_deals_table(deals_data[:MAX_DEALS_PER_SOURCE])
            except Exception as e:
                logger.error(f"Error in deals search callback for {current_search_id}: {e}")
                return dbc.Alert(f"Error searching deals: {e}", color="danger")

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
    tabs_children = []
    for tab_def in DEALS_TAB_DEFINITIONS:
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
            dbc.Tabs(id="deals-source-tabs", children=tabs_children, active_tab=f"deals-tab-{DEALS_TAB_DEFINITIONS[0]['id']}"),
        ]
    )
