import logging
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, dcc, html

from src.services.data_loader import (
    CLOUD_UPDATES_SOURCES_CONFIG,
    NEWS_SOURCES_CONFIG,
    VALENCIA_LOCAL_SOURCES_CONFIG,
    get_sortable_date,
    load_data_from_file,
)
from src.services.data_loader import (
    format_article_date as format_article_date_shared,
)
from src.web.dashboard.components import saved_items
from src.web.dashboard.components.duplicate_filter import create_duplicate_toggle
from src.web.dashboard.components.shared.table import paginate, render_items_table, title_cell
from src.web.dashboard.deduplication_utils import (
    annotate_duplicate_groups,
    filter_duplicates,
    format_duplicate_summary,
    get_duplicate_summary,
)
from src.web.dashboard.trend_utils import get_trending_items_map, match_item_trend, render_trend_badge

# Merge the extra source configs so the news tab can render them as subtabs
_ALL_NEWS_SOURCES = {
    **NEWS_SOURCES_CONFIG,
    **CLOUD_UPDATES_SOURCES_CONFIG,
    **VALENCIA_LOCAL_SOURCES_CONFIG,
}
from src.web.dashboard.search_utils import (
    create_search_input,
    filter_content,
    get_common_searchable_fields,
    highlight_segments,
)

# Configure logging
logger = logging.getLogger(__name__)

# --- Data Loading ---

# NEWS TAB - Actual news sites and aggregators
# NEWS_SOURCES_CONFIG imported from data_loader

# load_news_from_file removed (using shared load_data_from_file)


# Load news data dynamically instead of at import time
def get_all_news_data():
    """Load fresh news data from all configured sources."""
    # Simple TTL cache to avoid re-reading dozens of files on each tab switch
    # Cache in module state for ~60 seconds
    import time

    global _NEWS_CACHE
    now = time.time()
    try:
        if _NEWS_CACHE and now - _NEWS_CACHE.get("ts", 0) < 60:
            return _NEWS_CACHE["data"]
    except NameError:
        pass

    data = {source_key: load_data_from_file(config["path"]) for source_key, config in _ALL_NEWS_SOURCES.items()}
    _NEWS_CACHE = {"ts": now, "data": data}
    return data


# --- Helper function to parse dates ---
# parse_date logic removed (using shared parse_date)


# --- Layout Generation ---

MAX_ARTICLES_PER_SOURCE = 50  # Limit number of articles displayed per source initially

# One request per pause in typing, not per keystroke: every answer is the
# subtab's table rendered again (same value as the Knowledge Garden search).
NEWS_SEARCH_DEBOUNCE_MS = 400

# A source whose newest item is this old has stopped publishing, whatever the age
# of its file: every News ETL rewrites its file each cycle (T-176). The subtab says so.
STALE_SOURCE_DAYS = 7
_NO_DATE = datetime.min.replace(tzinfo=timezone.utc)  # what get_sortable_date returns for an undated item

# Top Tech subtab (spec 01 M4/M5): items-per-page selector (no more blind
# 50-cap / 800px scroll) + visible cross-source dedup. IDs are namespaced
# under TOP_TECH_COMPONENT_ID to avoid colliding with the per-source subtabs.
TOP_TECH_PER_PAGE_OPTIONS = (25, 50, 100, 250)
TOP_TECH_DEFAULT_PER_PAGE = 50
TOP_TECH_COMPONENT_ID = "news-toptech"

# ⭐ Saved-items toggle (T-053): only the "🔎 Global" search results get a star
# (NOT the per-source subtabs, NOT Top Tech). Pattern id type per tab, shared
# persistence with Knowledge Garden via data/garden/saved_items.json.
NEWS_SAVE_BTN_TYPE = "news-save-btn"


# Single source of truth for the subtab list. render_news_tab() builds the
# dbc.Tabs from it and register_news_search_callbacks() derives the search
# input IDs from it, so a new tab can never end up with a dead search box.
class _NewsTabDefRequired(TypedDict):
    """Keys every NEWS_TAB_DEFINITIONS entry must carry."""

    label: str
    keys: str | list[str]
    id: str


