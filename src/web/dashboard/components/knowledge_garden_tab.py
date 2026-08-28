import logging
from pathlib import Path
from typing import Any

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

# Import shared utilities
# Import repository pattern (NEW)
from src.repositories import BaseRepository
from src.services.data_loader import (
    KNOWLEDGE_SOURCES_CONFIG,
    get_sortable_date,
)
from src.services.data_loader import (
    format_article_date as format_article_date_shared,
)
from src.web.dashboard.components import saved_items
from src.web.dashboard.components.shared.cache import TTLDataCache
from src.web.dashboard.components.shared.health import source_health_dots
from src.web.dashboard.components.shared.table import (
    create_refresh_button,
    paginate,
    pagination_controls,
    render_items_table,
    title_cell,
)
from src.web.dashboard.search_utils import (
    create_search_input,
    filter_content,
    highlight_segments,
)

logger = logging.getLogger(__name__)

# KNOWLEDGE GARDEN TAB - Reddit, dev communities, and similar sources
# KNOWLEDGE_SOURCES_CONFIG imported from data_loader


# NEW: Repository-based loading (SOLID Pattern)
class KnowledgeGardenRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for knowledge garden data."""

    def __init__(self, data_path: str):
        """Initialize knowledge garden repository.

        Args:
            data_path: Path to knowledge data file
        """
        super().__init__(
            data_path=Path(data_path),
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform JSON data into list of knowledge items.

        Args:
            raw_data: Raw JSON data

        Returns:
            List of knowledge item dictionaries
        """
        if isinstance(raw_data, list):
            return raw_data
        elif isinstance(raw_data, dict):
            # Handle cases where JSON might be a dict with a key containing the list
            if "articles" in raw_data and isinstance(raw_data["articles"], list):
                return raw_data["articles"]
            elif "items" in raw_data and isinstance(raw_data["items"], list):
                return raw_data["items"]
            # Single item
            if all(k in raw_data for k in ["title", "url"]):
                return [raw_data]
            return []
        else:
            return []


# Create singleton instances for each source
opensource_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["opensource"]["path"])
reddit_opensource_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["reddit_opensource"]["path"])
gooddevs_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["gooddevs"]["path"])
podcasts_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["podcasts"]["path"])
product_hunt_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["product_hunt"]["path"])
gittrends_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["gittrends"]["path"])
hackernews_ask_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["hackernews_ask"]["path"])
stackoverflow_trends_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["stackoverflow_trends"]["path"])
reddit_unified_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["reddit_unified"]["path"])
reddit_ai_ml_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["reddit_ai_ml"]["path"])
reddit_programming_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["reddit_programming"]["path"])
reddit_tech_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["reddit_tech"]["path"])
reddit_devops_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["reddit_devops"]["path"])
devto_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["devto"]["path"])
hypeurls_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["hypeurls"]["path"])
lesswrong_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["lesswrong"]["path"])
substack_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["substack"]["path"])
trendshift_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["trendshift"]["path"])
rss_feeds_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["rss_feeds"]["path"])


# load_knowledge_from_file removed (unused/dead code)


# Load knowledge data dynamically instead of at import time
def _load_all_knowledge_data():
    """Read every configured source through its repository."""
    repository_map = {
        "opensource": opensource_repo,
        "reddit_opensource": reddit_opensource_repo,
        "gooddevs": gooddevs_repo,
        "podcasts": podcasts_repo,
        "product_hunt": product_hunt_repo,
        "gittrends": gittrends_repo,
        "hackernews_ask": hackernews_ask_repo,
        "stackoverflow_trends": stackoverflow_trends_repo,
        "reddit_unified": reddit_unified_repo,
        "reddit_ai_ml": reddit_ai_ml_repo,
        "reddit_programming": reddit_programming_repo,
        "reddit_tech": reddit_tech_repo,
        "reddit_devops": reddit_devops_repo,
        "devto": devto_repo,
        "hypeurls": hypeurls_repo,
        "lesswrong": lesswrong_repo,
        "substack": substack_repo,
        "trendshift": trendshift_repo,
        "rss_feeds": rss_feeds_repo,
    }

    data = {}
    for source_key, repo in repository_map.items():
        try:
            data[source_key] = repo.get()
        except Exception:
            # Gracefully handle missing/corrupt data files (e.g. ETL not yet run)
            data[source_key] = []
    return data


