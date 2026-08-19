import logging

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html

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
from src.web.dashboard.components.shared.health import source_health_dots
from src.web.dashboard.components.shared.table import render_items_table, title_cell
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

    global _NEWS_CACHE  # type: ignore
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

# Single source of truth for the subtab list. render_news_tab() builds the
# dbc.Tabs from it and register_news_search_callbacks() derives the search
# input IDs from it, so a new tab can never end up with a dead search box.
NEWS_TAB_DEFINITIONS = [
    {
        "label": "Top Tech",
        "keys": ["techcrunch", "venturebeat", "arstechnica", "kagi_ai"],
        "id": "top_tech",
    },
    {"label": "freeCodeCamp", "keys": "freecodecamp", "id": "fcc"},
    {"label": "Google AI Blog", "keys": "google_ai_blog", "id": "gaib"},
    {"label": "Lobsters", "keys": "lobsters", "id": "lobsters"},
    {
        "label": "FutureTools & Ben's Bites",
        "keys": ["futuretools", "bensbites"],
        "id": "ft-bb",
    },
    {"label": "Hacker News", "keys": "hackernews", "id": "hn"},
    {"label": "tldr.tech", "keys": "tldr", "id": "tldr"},
    {"label": "Medium GenAI", "keys": "medium_genai", "id": "med_genai"},
    {"label": "KDnuggets", "keys": "kdnuggets", "id": "kdn"},
    {"label": "Meneame General", "keys": "meneame_general", "id": "men_gen"},
    {"label": "Meneame Tech", "keys": "meneame_tecnologia", "id": "men_tec"},
    {"label": "Indie Hackers", "keys": "indiehackers", "id": "ih"},
    # Kagi RSS feeds as individual tabs
    {"label": "Kagi World", "keys": "kagi_world", "id": "kagi_world"},
    {"label": "Kagi USA", "keys": "kagi_usa", "id": "kagi_usa"},
    {"label": "Kagi Business", "keys": "kagi_business", "id": "kagi_business"},
    {"label": "Kagi Science", "keys": "kagi_science", "id": "kagi_science"},
    {"label": "Kagi Gaming", "keys": "kagi_gaming", "id": "kagi_gaming"},
    {"label": "Kagi Europe", "keys": "kagi_europe", "id": "kagi_europe"},
    {"label": "Kagi Spain", "keys": "kagi_spain", "id": "kagi_spain"},
    {"label": "Microsiervos", "keys": "microsiervos", "id": "microsiervos"},
    {"label": "🇪🇸 Spanish Tech", "keys": "spanish_tech", "id": "spanish_tech"},
    {"label": "☁️ Cloud Updates", "keys": "cloud_updates", "id": "cloud_updates"},
    {"label": "📍 Valencia Local", "keys": "valencia_local", "id": "valencia_local"},
]


def _search_id_for_tab(tab_def: dict) -> str:
    """Derive the search input ID for a tab definition.

    Mirrors the logic in create_news_source_tab_content so layout and
    callbacks always agree on the ID.
    """
    keys = tab_def["keys"]
    if isinstance(keys, str):
        return f"news-search-{keys}"
    return f"news-search-{'-'.join(keys)}"


# format_article_date removed (using shared logic)
def format_article_date(article):
    """Wrapper for shared formatting."""
    return format_article_date_shared(article)


# Removed create_article_card function as it's no longer needed for table view