class _NewsTabDef(_NewsTabDefRequired, total=False):
    """Optional keys (only some subtabs paginate)."""

    paginated: bool


NEWS_TAB_DEFINITIONS: list[_NewsTabDef] = [
    {
        "label": "Top Tech",
        "keys": ["techcrunch", "venturebeat", "arstechnica", "kagi_ai"],
        "id": "top_tech",
        # M4 (paginación) + M5 (dedup visible) apply to this aggregated subtab only
        "paginated": True,
    },
    # Google AI Blog, KDnuggets y Cloud Updates viven SOLO en Tech Radar (spec 13 M3):
    # su contenido sigue encontrable vía "🔎 Global" y el radar los muestra con más contexto.
    # Lobsters se mudó a Knowledge Garden (T-130, 2026-11-26).
    {
        "label": "FutureTools & Ben's Bites",
        "keys": ["futuretools", "bensbites"],
        "id": "ft-bb",
    },
    {"label": "Hacker News", "keys": "hackernews", "id": "hn"},
    {"label": "tldr.tech", "keys": "tldr", "id": "tldr"},
    {"label": "Medium GenAI", "keys": "medium_genai", "id": "med_genai"},
    {"label": "Meneame General", "keys": "meneame_general", "id": "men_gen"},
    {"label": "Meneame Tech", "keys": "meneame_tecnologia", "id": "men_tec"},
    {"label": "Indie Hackers", "keys": "indiehackers", "id": "ih"},
    # Kagi RSS feeds as individual tabs (usa and world were dropped on 2026-11-26, T-126)
    {"label": "Kagi Business", "keys": "kagi_business", "id": "kagi_business"},
    {"label": "Kagi Science", "keys": "kagi_science", "id": "kagi_science"},
    {"label": "Kagi Gaming", "keys": "kagi_gaming", "id": "kagi_gaming"},
    {"label": "Kagi Europe", "keys": "kagi_europe", "id": "kagi_europe"},
    {"label": "Kagi Spain", "keys": "kagi_spain", "id": "kagi_spain"},
    {"label": "Microsiervos", "keys": "microsiervos", "id": "microsiervos"},
    {"label": "🇪🇸 Spanish Tech", "keys": "spanish_tech", "id": "spanish_tech"},
    {"label": "📍 Valencia Local", "keys": "valencia_local", "id": "valencia_local"},
]


def _search_id_for_tab(tab_def: _NewsTabDef) -> str:
    """Derive the search input ID for a tab definition.

    Mirrors the logic in create_news_source_tab_content so layout and
    callbacks always agree on the ID.
    """
    keys = tab_def["keys"]
    if isinstance(keys, str):
        return f"news-search-{keys}"
    return f"news-search-{'-'.join(keys)}"


# The Top Tech controller callback is registered separately from the generic
# per-subtab loop, so its search id must be resolvable from here.
_TOP_TECH_DEF = next(tab_def for tab_def in NEWS_TAB_DEFINITIONS if tab_def["id"] == "top_tech")
TOP_TECH_SEARCH_ID = _search_id_for_tab(_TOP_TECH_DEF)