# Module cache via the shared TTL helper (spec 15 M2 — no NameError antipattern)
_knowledge_cache = TTLDataCache(ttl_seconds=60)


def get_all_knowledge_data(force_refresh: bool = False):
    """Load knowledge data from all configured sources (60s module cache)."""
    return _knowledge_cache.get(_load_all_knowledge_data, force_refresh=force_refresh)


# --- Helper function to parse dates ---
# parse_date logic removed (using shared parse_date)


# --- Layout Generation ---

MAX_ARTICLES_PER_SOURCE = 50  # Limit number of articles displayed per source initially

# Single source of truth for the subtab list; search input IDs are derived
# from it so every subtab's search box is guaranteed to be wired.
KNOWLEDGE_TAB_DEFINITIONS = [
    {"label": "LessWrong", "keys": "lesswrong", "id": "lw"},
    {"label": "Good Devs", "keys": "gooddevs", "id": "gd"},
    {"label": "Podcasts", "keys": "podcasts", "id": "pod"},
    {"label": "Reddit AI/ML", "keys": "reddit_ai_ml", "id": "reddit_ai_ml"},
    {
        "label": "Reddit Programming",
        "keys": "reddit_programming",
        "id": "reddit_prog",
    },
    {"label": "Reddit Tech", "keys": "reddit_tech", "id": "reddit_tech"},
    {"label": "Reddit DevOps", "keys": "reddit_devops", "id": "reddit_devops"},
    {"label": "Reddit All", "keys": "reddit_unified", "id": "reddit_all"},
    {"label": "Git Trends", "keys": "gittrends", "id": "gt"},
    {"label": "HN Ask", "keys": "hackernews_ask", "id": "hn_ask"},
    {"label": "Stack Overflow", "keys": "stackoverflow_trends", "id": "so"},
    {"label": "Product Hunt", "keys": "product_hunt", "id": "ph"},
    # Developer community tab
    {"label": "Dev.to", "keys": "devto", "id": "devto"},
    {"label": "HypeURLs", "keys": "hypeurls", "id": "hypeurls"},
    {"label": "Open Source", "keys": ["opensource", "reddit_opensource"], "id": "opensource"},
    {"label": "Substack", "keys": "substack", "id": "substack"},
    {"label": "TrendShift", "keys": "trendshift", "id": "trendshift"},
    {"label": "RSS Feeds", "keys": "rss_feeds", "id": "rss_feeds"},
]


def _knowledge_search_id(tab_def: dict) -> str:
    """Derive the search input ID for a tab definition (layout and callbacks agree)."""
    keys = tab_def["keys"]
    if isinstance(keys, str):
        return f"knowledge-search-{keys}"
    return f"knowledge-search-{'-'.join(keys)}"


# format_article_date removed (using shared logic)
def format_article_date(article):
    """Wrapper for shared formatting."""
    return format_article_date_shared(article)


# hash -> full item dict at render time. The registry itself now lives in the
# shared saved-items module (also used by News, Tech Radar and Markets, T-053);
# this alias keeps the historical name working for this tab's toggle callback.
_SAVE_REGISTRY: dict[str, dict] = saved_items.SAVE_CANDIDATES

KG_SAVE_BTN_TYPE = "kg-save-btn"


def _save_button(article: dict) -> dbc.Button:
    """Star/unstar button for a knowledge item (pattern-matching id per hash)."""
    return saved_items.save_button(article, KG_SAVE_BTN_TYPE, tab="knowledge_garden")


# Friendly labels for the saved-record "tab" field (T-053: News / Tech Radar /
# Markets now star into the same file). Old KG entries predate the field.
_SAVED_TAB_LABELS = {"knowledge_garden": "garden", "news": "news", "tech_radar": "radar", "markets": "markets"}


def _saved_tab_badge(tab: str | None) -> dbc.Badge:
    """Origin badge for a saved row (defaults to the garden for old records)."""
    label = _SAVED_TAB_LABELS.get(tab or "", tab or "garden")
    return dbc.Badge(label, color="secondary", pill=True, className="text-lowercase")


