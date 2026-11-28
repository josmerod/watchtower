"""Scavenging Tab Component for Watchtower Dashboard
Improved with premium table layout, clickable links, and search functionality.

Sources are config-driven via SCAVENGING_SOURCES (mirroring the News tab
pattern): each entry declares the canonical output file written by its
goldigging ETL, plus a deprecated legacy fallback under data/scavenging/ so
historical server data keeps rendering until each ETL's next run refreshes
the canonical file. An entry that carries a ``paused`` note keeps its subtab
and shows the note instead of records (T-157).

The layout is a shell per source and each subtab is built when it is opened
(T-170). The layout used to carry the first page of every source and every
file whole in a store: 3.9 MB in one response in production, for the one
subtab in view. Now a dispatcher on the subtab bar marks the subtab opened,
the controller of that subtab reads its file and builds its page, and nothing
is sent again when it is opened a second time.
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
    pagination_controls,
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
        # Its ETL left the orchestrator on 2026-08-19, so what it collected only gets older (T-157).
        "paused": "Paused since 2026-08-19: the free-games ETL that fed this subtab no longer runs, so its last records are not shown.",
        "paths": [
            get_data_path("epic_free_games", "output", "epic_free_games_latest.json"),
            get_data_path("scavenging", "epic_free_games.json"),  # deprecated fallback
        ],
    },
]

# --- Data Loading ---


def _live_sources() -> list[dict[str, Any]]:
    """The configured sources that are not paused."""
    return [source for source in SCAVENGING_SOURCES if not source.get("paused")]


def _paused_sources() -> list[dict[str, Any]]:
    """The configured sources that are paused, each with the note its subtab shows."""
    return [source for source in SCAVENGING_SOURCES if source.get("paused")]


def _resolve_source_file(source: dict[str, Any]) -> Path | None:
    """Return the first existing path for a source (canonical first, legacy fallback second)."""
    for raw_path in source["paths"]:
        candidate = Path(raw_path)
        if candidate.is_file():
            return candidate
    return None


def discover_categories() -> dict[str, Path]:
    """Return a mapping of category key -> resolved JSON path, for the sources that are not paused."""
    try:
        categories: dict[str, Path] = {}
        for source in _live_sources():
            resolved = _resolve_source_file(source)
            if resolved is not None:
                categories[source["key"]] = resolved

        logger.info(f"Discovered {len(categories)} scavenging categories: {list(categories.keys())}")
        return categories
    except Exception as e:
        logger.error(f"Error discovering categories: {e}")
        return {}


def get_scavenging_data(category_key: str) -> list[dict[str, Any]]:
    """Load data for a specific category, normalized for display; a paused source has none."""
    source = next((s for s in _live_sources() if s["key"] == category_key), None)
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

MAX_ITEMS_PER_TAB = 100  # rows per page: the rest is reached with Prev / Next
SEARCHABLE_FIELDS = ["title", "summary", "source", "seller", "deal_type", "category"]
SCAVENGING_SEARCH_DEBOUNCE_MS = 400  # the search runs on the server now: wait for a pause in typing
TABS_ID = "scavenging-main-tabs"
LOADING = "Loading…"
RESULTS_STYLE = {"maxHeight": "800px", "overflowY": "auto"}


def _search_id(key: str) -> str:
    return f"scavenging-search-{key}"


def _tab_id(key: str) -> str:
    return f"tab-scavenging-{key}"


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
        {"header": "Details", "cell": lambda item: _details_cell(item, search_term)},
        {"header": "Price/Type", "cell": _scavenging_price_badges},
        # The date of the entry: when an Audible release or a bundle launched, not the day it was read.
        {"header": "Date", "cell": lambda item: str(format_article_date_shared(item)), "td_kwargs": {"className": "text-nowrap font-monospace small"}},
    ]
    return render_items_table(items, columns, empty_message="No entries found matching your criteria.", wrap_scroll=False)


def _details_cell(item: dict[str, Any], search_term: str) -> html.Div:
    """The summary, and the shop links a record carries.

    Humble books name one per bundle they are in; the title links to the
    book's page on the index site, which is what keeps one row per book.
    """
    summary = item.get("summary") if isinstance(item.get("summary"), str) else str(item.get("summary", ""))
    links = item.get("humble_urls") or []
    return html.Div(
        [
            text_cell(summary, search_term, className="small", style={"maxWidth": "400px", "whiteSpace": "normal"}),
            *[html.A("Humble ↗" if len(links) == 1 else f"Humble {n} ↗", href=url, target="_blank", rel="noopener noreferrer", className="small ms-2") for n, url in enumerate(links, 1)],
        ]
    )


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


def _total_pages(total: int) -> int:
    return max(1, -(-total // MAX_ITEMS_PER_TAB))


def _pager(search_id: str, page: int, total: int) -> Any:
    """Prev / Next bar of one subtab, hidden while everything fits on one page.

    Hidden, not absent: the controller of the subtab listens to both buttons, and Dash never runs a callback whose
    Input is not in the page. With an empty pager, a source of 100 records or fewer had no search at all.
    """
    total_pages = _total_pages(total)
    showing = min(MAX_ITEMS_PER_TAB, total - (page - 1) * MAX_ITEMS_PER_TAB)
    bar = pagination_controls(search_id, page=page, total_pages=total_pages, showing=showing, total=total, id_prefix=search_id)
    return html.Div(bar, hidden=True) if total_pages == 1 else bar


def _target_page(triggered_id: Any, search_id: str, current_page: int | None, total_pages: int) -> int:
    """The page to show after a trigger: a new search starts over, Prev and Next move one page."""
    if triggered_id in (search_id, f"{search_id}-clear"):
        page = 1
    else:
        page = int(current_page or 1)
        if triggered_id == f"{search_id}-prev":
            page -= 1
        elif triggered_id == f"{search_id}-next":
            page += 1
    return min(max(page, 1), total_pages)


def _shell(source: dict[str, Any]) -> html.Div:
    """What a subtab holds until it is opened: its search box, its pager and an empty results container.

    Every id the controller takes is here from the start, and the pager keeps its two buttons even where they will
    not be shown: Dash never runs a callback whose Input is not in the page. The activate store is the exception:
    it lives in ``_activate_stores``, with those of the sources that have no subtab yet.
    """
    search_id = _search_id(source["key"])
    return html.Div(
        [
            dbc.Row(
                dbc.Col(
                    create_search_input(input_id=search_id, placeholder=f"Search in {source['label']}...", clear_button=True, debounce=SCAVENGING_SEARCH_DEBOUNCE_MS),
                    width=True,
                ),
                className="mb-3 mt-3",
            ),
            html.Div(_pager(search_id, 1, 0), id=f"{search_id}-pager"),
            html.Div(LOADING, id=f"{search_id}-results", style=RESULTS_STYLE),
            dcc.Store(id=f"{search_id}-page", data=None),  # empty until the page is first built
        ],
        className="p-3",
    )


def _activate_stores() -> html.Div:
    """The store the dispatcher marks, for every live source whether or not its subtab is on the page.

    Dash refuses to run a callback while any of its Outputs is missing from the page. With only the stores of the
    subtabs rendered, the dispatcher never ran where a source had no file yet, and no subtab was built at all.
    """
    return html.Div([dcc.Store(id=f"{_search_id(source['key'])}-activate", data=0) for source in _live_sources()], hidden=True)


def render_scavenging_tab() -> html.Div:
    """Render the main Scavenging tab layout: one shell per source, in key order, the first one open."""
    live = {source["key"]: source for source in _live_sources() if _resolve_source_file(source) is not None}
    if not live:
        return dbc.Alert("No scavenging data found. Please run the ETL processes.", color="warning", className="m-4")

    entries = {**live, **{source["key"]: source for source in _paused_sources()}}
    subtabs = []
    for key in sorted(entries):
        source = entries[key]
        note = source.get("paused")
        content = dbc.Alert(note, color="secondary", className="m-3") if note else _shell(source)
        subtabs.append(dbc.Tab(label=source["label"], tab_id=_tab_id(key), children=content))

    return html.Div(
        [
            html.H3("⛏️ Project Scavenging", className="mb-4"),
            html.P("Automated monitoring of free resources, audiobooks, and deal alerts.", className="text-muted"),
            dbc.Tabs(id=TABS_ID, children=subtabs, active_tab=subtabs[0].tab_id),
            _activate_stores(),
        ],
        className="p-4",
    )


IDLE = (dash.no_update, dash.no_update, dash.no_update)  # what a controller answers when it has nothing to build


def _scavenging_activation(active_tab: Any, marked: tuple[Any, ...] = ()) -> tuple[Any, ...]:
    """What the dispatcher writes to the activate stores: 1 for the subtab just opened, no_update for the others.

    ``marked`` holds what those stores hold already, in the order of the live sources. A subtab opened again is
    left alone, so its controller is not woken for a page it already built.
    """
    activation = []
    for position, source in enumerate(_live_sources()):
        opening = _tab_id(source["key"]) == active_tab
        already = position < len(marked) and bool(marked[position])
        activation.append(1 if opening and not already else dash.no_update)
    return tuple(activation)


def _scavenging_trigger(triggered_id: Any, activated: Any, current_page: int | None, search_id: str) -> Any:
    """The id ``_scavenging_page`` takes as its trigger, or None when the controller has nothing to build.

    A subtab is built when the dispatcher first marks it and its page store is still empty. Afterwards only its
    own controls count, and being marked again changes nothing.
    """
    if not activated:
        return None
    if triggered_id == f"{search_id}-activate":
        return search_id if not current_page else None  # the first build starts at page 1
    if current_page and triggered_id in (search_id, f"{search_id}-clear", f"{search_id}-prev", f"{search_id}-next"):
        return triggered_id
    return None


def register_scavenging_callbacks(app) -> None:
    """Register the subtab dispatcher, one controller per live source, and the clear buttons.

    One controller per live source, registered whether or not its file exists yet: a subtab whose data shows up
    after startup would otherwise have no search. A paused source gets none: its subtab only shows its note.
    """
    live = _live_sources()
    if not live:
        return
    stores = [f"{_search_id(source['key'])}-activate" for source in live]

    @app.callback(
        [Output(store, "data") for store in stores],
        Input(TABS_ID, "active_tab"),
        [State(store, "data") for store in stores],
        # It also runs when the tab first renders: the subtab in view then is the one to build.
        prevent_initial_call=False,
    )
    def open_subtab(active_tab, *marked):
        """Mark the subtab the bar now shows, unless its store is marked already."""
        return _scavenging_activation(active_tab, marked)

    for source in live:
        key = source["key"]
        search_id = _search_id(key)

        @app.callback(
            Output(f"{search_id}-results", "children"),
            Output(f"{search_id}-pager", "children"),
            Output(f"{search_id}-page", "data"),
            Input(search_id, "value"),
            Input(f"{search_id}-prev", "n_clicks"),
            Input(f"{search_id}-next", "n_clicks"),
            Input(f"{search_id}-activate", "data"),
            State(f"{search_id}-page", "data"),
            # Idle until the dispatcher marks the subtab; the clear button
            # empties the search box, and that change arrives as a new term.
            prevent_initial_call=True,
        )
        def update_scavenging_page(search_term, _prev, _next, activated, current_page, key=key, search_id=search_id):
            """Build a page of the subtab when its first opening or one of its controls asks for it."""
            try:
                trigger = _scavenging_trigger(dash.ctx.triggered_id, activated, current_page, search_id)
                if trigger is None:
                    return IDLE
                records = get_scavenging_data(key)
                records.sort(key=get_sortable_date, reverse=True)
                return _scavenging_page(records, search_term, trigger, current_page, search_id)
            except Exception as e:  # broad by design: the page must answer even when a record cannot be rendered
                logger.error(f"Error updating scavenging results for {search_id}: {e}")
                return dbc.Alert(f"Error updating results: {e}", color="danger"), dash.no_update, dash.no_update

        @app.callback(
            Output(search_id, "value", allow_duplicate=True),
            Input(f"{search_id}-clear", "n_clicks"),
            prevent_initial_call=True,
        )
        def clear_scavenging_search(n_clicks):
            if n_clicks:
                return ""
            return dash.no_update


def _scavenging_page(records: list[dict[str, Any]] | None, search_term: str | None, triggered_id: Any, current_page: int | None, search_id: str) -> tuple[Any, Any, Any]:
    """What one subtab shows after a trigger: the page of rows, its pager and the page number."""
    if not records:
        return dbc.Alert("No data loaded.", color="info"), _pager(search_id, 1, 0), 1

    term = (search_term or "").strip()
    shown = filter_content(term, records, SEARCHABLE_FIELDS) if term else records
    total_pages = _total_pages(len(shown))
    page = _target_page(triggered_id, search_id, current_page, total_pages)
    page_items = shown[(page - 1) * MAX_ITEMS_PER_TAB : page * MAX_ITEMS_PER_TAB]

    body = create_scavenging_table(page_items, search_term=term)
    if term:
        body = html.Div([dbc.Alert(f"⛏️ Found {len(shown)} items matching '{term}'", color="success", className="mb-3"), body])
    return body, _pager(search_id, page, len(shown)), page