def _aggregate_source_articles(source_keys: list[str], all_news_data: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Aggregate sources into one date-descending list of copies.

    Copies (never the cached dicts) get ``source_display_name`` injected, per
    spec 01 N7 — mutating the shared cache leaks display fields across tabs.
    """
    articles: list[dict[str, Any]] = []
    for key in source_keys:
        for article in all_news_data.get(key, []):
            item = dict(article)
            item["source_display_name"] = article.get("source", _ALL_NEWS_SOURCES.get(key, {}).get("name", key))
            articles.append(item)
    articles.sort(key=get_sortable_date, reverse=True)
    return articles


def _build_news_table(articles: list[dict[str, Any]], search_term: str | None = None) -> dbc.Table:
    """Build the shared news table (Title/Source/Date, trend badge, read-state hash)."""
    trending_map = get_trending_items_map()

    table_body_rows = []
    for article in articles:
        trend_record = match_item_trend(article, trending_map)
        trend_badge = render_trend_badge(trend_record)

        title = article.get("title") or article.get("name") or article.get("full_name") or "No Title"
        url = article.get("url") or article.get("link") or article.get("html_url") or article.get("website")
        source_for_display = article.get("source_display_name", "Unknown")
        date_display = format_article_date(article)
        # Dash children legitimately accept str | list[Component]; keep the dynamic union explicit.
        title_children: Any = highlight_segments(title, search_term) if search_term else title

        table_body_rows.append(
            html.Tr(
                [
                    html.Td(
                        [
                            (html.A(title_children, href=url, target="_blank") if url else title_children),
                            trend_badge,
                        ]
                    ),
                    html.Td(source_for_display),
                    html.Td(date_display),
                ],
                className="trending-item" if trend_record is not None else "",
                # data-* wildcard props are valid at runtime but absent from Dash's generated stubs
                **{"data-item-hash": _news_item_hash(url or "", title or "")},  # type: ignore[arg-type]
            )
        )

    return dbc.Table(
        [
            html.Thead(html.Tr([html.Th("Title"), html.Th("Source"), html.Th("Date")])),
            html.Tbody(table_body_rows),
        ],
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        size="sm",
        color="dark",
        className="table-responsive mb-0",
    )


def _render_top_tech_view(
    articles: list[dict[str, Any]],
    search_term: str | None = None,
    show_duplicates: bool = False,
    per_page: int = TOP_TECH_DEFAULT_PER_PAGE,
    page: int = 1,
) -> tuple[list[Any], int]:
    """Render the Top Tech results: dedup summary + one page + pager (spec 01 M4/M5).

    Single renderer shared by the static layout and the controller callback so
    both views are identical (spec 01 N6): annotate cross-source duplicate
    groups on copies, hide duplicates unless toggled, then slice one page.

    Returns:
        Tuple of (children for the results container, clamped current page).
    """
    annotated = annotate_duplicate_groups(articles)
    summary = get_duplicate_summary(annotated)
    visible = filter_duplicates(annotated, show_duplicates=show_duplicates)

    # Shared pagination helper: slice one page and clamp it into range
    page_items, total_pages, page = paginate(visible, page, per_page)

    children: list[Any] = []
    if not show_duplicates and summary["duplicate_items"] > 0:
        children.append(
            html.Span(
                format_duplicate_summary(summary),
                id=f"{TOP_TECH_COMPONENT_ID}-duplicate-summary",
                className="text-muted small d-block mb-2",
            )
        )
    children.append(_build_news_table(page_items, search_term))
    if total_pages > 1:
        children.append(
            html.Div(
                [
                    dbc.Button(
                        "« Anterior",
                        id={"type": f"{TOP_TECH_COMPONENT_ID}-page-btn", "dir": "prev"},
                        color="secondary",
                        outline=True,
                        size="sm",
                        disabled=(page <= 1),
                        className="me-2",
                    ),
                    html.Span(
                        f"Página {page} de {total_pages} · {len(visible)} items",
                        className="align-self-center text-muted small me-2",
                    ),
                    dbc.Button(
                        "Siguiente »",
                        id={"type": f"{TOP_TECH_COMPONENT_ID}-page-btn", "dir": "next"},
                        color="secondary",
                        outline=True,
                        size="sm",
                        disabled=(page >= total_pages),
                    ),
                ],
                className="d-flex justify-content-center flex-wrap mt-3",
            )
        )
    return children, page


# format_article_date removed (using shared logic)
def format_article_date(article):
    """Wrapper for shared formatting."""
    return format_article_date_shared(article)


# Removed create_article_card function as it's no longer needed for table view


def _stale_source_notes(source_keys: list[str]) -> list[str]:
    """One line for each source of a subtab whose newest item is ``STALE_SOURCE_DAYS`` old or more."""
    notes = []
    now = datetime.now(timezone.utc)
    for key in source_keys:
        dates = [date for date in map(get_sortable_date, get_all_news_data().get(key, [])) if date != _NO_DATE]
        if dates and now - max(dates) >= timedelta(days=STALE_SOURCE_DAYS):
            notes.append(f"⚠️ {_ALL_NEWS_SOURCES[key]['name']} lleva sin publicar nada nuevo desde el {max(dates):%d/%m/%Y}.")
    return notes


def _render_news_results(source_keys: list[str], search_term: str | None = None):
    """The content of a subtab's results container: the table of its articles, filtered by the search term.

    The layout and the subtab's search controller both call this, so the table the page is born
    with is the table the controller would build for an empty search. A source that stopped
    publishing is named above the table.

    Args:
        source_keys: The subtab's sources.
        search_term: When given, only the articles that match are listed, newest first, under an
            alert with the count; otherwise the newest ``MAX_ARTICLES_PER_SOURCE``.

    Returns:
        A warning alert when the sources hold no article, else the scroll container with the table.
    """
    articles: list[dict[str, Any]] = []
    for key in source_keys:
        for article in get_all_news_data().get(key, []):
            article["source_display_name"] = _ALL_NEWS_SOURCES[key]["name"]
            articles.append(article)
    if not articles:
        return dbc.Alert("No data available (fetch returned empty)", color="warning")
    articles.sort(key=get_sortable_date, reverse=True)

    shown = filter_content(search_term, articles, get_common_searchable_fields("news")) if search_term else articles[:MAX_ARTICLES_PER_SOURCE]

    # Trend data renders the badges
    trending_map = get_trending_items_map()

    table_body_rows = []
    for article in shown:
        # Match by id, url, source or trending term in the title
        trend_record = match_item_trend(article, trending_map)

        # Title fallbacks: common across news sources
        title = article.get("title") or article.get("name") or article.get("full_name") or "No Title"
        # URL fallbacks
        url = article.get("url") or article.get("link") or article.get("html_url") or article.get("website")
        # Real highlight components when a search term is active
        title_children = highlight_segments(title, search_term) if search_term else title
        title_cell: list[Any] = [html.A(title_children, href=url, target="_blank")] if url else title_children if isinstance(title_children, list) else [title_children]
        title_cell.append(render_trend_badge(trend_record))
        # Read/unread tracking key (see assets/js/read_state.js)
        row_props: dict[str, Any] = {"data-item-hash": _news_item_hash(url or "", title or "")}

        table_body_rows.append(
            html.Tr(
                [html.Td(title_cell), html.Td(article.get("source_display_name", "Unknown")), html.Td(format_article_date(article))], className="trending-item" if trend_record is not None else "", **row_props
            )
        )

    table = dbc.Table(
        [
            html.Thead(html.Tr([html.Th("Title"), html.Th("Source"), html.Th("Date")])),
            html.Tbody(table_body_rows),
        ],
        bordered=True,
        hover=True,
        responsive=True,  # Makes table scroll horizontally on small screens
        striped=True,
        size="sm",
        color="dark",
        className="table-responsive mb-0",  # Remove default bottom margin if wrapped in Div with padding
    )

    # The count alert only shows while a search term is active
    alert = dbc.Alert(f"📰 Found {len(shown)} articles matching '{search_term}'", color="success", className="mb-3") if search_term else None
    notices = [dbc.Alert(note, color="warning", className="mb-3 py-2") for note in _stale_source_notes(source_keys)]
    return html.Div(
        [*notices, *([alert] if alert else []), table],
        style={
            "maxHeight": "800px",
            "overflowY": "auto",
            "paddingRight": "15px",
        },
    )


def create_news_source_tab_content(source_keys, combined_name=None, with_pagination=False):
    """Creates the content for a news tab: its search row and the table of its articles, potentially combining multiple sources.

    Args:
        source_keys: Single source key or list of keys (combined tabs).
        combined_name: Display name for combined tabs.
        with_pagination: Render the M4/M5 controls (items-per-page selector +
            "mostrar duplicados" toggle) and a paginated, deduplicated results
            container instead of the capped, 800px-scroll table. Used by the
            aggregated "Top Tech" subtab.
    """
    if isinstance(source_keys, str):  # Single source key
        source_keys = [source_keys]
        source_display_name = _ALL_NEWS_SOURCES[source_keys[0]]["name"]
    else:  # List of source keys (for combined tabs)
        source_display_name = combined_name or "Combined News"
    tab_search_id = f"news-search-{'-'.join(source_keys)}"

    # Search + CSV export row (shared by every subtab layout)
    search_row = dbc.Row(
        [
            dbc.Col(
                # Search input
                create_search_input(
                    input_id=tab_search_id,
                    placeholder=f"Filter {source_display_name} by term...",
                    clear_button=True,
                    debounce=NEWS_SEARCH_DEBOUNCE_MS,
                ),
                width=True,
            ),
            dbc.Col(
                dbc.Button(
                    "⬇ CSV",
                    id={"type": "news-export", "keys": "-".join(source_keys)},
                    color="secondary",
                    size="sm",
                    title="Exportar el dataset de este subtab a CSV",
                ),
                width="auto",
            ),
            # Trend filter button removed
        ],
        className="mb-3 align-items-center",
    )

    if with_pagination:
        all_articles_for_tab = []
        for key in source_keys:
            # Add source name to each article for display in the table
            for article in get_all_news_data().get(key, []):
                # Use 'source_display' to ensure we have a consistent field for the table
                article["source_display_name"] = article.get("source", _ALL_NEWS_SOURCES[key]["name"])
                all_articles_for_tab.append(article)

        # Sort all articles by date (descending)
        all_articles_for_tab.sort(key=get_sortable_date, reverse=True)

        # Top Tech (spec 01 M4/M5): dedup + first page at the default size,
        # rendered by the same shared view the controller callback uses.
        results_children, _page = _render_top_tech_view(all_articles_for_tab)
        results_container = html.Div(
            results_children,
            id=f"{tab_search_id}-results",
            className="mt-1",  # no 800px scroll: pagination replaces it (M4)
        )
        # M4 items-per-page selector + M5 "mostrar duplicados" switch
        controls_row = dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Items por página:", className="form-label small mb-0 me-2"),
                        dcc.Dropdown(
                            id=f"{TOP_TECH_COMPONENT_ID}-items-per-page",
                            options=[{"label": str(size), "value": size} for size in TOP_TECH_PER_PAGE_OPTIONS],
                            value=TOP_TECH_DEFAULT_PER_PAGE,
                            clearable=False,
                            style={"minWidth": "90px"},
                        ),
                    ],
                    width="auto",
                    className="d-flex align-items-center",
                ),
                dbc.Col(
                    create_duplicate_toggle(TOP_TECH_COMPONENT_ID),
                    width="auto",
                    className="d-flex align-items-center",
                ),
            ],
            className="mb-3 align-items-center",
        )
        tab_children = [search_row, controls_row, results_container, dcc.Store(id=f"{TOP_TECH_COMPONENT_ID}-page", data=1)]
        return html.Div(tab_children)

    # The table as the search controller builds it for an empty search: the controller is then
    # idle until the user types
    return html.Div([search_row, html.Div(_render_news_results(list(source_keys)), id=f"{tab_search_id}-results")])


def _build_global_results_table(results: list[dict[str, Any]], search_term: str | None = None) -> Any:
    """Build the "🔎 Global" results table (⭐ save column + Title/Fuente/Date).

    Extracted from the global-search callback (T-053) so the static renderer,
    the callback and the tests all render the identical star column.
    """
    trending_map = get_trending_items_map()
    columns = [
        {
            "header": "",
            "cell": lambda a: saved_items.save_button(a, NEWS_SAVE_BTN_TYPE, tab="news"),
            "td_kwargs": {"style": {"width": "2rem"}},
        },
        {
            "header": "Title",
            "cell": lambda a: html.Div(
                [
                    title_cell(a, search_term or "", title_fields=("title", "name", "full_name")),
                    render_trend_badge(match_item_trend(a, trending_map)),
                ]
            ),
        },
        {"header": "Fuente", "cell": lambda a: a.get("source_display_name", "?")},
        {"header": "Date", "cell": lambda a: format_article_date(a)},
    ]
    return render_items_table(results, columns, empty_message="Sin resultados.", wrap_scroll=False)


def register_news_search_callbacks(app):
    """Register search callbacks for all news tabs."""
    # Derive search IDs from the same tab definitions used to build the layout
    # so every subtab's search box is guaranteed to be wired.
    search_ids = [_search_id_for_tab(tab_def) for tab_def in NEWS_TAB_DEFINITIONS]

    # --- Top Tech controller (spec 01 M4/M5) ---------------------------------
    # The SAME single controller pattern as the generic loop below, extended
    # with extra Inputs instead of a second callback chain: items-per-page
    # (M4), "mostrar duplicados" toggle (M5) and the pattern-matching pager
    # buttons all feed this one callback, which stays the only writer of the
    # results container. prevent_initial_call=True because the static layout
    # already renders the identical default view via _render_top_tech_view.
    @app.callback(
        Output(f"{TOP_TECH_SEARCH_ID}-results", "children"),
        Output(f"{TOP_TECH_COMPONENT_ID}-page", "data"),
        Input(TOP_TECH_SEARCH_ID, "value"),
        Input(f"{TOP_TECH_COMPONENT_ID}-items-per-page", "value"),
        Input(f"{TOP_TECH_COMPONENT_ID}-show-duplicates", "value"),
        Input({"type": f"{TOP_TECH_COMPONENT_ID}-page-btn", "dir": ALL}, "n_clicks"),
        State(f"{TOP_TECH_COMPONENT_ID}-page", "data"),
        prevent_initial_call=True,
    )
    def update_top_tech_view(search_term, items_per_page, show_duplicates_value, _page_btn_clicks, current_page):
        """Render Top Tech with visible dedup + pagination, fetching fresh data."""
        try:
            articles = _aggregate_source_articles(_TOP_TECH_DEF["keys"], get_all_news_data())
            if not articles:
                return dbc.Alert("No data available (fetch returned empty)", color="warning"), 1

            if search_term:
                articles = filter_content(search_term, articles, get_common_searchable_fields("news"))

            # Defensive validation: the page size arrives straight from the client
            try:
                per_page = int(items_per_page)
            except (TypeError, ValueError):
                per_page = TOP_TECH_DEFAULT_PER_PAGE
            if per_page not in TOP_TECH_PER_PAGE_OPTIONS:
                per_page = TOP_TECH_DEFAULT_PER_PAGE

            # Prev/next move within range; any other trigger (search, page size,
            # dedup toggle) resets to page 1 — same UX as the Videos tab
            triggered_id = dash.ctx.triggered_id
            direction = triggered_id.get("dir") if isinstance(triggered_id, dict) else None
            current_page = current_page or 1
            if direction == "prev":
                page = max(1, current_page - 1)
            elif direction == "next":
                page = current_page + 1
            else:
                page = 1

            results_children, page = _render_top_tech_view(
                articles,
                search_term=search_term,
                show_duplicates=bool(show_duplicates_value),
                per_page=per_page,
                page=page,
            )
            return results_children, page
        except Exception as e:
            logger.error(f"Error in Top Tech view callback: {e}")
            return dbc.Alert(f"Error loading Top Tech articles: {e}", color="danger"), dash.no_update

    # Top Tech's clear-search button (same contract as the generic loop's,
    # kept out of the loop because this subtab registers its own controller)
    @app.callback(
        Output(TOP_TECH_SEARCH_ID, "value", allow_duplicate=True),
        Input(f"{TOP_TECH_SEARCH_ID}-clear", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_top_tech_search(n_clicks):
        """Clear the Top Tech search input."""
        if n_clicks:
            return ""
        return dash.no_update

    # --- Generic per-subtab controllers --------------------------------------
    for search_id in search_ids:
        if search_id == TOP_TECH_SEARCH_ID:
            continue  # Top Tech is fully handled by the controller above

        @app.callback(
            Output(f"{search_id}-results", "children"),
            [Input(search_id, "value")],
            # Idle on insertion: the layout already holds the table this builds for an empty search
            prevent_initial_call=True,
        )
        def update_news_search(search_term, current_search_id=search_id):
            """Show the subtab's articles that match the search term."""
            try:
                # The search id carries the source keys: news-search-{key} or news-search-{key1}-{key2}
                source_keys = current_search_id.replace("news-search-", "").split("-")
                return _render_news_results(source_keys, search_term)

            except Exception as e:
                logger.error(f"Error in news search callback for {current_search_id}: {e}")
                return dbc.Alert(f"Error searching articles: {e}", color="danger")

        # Clear search callback
        @app.callback(
            Output(search_id, "value", allow_duplicate=True),
            Input(f"{search_id}-clear", "n_clicks"),
            prevent_initial_call=True,
        )
        def clear_news_search(n_clicks):
            """Clear search input."""
            if n_clicks:
                return ""
            return dash.no_update

    # Global search across every news source (spec 01 F1)
    @app.callback(
        Output("news-global-results", "children"),
        [Input("news-global-search-input", "value"), Input("news-global-range", "value")],
        prevent_initial_call=True,
    )
    def news_global_search(search_term, date_range):
        """Search every news source at once and render a unified table."""
        try:
            from datetime import datetime, timezone

            term = (search_term or "").strip()
            if not term:
                return dbc.Alert("Escribe un término para comenzar.", color="secondary")

            all_news_data = get_all_news_data()
            range_seconds = {"7d": 7 * 86400, "30d": 30 * 86400, "all": None}.get(date_range)

            now = datetime.now(timezone.utc)
            combined = []
            empty_sources = []
            for key, cfg in _ALL_NEWS_SOURCES.items():
                items = all_news_data.get(key, [])
                if not items:
                    empty_sources.append(cfg.get("name", key))
                    continue
                for article in items:
                    article = dict(article)
                    article["source_display_name"] = article.get("source", cfg.get("name", key))
                    if range_seconds:
                        dt = get_sortable_date(article)
                        if dt is None:
                            continue
                        delta = (now - dt).total_seconds() if dt.tzinfo else (now.replace(tzinfo=None) - dt).total_seconds()
                        if delta > range_seconds:
                            continue
                    combined.append(article)

            searchable_fields = get_common_searchable_fields("news")
            results = filter_content(term, combined, searchable_fields)
            results.sort(key=get_sortable_date, reverse=True)

            sources_hit = {r.get("source_display_name", "?") for r in results}
            header_alert = dbc.Alert(
                f"🔎 {len(results)} resultados de {len(sources_hit)} fuentes para '{term}'" + (f" (últimos {date_range[:-1]} días)" if range_seconds else ""),
                color="success",
                className="mb-3",
            )

            if not results:
                hint = f" Fuentes sin datos ahora mismo: {', '.join(empty_sources[:8])}" if empty_sources else ""
                return dbc.Alert(f"Sin resultados para '{term}'.{hint}", color="info")

            table = _build_global_results_table(results[:200], term)
            return html.Div([header_alert, html.Div(table, style={"maxHeight": "700px", "overflowY": "auto", "paddingRight": "15px"})])
        except Exception as e:
            logger.error(f"Error in news global search: {e}")
            return dbc.Alert(f"Error en la búsqueda global: {e}", color="danger")

    # Per-subtab CSV export (spec 01 F3)
    @app.callback(
        Output("news-export-download", "data"),
        Input({"type": "news-export", "keys": dash.ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def export_news_subtab(_n_clicks):
        """Download the clicked subtab's dataset as CSV."""
        try:
            import csv
            import io

            keys_str = dash.ctx.triggered_id.keys
            keys = [keys_str] if keys_str in _ALL_NEWS_SOURCES else keys_str.split("-")
            all_news_data = get_all_news_data()
            rows = []
            for key in keys:
                for article in all_news_data.get(key, []):
                    if not isinstance(article, dict):
                        continue
                    rows.append(
                        {
                            "title": article.get("title") or article.get("name") or "",
                            "url": article.get("url") or article.get("link") or "",
                            "source": article.get("source", _ALL_NEWS_SOURCES.get(key, {}).get("name", key)),
                            "date": str(article.get("published") or article.get("published_at") or article.get("date") or ""),
                            "summary": (article.get("summary") or "")[:300],
                        }
                    )
            if not rows:
                return dash.no_update
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=["title", "url", "source", "date", "summary"])
            writer.writeheader()
            writer.writerows(rows)
            return dcc.send_string(buf.getvalue(), f"watchtower_news_{keys_str}.csv", type="text/csv")
        except Exception as e:
            logger.error(f"Error exporting news subtab: {e}")
            return dash.no_update

    # ⭐ Save/unsave toggles for the "🔎 Global" results (T-053): pattern-
    # matching callback on the star buttons only; targets new outputs so the
    # controllers above are untouched.
    saved_items.register_save_toggle_callback(app, NEWS_SAVE_BTN_TYPE)


# Main function to render the news tab
def _news_item_hash(url: str, title: str) -> str:
    """Stable per-item key for read-state tracking (matches assets/js/read_state.js)."""
    import hashlib

    key = (url or "").strip().lower() or (title or "").strip().lower()
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def _build_global_search_tab() -> dbc.Tab:
    """Build the '🔎 Global' subtab: one query across every news source."""
    return dbc.Tab(
        label="🔎 Global",
        tab_id="news-tab-global",
        children=html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Input(
                                id="news-global-search-input",
                                type="text",
                                placeholder="Buscar en todas las fuentes de noticias… (ej. llama, docker, valencia)",
                                debounce=True,
                                className="form-control form-control-lg",
                            ),
                            xs=12,
                            md=8,
                        ),
                        dbc.Col(
                            dcc.Dropdown(
                                id="news-global-range",
                                options=[
                                    {"label": "Últimos 7 días", "value": "7d"},
                                    {"label": "Últimos 30 días", "value": "30d"},
                                    {"label": "Todo", "value": "all"},
                                ],
                                value="all",
                                clearable=False,
                            ),
                            xs=12,
                            md=4,
                        ),
                    ],
                    className="mb-3",
                ),
                html.Div(
                    dbc.Alert(
                        f"Escribe un término para buscar en las {len(_ALL_NEWS_SOURCES)} fuentes a la vez. Los resultados se agrupan en una sola tabla con su fuente.",
                        color="secondary",
                    ),
                    id="news-global-results",
                ),
            ],
            className="pt-2",
        ),
    )