def _render_saved_subtab() -> html.Div:
    """Render the '⭐ Guardados' subtab content (read-it-later list)."""
    saved = saved_items.load_saved()
    container = html.Div(id="kg-saved-results")
    if not saved:
        container.children = dbc.Alert("Todavía no has guardado nada. Pulsa la estrella ☆ de cualquier item de la garden.", color="info")
        return container
    rows = [
        html.Tr(
            [
                html.Td(_save_button({"url": s.get("url"), "title": s.get("title"), "source": s.get("source")})),
                html.Td(html.A(s.get("title", ""), href=s.get("url"), target="_blank")),
                html.Td(s.get("source", "")),
                html.Td(_saved_tab_badge(s.get("tab"))),
                html.Td(s.get("saved_at", "")),
            ]
        )
        for s in saved
    ]
    table = dbc.Table(
        [html.Thead(html.Tr([html.Th(""), html.Th("Title"), html.Th("Source"), html.Th("Tab"), html.Th("Saved")]))] + [html.Tbody(rows)],
        bordered=True,
        hover=True,
        striped=True,
        size="sm",
        color="dark",
    )
    container.children = html.Div(table, style={"maxHeight": "800px", "overflowY": "auto", "paddingRight": "15px"})
    return container


# Card-view toggle (spec 03 F2): available views and the label the toggle
# button shows while a given view is active (i.e. what a click switches TO).
KG_VIEWS = ("list", "cards")
KG_VIEW_TOGGLE_LABELS = {"list": "▦ Tarjetas", "cards": "☰ Lista"}

# Fields probed (first hit wins) for the card snippet text.
_KG_SNIPPET_FIELDS = ("summary", "description")


def _knowledge_card(article: dict, search_term: str = "") -> dbc.Col:
    """Build one minimalist result card (title, source, snippet, link + star).

    Mirrors the videos-tab card pattern (2-line clamped title, muted metadata)
    so both grids feel like the same design language.
    """
    title = next((str(article.get(f)) for f in ("title", "name", "full_name") if article.get(f)), "No Title")
    url = next((article.get(f) for f in ("url", "link", "html_url", "website") if article.get(f)), None)
    snippet = next((str(article.get(f)) for f in _KG_SNIPPET_FIELDS if article.get(f)), "")

    title_children = highlight_segments(title, search_term) if search_term else title
    snippet_children = highlight_segments(snippet, search_term) if (search_term and snippet) else snippet

    header = html.Div(
        [
            _save_button(article),
            dbc.Badge(article.get("source_display_name", "Knowledge"), color="secondary", pill=True, className="text-lowercase ms-auto"),
        ],
        className="d-flex align-items-center mb-1",
    )

    body = [
        header,
        html.H6(
            html.A(title_children, href=url, target="_blank", style={"color": "#A37FFF", "textDecoration": "none"}) if url else html.Span(title_children),
            className="card-title mb-1",
            style={"fontSize": "0.9rem", "overflow": "hidden", "textOverflow": "ellipsis", "display": "-webkit-box", "-webkitLineClamp": "2", "-webkitBoxOrient": "vertical", "minHeight": "2.5em"},
        ),
    ]
    if snippet:
        body.append(
            html.P(
                snippet_children,
                className="card-text text-muted mb-1",
                style={"fontSize": "0.8rem", "overflow": "hidden", "textOverflow": "ellipsis", "display": "-webkit-box", "-webkitLineClamp": "2", "-webkitBoxOrient": "vertical"},
            )
        )
    body.append(html.P(format_article_date(article), className="card-text text-muted mb-0", style={"fontSize": "0.75rem"}))

    return dbc.Col(
        dbc.Card(dbc.CardBody(body), className="h-100"),
        xs=12,
        sm=6,
        md=4,
        className="mb-3",
    )