def create_news_source_tab_content(source_keys, combined_name=None):
    """Creates the content for a news tab as a table with search functionality, potentially combining multiple sources.

    Sorts articles by date before limiting.
    """
    all_articles_for_tab = []
    if isinstance(source_keys, str):  # Single source key
        source_keys = [source_keys]
        source_display_name = _ALL_NEWS_SOURCES[source_keys[0]]["name"]
        tab_search_id = f"news-search-{source_keys[0]}"
    else:  # List of source keys (for combined tabs)
        source_display_name = combined_name or "Combined News"
        tab_search_id = f"news-search-{'-'.join(source_keys)}"

    # Load fresh data each time
    all_news_data = get_all_news_data()

    for key in source_keys:
        articles_from_source = all_news_data.get(key, [])
        # Add source name to each article for display in the table
        for article in articles_from_source:
            # Use 'source_display' to ensure we have a consistent field for the table
            article["source_display_name"] = article.get("source", _ALL_NEWS_SOURCES[key]["name"])
        all_articles_for_tab.extend(articles_from_source)

    # Sort all articles by date (descending)
    all_articles_for_tab.sort(key=get_sortable_date, reverse=True)

    if not all_articles_for_tab:
        return dbc.Alert(f"No news items available for {source_display_name}.", color="info")

    # Create table header
    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Title"),
                    html.Th("Source"),
                    html.Th("Date"),
                ]
            )
        )
    ]

    # Load trend data
    trending_map = get_trending_items_map()

    # Create table body with robust field fallbacks for heterogeneous sources
    table_body_rows = []
    for _i, article in enumerate(all_articles_for_tab[:MAX_ARTICLES_PER_SOURCE]):
        # Match by id, url, source or trending term in the title
        trend_record = match_item_trend(article, trending_map)
        is_trending = trend_record is not None
        trend_badge = render_trend_badge(trend_record)

        # Title fallbacks: common across Product Hunt/GitHub Trends/others
        title = article.get("title") or article.get("name") or article.get("full_name") or "No Title"
        # URL fallbacks
        url = article.get("url") or article.get("link") or article.get("html_url") or article.get("website")
        # Use the 'source_display_name' we added earlier
        source_for_display = article.get("source_display_name", source_display_name)
        date_display = format_article_date(article)

        # Add trending class for filtering
        row_class = "trending-item" if is_trending else ""

        table_body_rows.append(
            html.Tr(
                [
                    html.Td(
                        [
                            html.A(title, href=url, target="_blank") if url else title,
                            trend_badge,
                        ]
                    ),
                    html.Td(source_for_display),
                    html.Td(date_display),
                    # Hidden cell for trend filtering
                    html.Td(
                        str(is_trending).lower(),
                        style={"display": "none"},
                        className="is-trending-data",
                    ),
                ],
                className=row_class,
                # Read/unread tracking key (see assets/js/read_state.js)
                **{"data-item-hash": _news_item_hash(url or "", title or "")},
            )
        )

    table_body = [html.Tbody(table_body_rows)]

    # Combine header and body into a dbc.Table
    table = dbc.Table(
        table_header + table_body,
        bordered=True,
        hover=True,
        responsive=True,  # Makes table scroll horizontally on small screens
        striped=True,
        size="sm",
        color="dark",
        className="table-responsive mb-0",  # Remove default bottom margin if wrapped in Div with padding
    )

    # Return search input and table container
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        # Search input
                        create_search_input(
                            input_id=tab_search_id,
                            placeholder=f"Filter {source_display_name} by term...",
                            clear_button=True,
                        ),
                        width=True,
                    ),
                    dbc.Col(
                        dbc.Button(
                            "⬇ CSV",
                            id={"type": "news-export", "keys": "-".join([source_keys] if isinstance(source_keys, str) else source_keys)},
                            color="secondary",
                            size="sm",
                            title="Exportar el dataset de este subtab a CSV",
                        ),
                        width="auto",
                    ),
                    # Trend filter button removed
                ],
                className="mb-3 align-items-center",
            ),
            # Container for filtered results
            html.Div(
                table,
                id=f"{tab_search_id}-results",
                style={
                    "maxHeight": "800px",
                    "overflowY": "auto",
                    "paddingRight": "15px",
                },
            ),
        ]
    )