def render_news_tab():
    """Render the complete news tab with all sub-tabs."""
    tab_definitions = NEWS_TAB_DEFINITIONS

    # "🔎 Global" moved to LAST (user feedback 2026-08-27: the daily-driver
    # sources should come first; global search is the fallback)
    tabs_children = []
    for tab_def in tab_definitions:
        tab_id = f"news-tab-{tab_def['id']}"
        content = create_news_source_tab_content(tab_def["keys"], combined_name=tab_def["label"], with_pagination=tab_def.get("paginated", False))
        tabs_children.append(
            dbc.Tab(
                label=tab_def["label"],
                tab_id=tab_id,
                children=content,
                id=tab_id + "-container",
            )  # Added id to tab for potential future targeting
        )
    tabs_children.append(_build_global_search_tab())

    return html.Div(
        [
            html.H3("News Feed", className="mb-3"),
            html.Div(
                [
                    html.Button(
                        "👁 Marcar mostrados como leido",
                        id="news-mark-all-read",
                        className="btn btn-sm btn-outline-secondary me-2",
                        title="Marca los items mostrados como leido (persiste en este navegador)",
                    ),
                    html.Button(
                        "🙈 Ocultar leídos: OFF",
                        id="news-toggle-hide-read",
                        className="btn btn-sm btn-outline-secondary me-2",
                    ),
                    html.Span(id="news-read-count", className="text-muted small"),
                ],
                className="mb-2",
            ),
            # Source-health dots removed from News (user feedback 2026-08-27:
            # always-gray + redundant with the Metrics freshness card); the
            # shared helper stays available — KG still renders its own row
            dcc.Download(id="news-export-download"),
            dbc.Tabs(
                id="news-source-tabs-main",
                children=tabs_children,
                active_tab=f"news-tab-{tab_definitions[0]['id']}",
            ),
        ]
    )