def build_knowledge_table(source_keys, search_term: str = "", display_name: str = "Knowledge", page: int = 1, view: str = "list"):
    """Build the knowledge items list or card grid, filtered, highlighted and paginated.

    Args:
        view: ``"list"`` renders the shared items table; ``"cards"`` renders
            the card grid (spec 03 F2 toggle).

    Returns:
        Tuple of (content, current_page): content is the pagination controls +
        table or card grid; current_page is the clamped page actually rendered.
    """
    if isinstance(source_keys, str):
        source_keys = [source_keys]

    # Load fresh data each time (60s module cache)
    all_knowledge_data = get_all_knowledge_data()

    all_articles_for_tab = []
    for key in source_keys:
        articles_from_source = all_knowledge_data.get(key, [])
        for article in articles_from_source:
            article["source_display_name"] = article.get("source", KNOWLEDGE_SOURCES_CONFIG[key]["name"])
        all_articles_for_tab.extend(articles_from_source)

    all_articles_for_tab.sort(key=get_sortable_date, reverse=True)

    if not all_articles_for_tab:
        return dbc.Alert(f"No knowledge items available for {display_name}.", color="info"), 1

    if search_term:
        searchable_fields = ["title", "name", "full_name", "summary", "description", "source", "source_display_name"]
        all_articles_for_tab = filter_content(search_term, all_articles_for_tab, searchable_fields)

    if not all_articles_for_tab:
        return dbc.Alert(f"No knowledge items matching '{search_term}'.", color="info"), 1

    page_items, total_pages, page = paginate(all_articles_for_tab, page, MAX_ARTICLES_PER_SOURCE)

    search_id = f"knowledge-search-{'-'.join(source_keys)}"
    controls = pagination_controls(
        "kg",
        page=page,
        total_pages=total_pages,
        showing=len(page_items),
        total=len(all_articles_for_tab),
        id_prefix=search_id,
    )

    if view == "cards":
        # Card grid (spec 03 F2): same page slice, same controls, premium cards
        cards = html.Div([_knowledge_card(article, search_term) for article in page_items], className="row")
        body = html.Div(cards, style={"maxHeight": "800px", "overflowY": "auto", "paddingRight": "15px"})
        if search_term:
            body = html.Div(
                [
                    dbc.Alert(f"🌱 Found {len(all_articles_for_tab)} items matching '{search_term}'", color="success", className="mb-3"),
                    cards,
                ]
            )
        return html.Div([controls, body]), page

    columns = [
        {
            "header": "",
            "cell": lambda article: _save_button(article),
            "td_kwargs": {"style": {"width": "2rem"}},
        },
        {
            "header": "Title",
            "cell": lambda article: title_cell(article, search_term, title_fields=("title", "name", "full_name"), url_fields=("url", "link", "html_url", "website")),
        },
        {"header": "Source", "cell": lambda article: article.get("source_display_name", display_name)},
        {"header": "Date", "cell": lambda article: format_article_date(article)},
    ]
    table = render_items_table(page_items, columns, empty_message=f"No knowledge items matching '{search_term}'.", wrap_scroll=False)

    content = html.Div([table], style={"maxHeight": "800px", "overflowY": "auto", "paddingRight": "15px"})
    if search_term:
        content = html.Div(
            [
                dbc.Alert(f"🌱 Found {len(all_articles_for_tab)} items matching '{search_term}'", color="success", className="mb-3"),
                table,
            ]
        )
    return html.Div([controls, content]), page


def create_knowledge_source_tab_content(source_keys, combined_name=None):
    """Creates the content for a knowledge tab: search input + results container."""
    if isinstance(source_keys, str):
        source_keys = [source_keys]
        source_display_name = KNOWLEDGE_SOURCES_CONFIG[source_keys[0]]["name"]
    else:  # List of source keys (for combined tabs)
        source_display_name = combined_name or "Combined Knowledge"

    tab_search_id = f"knowledge-search-{'-'.join(source_keys)}"

    initial_content, _ = build_knowledge_table(source_keys, display_name=source_display_name)

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
                    dbc.Col(
                        [
                            dbc.Button(
                                KG_VIEW_TOGGLE_LABELS["list"],
                                id=f"{tab_search_id}-view-toggle",
                                color="secondary",
                                size="sm",
                                className="float-end ms-2",
                                title="Alternar entre vista lista y tarjetas (spec 03 F2)",
                            ),
                            dbc.Button(
                                "🔄 Refresh",
                                id=f"{tab_search_id}-refresh",
                                color="secondary",
                                size="sm",
                                className="float-end",
                            ),
                        ],
                        width="auto",
                    ),
                ],
                className="mb-3",
            ),
            html.Div(
                initial_content,
                id=f"{tab_search_id}-results",
                style={"maxHeight": "860px", "overflowY": "auto", "paddingRight": "15px"},
            ),
            dcc.Store(id=f"{tab_search_id}-page", data=1),
            dcc.Store(id=f"{tab_search_id}-view", data="list"),
        ]
    )