def register_news_search_callbacks(app):
    """Register search callbacks for all news tabs."""
    # Derive search IDs from the same tab definitions used to build the layout
    # so every subtab's search box is guaranteed to be wired.
    search_ids = [_search_id_for_tab(tab_def) for tab_def in NEWS_TAB_DEFINITIONS]

    for search_id in search_ids:

        @app.callback(
            Output(f"{search_id}-results", "children"),
            [Input(search_id, "value")],
            # prevent_initial_call=False (default), so it runs on load
        )
        def update_news_search(search_term, current_search_id=search_id):
            """Update news display based on search term. Fetches fresh data on execution."""
            try:
                # 1. Determine Source Keys from Search ID
                # Format: news-search-{key} or news-search-{key1}-{key2}
                id_suffix = current_search_id.replace("news-search-", "")
                if id_suffix == "futuretools-bensbites":
                    source_keys = ["futuretools", "bensbites"]
                else:
                    source_keys = id_suffix.split("-")

                # 2. Fetch Fresh Data (CACHE HIT usually, unless cleared)
                all_news_data = get_all_news_data()

                # 3. Aggregate Data for this Tab
                articles_data = []
                for key in source_keys:
                    # Robust key matching (try exact, then maybe underscore/dash swap if needed)
                    # Keys in config use underscores. ID uses dashes?
                    # Let's attempt to access direct key first, then try replace
                    if key in all_news_data:
                        source_articles = all_news_data[key]
                        # Enrich with source display name
                        for art in source_articles:
                            art["source_display_name"] = _ALL_NEWS_SOURCES[key]["name"]
                        articles_data.extend(source_articles)
                    else:
                        # Try swapping dash to underscore just in case
                        alt_key = key.replace("-", "_")
                        if alt_key in all_news_data:
                            source_articles = all_news_data[alt_key]
                            # Enrich with source display name
                            for art in source_articles:
                                art["source_display_name"] = _ALL_NEWS_SOURCES[alt_key]["name"]
                            articles_data.extend(source_articles)

                if not articles_data:
                    return dbc.Alert("No data available (fetch returned empty)", color="warning")

                # 4. Sort
                articles_data.sort(key=get_sortable_date, reverse=True)

                # 5. Filter (Search)
                if search_term:
                    searchable_fields = get_common_searchable_fields("news")
                    filtered_articles = filter_content(search_term, articles_data, searchable_fields)
                else:
                    filtered_articles = articles_data[:MAX_ARTICLES_PER_SOURCE]  # Limit initial view

                # Legacy filtering block removed

                # Create table for filtered results
                table_header = [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Title"),
                                html.Th("Source"),
                                html.Th("Date"),
                            ]
                        )
                    )
                ]

                # Load trend data for rendering badges
                trending_map = get_trending_items_map()

                table_body_rows = []
                for _i, article in enumerate(filtered_articles):
                    # Match by id, url, source or trending term in the title
                    trend_record = match_item_trend(article, trending_map)
                    is_trending = trend_record is not None
                    trend_badge = render_trend_badge(trend_record)

                    # Title fallbacks: common across news sources
                    title = article.get("title") or article.get("name") or article.get("full_name") or "No Title"
                    # URL fallbacks
                    url = article.get("url") or article.get("link") or article.get("html_url") or article.get("website")
                    # Use the 'source_display_name' if available
                    source_for_display = article.get("source_display_name", "Unknown")
                    date_display = format_article_date(article)

                    # Real highlight components when a search term is active
                    title_children = highlight_segments(title, search_term) if search_term else title

                    # Add trending class
                    row_class = "trending-item" if is_trending else ""

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
                            className=row_class,
                            **{"data-item-hash": _news_item_hash(url or "", title or "")},
                        )
                    )

                table_body = [html.Tbody(table_body_rows)]

                # Combine header and body into a dbc.Table
                table = dbc.Table(
                    table_header + table_body,
                    bordered=True,
                    hover=True,
                    responsive=True,
                    striped=True,
                    size="sm",
                    color="dark",
                    className="table-responsive mb-0",
                )

                # Only show alert if a search term is active
                if search_term:
                    alert = dbc.Alert(
                        f"📰 Found {len(filtered_articles)} articles matching '{search_term}'",
                        color="success",
                        className="mb-3",
                    )
                else:
                    alert = None

                return html.Div(
                    [
                        alert,
                        table,
                    ],
                    style={
                        "maxHeight": "800px",
                        "overflowY": "auto",
                        "paddingRight": "15px",
                    },
                )

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

            trending_map = get_trending_items_map()
            columns = [
                {
                    "header": "Title",
                    "cell": lambda a: html.Div(
                        [
                            title_cell(a, term, title_fields=("title", "name", "full_name")),
                            render_trend_badge(match_item_trend(a, trending_map)),
                        ]
                    ),
                },
                {"header": "Fuente", "cell": lambda a: a.get("source_display_name", "?")},
                {"header": "Date", "cell": lambda a: format_article_date(a)},
            ]
            table = render_items_table(results[:200], columns, empty_message="Sin resultados.", wrap_scroll=False)
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
                        "Escribe un término para buscar en las 26 fuentes a la vez. Los resultados se agrupan en una sola tabla con su fuente.",
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

    tabs_children = [_build_global_search_tab()]
    for tab_def in tab_definitions:
        tab_id = f"news-tab-{tab_def['id']}"
        content = create_news_source_tab_content(tab_def["keys"], combined_name=tab_def["label"])
        tabs_children.append(
            dbc.Tab(
                label=tab_def["label"],
                tab_id=tab_id,
                children=content,
                id=tab_id + "-container",
            )  # Added id to tab for potential future targeting
        )

    # Health dots for every configured source (spec 01 F4)
    health_sources = {cfg["name"]: cfg.get("path", "") for cfg in _ALL_NEWS_SOURCES.values() if cfg.get("path")}

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
            source_health_dots(health_sources, title="Salud de fuentes:"),
            dcc.Download(id="news-export-download"),
            dbc.Tabs(
                id="news-source-tabs-main",
                children=tabs_children,
                active_tab="news-tab-global",
            ),
        ]
    )
