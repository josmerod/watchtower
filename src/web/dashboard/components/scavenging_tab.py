"""Scavenging Tab Component for Watchtower Dashboard
Improved with premium table layout, clickable links, and search functionality.

Sources are config-driven via SCAVENGING_SOURCES (mirroring the News tab
pattern): each entry declares the canonical output file written by its
goldigging ETL, plus a deprecated legacy fallback under data/scavenging/ so
historical server data keeps rendering until each ETL's next run refreshes
the canonical file.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

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

# --- Source configuration ---


def _iso(value: Any) -> str:
    """Coerce a datetime-or-string field into an ISO string for display/sorting."""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value or "")


def _adapt_travel_deal(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize a TravelDeal dump (canonical viajeros_piratas output) for display.

    Legacy scavenging-shaped records (the deprecated fallback file) pass
    through unchanged so both paths render identically.
    """
    if "deal_id" not in item and "published_at" not in item:
        return item
    price = item.get("price")
    price_label = f"{price}€" if isinstance(price, (int, float)) and price > 0 else item.get("raw_price", "")
    return {
        "title": item.get("title", ""),
        "link": str(item.get("url") or ""),
        "published": _iso(item.get("published_at")),
        "summary": item.get("description") or "",
        "category": "viajeros_piratas",
        "source": item.get("source", "viajeros_piratas"),
        "price": price_label,
        "deal_type": item.get("category", "other"),
        "currency": item.get("currency", "EUR"),
    }


def _adapt_gumroad_product(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize a GumroadProduct dump (canonical gumroad_scraper output) for display.

    Legacy scavenging-shaped records (the deprecated fallback file) pass
    through unchanged so both paths render identically.
    """
    if "product_id" not in item and "name" not in item:
        return item
    return {
        "title": item.get("name", ""),
        "link": str(item.get("url") or ""),
        "published": _iso(item.get("fetched_at")),
        "summary": item.get("description") or "",
        "category": "gumroad_free",
        "source": "gumroad_scraper",
        "price": item.get("price", ""),
        "seller": item.get("seller"),
    }


# Canonical path first; the data/scavenging/ entry is the deprecated legacy
# fallback (T-067, 2026-08) kept only so historical server files keep
# rendering until each ETL's next run writes its canonical output.
SCAVENGING_SOURCES: list[dict[str, Any]] = [
    {
        "key": "anime",
        "label": "Anime",
        "category": "anime",
        "paths": [
            get_data_path("goldigging_scavenging", "output", "anime_rss_entries.json"),
            get_data_path("scavenging", "anime_rss_entries.json"),  # deprecated fallback
        ],
    },
    {
        "key": "audiobooks",
        "label": "Audiobooks",
        "category": "audiobooks",
        "paths": [
            get_data_path("goldigging_scavenging", "output", "audiobooks_rss_entries.json"),
            get_data_path("scavenging", "audiobooks_rss_entries.json"),  # deprecated fallback
        ],
    },
    {
        "key": "courses",
        "label": "Courses",
        "category": "courses",
        "paths": [
            get_data_path("goldigging_scavenging", "output", "courses_rss_entries.json"),
            get_data_path("scavenging", "courses_rss_entries.json"),  # deprecated fallback
        ],
    },
    {
        "key": "audible",
        "label": "Audible",
        "category": "audible",
        "paths": [
            get_data_path("audible_releases", "output", "audible_releases_latest.json"),
            get_data_path("scavenging", "audible_rss_entries.json"),  # deprecated fallback
        ],
    },
    {
        "key": "gumroad_free",
        "label": "Gumroad free",
        "category": "gumroad_free",
        "adapter": _adapt_gumroad_product,
        "paths": [
            get_data_path("gumroad_scraper", "output", "gumroad_free_products.json"),
            get_data_path("scavenging", "gumroad_free_products.json"),  # deprecated fallback
        ],
    },
    {
        "key": "viajeros_piratas",
        "label": "Viajeros piratas",
        "category": "viajeros_piratas",
        "adapter": _adapt_travel_deal,
        "paths": [
            get_data_path("viajeros_piratas", "output", "viajeros_piratas_deals.json"),
            get_data_path("scavenging", "viajeros_piratas_deals.json"),  # deprecated fallback
        ],
    },
    {
        "key": "humble_books",
        "label": "Humble books",
        "category": "humble_books",
        "paths": [
            get_data_path("humble_books", "output", "humble_books_latest.json"),
            get_data_path("scavenging", "humble_books.json"),  # deprecated fallback
        ],
    },
    {
        "key": "epic_free",
        "label": "Epic free",
        "category": "epic_free",
        "paths": [
            get_data_path("epic_free_games", "output", "epic_free_games_latest.json"),
            get_data_path("scavenging", "epic_free_games.json"),  # deprecated fallback
        ],
    },
]

# --- Data Loading ---


def _resolve_source_file(source: dict[str, Any]) -> Path | None:
    """Return the first existing path for a source (canonical first, legacy fallback second)."""
    for raw_path in source["paths"]:
        candidate = Path(raw_path)
        if candidate.is_file():
            return candidate
    return None


def discover_categories() -> dict[str, Path]:
    """Return a mapping of category key -> resolved JSON path."""
    try:
        categories: dict[str, Path] = {}
        for source in SCAVENGING_SOURCES:
            resolved = _resolve_source_file(source)
            if resolved is not None:
                categories[source["key"]] = resolved

        logger.info(f"Discovered {len(categories)} scavenging categories: {list(categories.keys())}")
        return categories
    except Exception as e:
        logger.error(f"Error discovering categories: {e}")
        return {}


def get_scavenging_data(category_key: str) -> list[dict[str, Any]]:
    """Load data for a specific category, normalized for display."""
    source = next((s for s in SCAVENGING_SOURCES if s["key"] == category_key), None)
    if source is None:
        return []

    resolved = _resolve_source_file(source)
    if resolved is None:
        return []

    records = load_data_from_file(str(resolved))
    adapter = source.get("adapter")
    if adapter is not None:
        records = [adapter(record) for record in records]

    # Config category as a display fallback for sparse records (badges/search).
    for record in records:
        if not record.get("category"):
            record["category"] = source["category"]
    return records


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

    labels = {source["key"]: source["label"] for source in SCAVENGING_SOURCES}
    category_tabs = []
    for category in sorted(categories_map.keys()):
        source_display_name = labels.get(category, category.replace("_", " ").capitalize())
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