def register_knowledge_garden_callbacks(app):
    """Register per-subtab controllers (search + pagination + refresh).

    Every subtab is rendered eagerly, so literal component ids referenced here
    are always present in the layout (no renderer dead-callback risk).
    """
    for tab_def in KNOWLEDGE_TAB_DEFINITIONS:
        search_id = _knowledge_search_id(tab_def)
        keys = tab_def["keys"]
        label = tab_def["label"]

        @app.callback(
            [Output(f"{search_id}-results", "children"), Output(f"{search_id}-page", "data"), Output(f"{search_id}-view", "data"), Output(f"{search_id}-view-toggle", "children")],
            [
                Input(search_id, "value"),
                Input(f"{search_id}-prev", "n_clicks"),
                Input(f"{search_id}-next", "n_clicks"),
                Input(f"{search_id}-refresh", "n_clicks"),
                Input(f"{search_id}-view-toggle", "n_clicks"),
            ],
            [State(f"{search_id}-page", "data"), State(f"{search_id}-view", "data")],
            prevent_initial_call=True,
        )
        def update_knowledge_controller(search_term, _prev, _next, _refresh, _view_toggle, current_page, current_view, keys=keys, label=label, search_id=search_id):
            try:
                ctx = dash.ctx.triggered_id
                page = int(current_page or 1)
                view = current_view if current_view in KG_VIEWS else "list"
                force_refresh = False
                if ctx == f"{search_id}-prev":
                    page -= 1
                elif ctx == f"{search_id}-next":
                    page += 1
                elif ctx == f"{search_id}-refresh":
                    force_refresh = True
                elif ctx == f"{search_id}-view-toggle":
                    # List ↔ cards toggle (spec 03 F2): keep the current page
                    view = "cards" if view == "list" else "list"
                else:
                    # Any search-term change resets to the first page
                    page = 1
                if force_refresh:
                    get_all_knowledge_data(force_refresh=True)
                content, page = build_knowledge_table(keys, search_term=(search_term or "").strip(), display_name=label, page=page, view=view)
                return content, page, view, KG_VIEW_TOGGLE_LABELS[view]
            except Exception as e:
                logger.error(f"Error in knowledge controller for {label}: {e}")
                return dbc.Alert(f"Error searching: {e}", color="danger"), 1, dash.no_update, dash.no_update

        @app.callback(
            Output(search_id, "value", allow_duplicate=True),
            Input(f"{search_id}-clear", "n_clicks"),
            prevent_initial_call=True,
        )
        def clear_knowledge_search(n_clicks):
            if n_clicks:
                return ""
            return dash.no_update

    # Save/unsave toggle (spec 03 F3): one dynamic callback per starred item
    @app.callback(
        Output({"type": "kg-save-btn", "hash": dash.MATCH}, "children"),
        Output({"type": "kg-save-btn", "hash": dash.MATCH}, "color"),
        Output({"type": "kg-save-btn", "hash": dash.MATCH}, "title"),
        Output("kg-saved-results", "children", allow_duplicate=True),
        Input({"type": "kg-save-btn", "hash": dash.MATCH}, "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_saved_item(n_clicks):
        try:
            h = dash.ctx.triggered_id.hash
            # Unstar: the record lives in the saved file. First star: the item
            # comes from the render-time registry (the id only carries a hash).
            record = saved_items.lookup_candidate(h)
            if record is None:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update
            new_state = saved_items.toggle_saved(record)
            updated = _render_saved_subtab().children
            if new_state:
                return "★", "warning", "Quitar de guardados", updated
            return "☆", "outline-secondary", "Guardar para luego", updated
        except Exception as e:
            logger.error(f"Error toggling saved item: {e}")
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # Garden global search across every source (spec 03 F1)
    @app.callback(
        Output("kg-global-results", "children"),
        Input("kg-global-search-input", "value"),
        prevent_initial_call=True,
    )
    def kg_global_search(search_term):
        """Search every knowledge source and group results by source."""
        try:
            term = (search_term or "").strip()
            if not term:
                return dbc.Alert("Escribe un término para comenzar.", color="secondary")

            all_data = get_all_knowledge_data()
            searchable_fields = ["title", "name", "full_name", "summary", "description", "source"]

            groups = []
            total = 0
            for key, articles in all_data.items():
                if not articles:
                    continue
                source_name = KNOWLEDGE_SOURCES_CONFIG.get(key, {}).get("name", key)
                candidates = [dict(a) for a in articles]
                matches = filter_content(term, candidates, searchable_fields)
                if matches:
                    matches.sort(key=get_sortable_date, reverse=True)
                    groups.append((source_name, matches))
                    total += len(matches)

            if not groups:
                return dbc.Alert(f"Sin resultados para '{term}' en la garden.", color="info")

            groups.sort(key=lambda g: len(g[1]), reverse=True)
            summary = dbc.Alert(
                f"🌱 {total} resultados en {len(groups)} fuentes para '{term}'",
                color="success",
                className="mb-3",
            )

            sections = [summary]
            for source_name, matches in groups[:12]:
                sections.append(
                    html.Div(
                        [
                            html.H6(
                                [
                                    f"{source_name} ",
                                    dbc.Badge(len(matches), color="secondary", pill=True),
                                ],
                                className="mt-3 mb-1",
                            ),
                            render_items_table(
                                matches[:15],
                                [
                                    {"header": "Title", "cell": lambda a: title_cell(a, term)},
                                    {"header": "Date", "cell": lambda a: format_article_date(a)},
                                ],
                                empty_message="Sin resultados.",
                                wrap_scroll=False,
                            ),
                        ]
                    )
                )
            return html.Div(sections)
        except Exception as e:
            logger.error(f"Error in KG global search: {e}")
            return dbc.Alert(f"Error en la búsqueda global: {e}", color="danger")


# Main function to render the knowledge garden tab
def render_knowledge_garden_tab():
    """Render the complete knowledge garden tab with all sub-tabs."""
    tab_definitions = KNOWLEDGE_TAB_DEFINITIONS

    tabs_children = [
        dbc.Tab(
            label="⭐ Guardados",
            tab_id="knowledge-tab-saved",
            children=_render_saved_subtab(),
            id="knowledge-tab-saved-container",
        )
    ]

    # 2. Standard Knowledge Sources (Table Layout)
    for tab_def in tab_definitions:
        tab_id = f"knowledge-tab-{tab_def['id']}"
        content = create_knowledge_source_tab_content(tab_def["keys"], combined_name=tab_def["label"])
        tabs_children.append(
            dbc.Tab(
                label=tab_def["label"],
                tab_id=tab_id,
                children=content,
                id=tab_id + "-container",
            )
        )

    # Health dots for every configured source (spec 03 F4)
    health_sources = {cfg["name"]: cfg.get("path", "") for cfg in KNOWLEDGE_SOURCES_CONFIG.values() if cfg.get("path")}

    return html.Div(
        [
            html.H3("Knowledge Garden", className="mb-3"),
            source_health_dots(health_sources, title="Salud de fuentes:"),
            # Garden global search — one query across every source (spec 03 F1)
            dcc.Input(
                id="kg-global-search-input",
                type="text",
                placeholder="🔎 Buscar en todas las fuentes de la garden… (ej. kubernetes rust)",
                debounce=True,
                className="form-control mb-2",
            ),
            html.Div(
                dbc.Alert("Escribe un término para buscar en todas las fuentes a la vez; los resultados se agrupan por fuente.", color="secondary"),
                id="kg-global-results",
                className="mb-3",
            ),
            dbc.Tabs(
                id="knowledge-source-tabs-main",
                children=tabs_children,
                active_tab="knowledge-tab-opensource",
            ),
        ]
    )


if __name__ == "__main__":
    # For testing this component independently
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

    # The render_knowledge_garden_tab now produces the full tabbed layout
    app_test.layout = dbc.Container(
        [
            html.H1("Knowledge Garden Tab Test (Standalone)"),
            render_knowledge_garden_tab(),  # This will include the tabs and initial content
        ],
        fluid=True,
        className="py-4",
    )

    print("Running standalone test for knowledge_garden_tab.py...")
    print(f"Displaying max {MAX_ARTICLES_PER_SOURCE} articles per tab, sorted by date.")
    print("Expected knowledge JSON files relative to project root, e.g., data/futuretools/futuretoolsnews.json")
    print("Check console for warnings about missing files or parsing errors, especially date parsing.")
    app_test.run(debug=True, port=8053)
