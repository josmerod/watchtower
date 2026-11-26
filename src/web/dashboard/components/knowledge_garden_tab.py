import logging
import re
from functools import partial
from html import unescape
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
    parse_date,
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
def _kg_sort_key(article: dict) -> Any:
    """Sort key of a knowledge item: the date taken at load time when there is one."""
    return article["_kg_sort"] if "_kg_sort" in article else get_sortable_date(article)


class KnowledgeGardenRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for one knowledge garden source.

    ``get()`` returns the items newest first, each of them a copy carrying
    ``_kg_sort`` (the sort date) and ``source_display_name``. They are computed
    once per cache period here: the Podcasts source alone holds thousands of
    items, and parsing a date per item on every render cost ~0.4 s (T-136).
    """

    def __init__(self, data_path: str, source_name: str = ""):
        """Initialize knowledge garden repository.

        Args:
            data_path: Path to knowledge data file
            source_name: Display source of an item that carries none
        """
        super().__init__(
            data_path=Path(data_path),
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )
        self.source_name = source_name

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform JSON data into knowledge items, newest first.

        Args:
            raw_data: Raw JSON data

        Returns:
            List of knowledge item dictionaries
        """
        if isinstance(raw_data, list):
            items: list[Any] = raw_data
        elif isinstance(raw_data, dict):
            # Handle cases where JSON might be a dict with a key containing the list
            if "articles" in raw_data and isinstance(raw_data["articles"], list):
                items = raw_data["articles"]
            elif "items" in raw_data and isinstance(raw_data["items"], list):
                items = raw_data["items"]
            # Single item
            elif all(k in raw_data for k in ["title", "url"]):
                items = [raw_data]
            else:
                items = []
        else:
            items = []
        fallback_name = self.source_name or self.data_path.stem
        enriched = [{**item, "_kg_sort": get_sortable_date(item), "source_display_name": item.get("source", fallback_name)} for item in items if isinstance(item, dict)]
        enriched.sort(key=_kg_sort_key, reverse=True)
        return enriched


# One repository per configured source, keyed like KNOWLEDGE_SOURCES_CONFIG: a
# new source needs a config entry and a subtab, nothing else in this module.
_repositories: dict[str, KnowledgeGardenRepository] = {key: KnowledgeGardenRepository(cfg["path"], cfg["name"]) for key, cfg in KNOWLEDGE_SOURCES_CONFIG.items()}


# load_knowledge_from_file removed (unused/dead code)


def _load_all_knowledge_data(force_refresh: bool = False) -> dict[str, list[dict[str, Any]]]:
    """Read every configured source through its repository (newest first).

    Args:
        force_refresh: Bypass the repositories' one-hour cache too (Refresh).
    """
    data = {}
    for source_key, repo in _repositories.items():
        try:
            data[source_key] = repo.get(force_refresh=force_refresh) or []
        except Exception:
            # Gracefully handle missing/corrupt data files (e.g. ETL not yet run)
            data[source_key] = []
    return data


# Module cache via the shared TTL helper (spec 15 M2 — no NameError antipattern)
_knowledge_cache = TTLDataCache(ttl_seconds=60)


def get_all_knowledge_data(force_refresh: bool = False):
    """Load knowledge data from all configured sources (60s module cache).

    A forced refresh also bypasses the per-source repositories (1h cache);
    without that the Refresh button kept serving the same file for an hour.
    """
    loader = _load_all_knowledge_data
    if force_refresh:
        loader = partial(_load_all_knowledge_data, force_refresh=True)
    return _knowledge_cache.get(loader, force_refresh=force_refresh)


# --- Helper function to parse dates ---
# parse_date logic removed (using shared parse_date)


# --- Layout Generation ---

MAX_ARTICLES_PER_SOURCE = 50  # Limit number of articles displayed per source initially

# Single source of truth for the subtab list; search input IDs are derived
# from it so every subtab's search box is guaranteed to be wired. Typed
# explicitly: ``keys`` is a str or a list, and mypy would join both into
# ``object``.
KNOWLEDGE_TAB_DEFINITIONS: list[dict[str, Any]] = [
    {"label": "LessWrong", "keys": "lesswrong", "id": "lw"},
    {"label": "Good Devs", "keys": "gooddevs", "id": "gd"},
    {"label": "Lobsters", "keys": "lobsters", "id": "lobsters"},
    {"label": "Podcasts", "keys": "podcasts", "id": "pod"},
    {"label": "Reddit Tech", "keys": "reddit_tech", "id": "reddit_tech"},
    {"label": "HN Ask", "keys": "hackernews_ask", "id": "hn_ask"},
    {"label": "Product Hunt", "keys": "product_hunt", "id": "ph"},
    # Developer community tab
    {"label": "Dev.to", "keys": "devto", "id": "devto"},
    {"label": "HypeURLs", "keys": "hypeurls", "id": "hypeurls"},
    {"label": "Open Source", "keys": ["opensource", "reddit_opensource"], "id": "opensource"},
    {"label": "Substack", "keys": "substack", "id": "substack"},
    {"label": "RSS Feeds", "keys": "rss_feeds", "id": "rss_feeds"},
]

# The subtab bar. Its active_tab is read by one dispatcher that marks the
# open subtab as activated; only that subtab's controller listens for it.
# With the bar as an input of every controller, each switch ran all twelve
# (T-136).
KG_TABS_ID = "knowledge-source-tabs-main"

# Star clicks. The stars are plain buttons, not callback inputs: Dash runs a
# pattern-matching callback once per button inserted into the page, so
# building a subtab's table sent fifty no-op star requests. Instead
# assets/js/kg_state.js flips the star, writes the request store, and the
# toggle callback persists the change and answers through the outcome
# element, which the script applies to every star showing that item.
KG_SAVE_REQUEST_ID = "kg-save-request"
KG_SAVE_OUTCOME_ID = "kg-save-outcome"

# The search filters on the server: wait for a pause in typing instead of a
# callback (and a whole page of rows) per keystroke.
KG_SEARCH_DEBOUNCE_MS = 400


def _knowledge_search_id(tab_def: dict) -> str:
    """Derive the search input ID for a tab definition (layout and callbacks agree)."""
    keys = tab_def["keys"]
    if isinstance(keys, str):
        return f"knowledge-search-{keys}"
    return f"knowledge-search-{'-'.join(keys)}"


def _knowledge_tab_id(tab_def: dict) -> str:
    """The subtab's id on the subtab bar (the value ``active_tab`` reports)."""
    return f"knowledge-tab-{tab_def['id']}"


# format_article_date removed (using shared logic)
def format_article_date(article):
    """Wrapper for shared formatting."""
    return format_article_date_shared(article)


# --- NUEVO badge plumbing (T-085) ---
# Rows/cards carry a machine-readable ISO date in data-kg-date so
# assets/js/kg_state.js can badge items newer than the previous visit
# (same UX as the Videos tab, spec 04 F5). Field order mirrors
# get_sortable_date so sort order and badges always agree.
_KG_DATE_FIELDS = (
    "published_at",
    "published",
    "published_date",
    "publication_date",
    "created_at",
    "created_utc",
    "updated_at",
    "updated",
    "time",
    "pubDate",
    "release_date",
    "fetched_at",
    "extracted_at",
    "first_seen",
    "date",
)


def _kg_date_iso(article: dict) -> str:
    """Best-effort ISO 8601 timestamp for the client-side NUEVO badge (T-085).

    Parses the first date-ish field (same order as ``get_sortable_date``) and
    falls back to the raw string; ``assets/js/kg_state.js`` skips values that
    ``Date.parse`` rejects. Empty string for undated items — never badged.
    """
    raw = next((article.get(f) for f in _KG_DATE_FIELDS if article.get(f)), None)
    if not raw:
        return ""
    parsed = parse_date(raw)
    return parsed.isoformat() if parsed else str(raw)


def _tag_rows_with_kg_dates(table: Any, items: list[dict]) -> None:
    """Attach ``data-kg-date`` to each table body row, in item order (T-085).

    ``render_items_table`` builds plain ``html.Tr`` rows with no per-row
    attributes, and dbc components reject ``data-*`` wildcards — so the
    cleanest injection point is post-construction (Dash serializes data-*
    wildcards set this way; verified in Tests/unit/test_kg_new_badge.py).
    """
    for child in getattr(table, "children", None) or []:
        if isinstance(child, html.Tbody):
            # strict=False on purpose: badge tagging must never break rendering
            # if the shared table builder's structure ever changes.
            for row, article in zip(child.children or [], items, strict=False):
                setattr(row, "data-kg-date", _kg_date_iso(article))


# Same classes as the shared dbc star, so both look alike.
_KG_STAR_CLASS = "ms-1 p-0 border-0 btn btn-sm"


def _save_button(article: dict) -> html.Button:
    """Star/unstar button for a knowledge item, flipped by ``kg_state.js``.

    A plain ``html.Button`` carrying the item hash in ``data-kg-hash`` and
    its state in ``data-kg-saved``; see ``KG_SAVE_REQUEST_ID`` for why it is
    not a callback input.
    """
    h = saved_items.register_candidate(article, tab="knowledge_garden")
    saved = saved_items.is_saved(h)
    star = html.Button(
        "★" if saved else "☆",
        className=f"{_KG_STAR_CLASS} {'btn-warning' if saved else 'btn-outline-secondary'}",
        title="Quitar de guardados" if saved else "Guardar para luego",
    )
    # Set after construction like the NUEVO dates above: Dash serializes
    # data-* wildcards added this way.
    setattr(star, "data-kg-hash", h)
    setattr(star, "data-kg-saved", "1" if saved else "0")
    return star


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

# HTML comments and tags. Reddit summaries arrive as the post's raw HTML
# (``<!-- SC_OFF --><div class="md"><p>…``), which the cards used to show as is.
# A tag starts with a letter, so "a < b" is left alone.
_HTML_COMMENT_OR_TAG = re.compile(r"<!--.*?-->|</?[A-Za-z][^>]*>", re.DOTALL)


def _plain_text(value: str) -> str:
    """Turn a snippet that carries HTML markup or entities into plain text."""
    if "<" not in value and "&" not in value:
        return value
    text = _HTML_COMMENT_OR_TAG.sub(" ", value) if "<" in value else value
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _knowledge_card(article: dict, search_term: str = "") -> dbc.Col:
    """Build one minimalist result card (title, source, snippet, link + star).

    Mirrors the videos-tab card pattern (2-line clamped title, muted metadata)
    so both grids feel like the same design language.
    """
    title = next((str(article.get(f)) for f in ("title", "name", "full_name") if article.get(f)), "No Title")
    url = next((article.get(f) for f in ("url", "link", "html_url", "website") if article.get(f)), None)
    snippet = next((_plain_text(str(article.get(f))) for f in _KG_SNIPPET_FIELDS if article.get(f)), "")

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

    # html.Div wrapper carries the data-* attribute (dbc components don't
    # accept wildcards); kg_state.js keys on it for the NUEVO badge (T-085).
    card_wrapper = html.Div(
        dbc.Card(dbc.CardBody(body), className="h-100"),
        className="h-100",
    )
    setattr(card_wrapper, "data-kg-date", _kg_date_iso(article))
    return dbc.Col(
        card_wrapper,
        xs=12,
        sm=6,
        md=4,
        className="mb-3",
    )


def _sorted_articles(source_keys) -> list[dict[str, Any]]:
    """Return the items of one or more sources, newest first."""
    if isinstance(source_keys, str):
        source_keys = [source_keys]
    all_knowledge_data = get_all_knowledge_data()
    articles: list[dict[str, Any]] = []
    for key in source_keys:
        articles.extend(all_knowledge_data.get(key, []))
    articles.sort(key=_kg_sort_key, reverse=True)
    return articles


def _knowledge_view(source_keys, search_term: str = "", display_name: str = "Knowledge", page: int = 1, view: str = "list") -> dict[str, Any]:
    """Build one page of a subtab: its content and what the pagination bar shows.

    Args:
        view: ``"list"`` renders the shared items table; ``"cards"`` renders
            the card grid (spec 03 F2 toggle).

    Returns:
        Dict with ``content`` (table, card grid or an alert), ``page`` (the
        clamped page actually rendered), ``showing``, ``total`` and
        ``total_pages`` of the filtered items.
    """
    all_articles_for_tab = _sorted_articles(source_keys)

    empty: dict[str, Any] = {"showing": 0, "total": 0, "total_pages": 0}
    if not all_articles_for_tab:
        return {**empty, "page": 1, "content": dbc.Alert(f"No knowledge items available for {display_name}.", color="info")}

    if search_term:
        searchable_fields = ["title", "name", "full_name", "summary", "description", "source", "source_display_name"]
        all_articles_for_tab = filter_content(search_term, all_articles_for_tab, searchable_fields)

    if not all_articles_for_tab:
        return {**empty, "page": 1, "content": dbc.Alert(f"No knowledge items matching '{search_term}'.", color="info")}

    page_items, total_pages, page = paginate(all_articles_for_tab, page, MAX_ARTICLES_PER_SOURCE)
    # The items come from a cache every subtab shares: they are tagged on copies.
    page_items = [article if "source_display_name" in article else {**article, "source_display_name": article.get("source", display_name)} for article in page_items]
    built = {"page": page, "showing": len(page_items), "total": len(all_articles_for_tab), "total_pages": total_pages}
    found_alert = dbc.Alert(f"🌱 Found {len(all_articles_for_tab)} items matching '{search_term}'", color="success", className="mb-3") if search_term else None

    if view == "cards":
        # Card grid (spec 03 F2): same page slice as the list, premium cards
        body = html.Div([_knowledge_card(article, search_term) for article in page_items], className="row")
    else:
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
        body = render_items_table(page_items, columns, empty_message=f"No knowledge items matching '{search_term}'.", wrap_scroll=False)
        _tag_rows_with_kg_dates(body, page_items)  # data-kg-date for NUEVO badges (T-085)

    if found_alert:
        # The results container already scrolls; the summary stays above the rows.
        return {**built, "content": html.Div([found_alert, body])}
    return {**built, "content": html.Div(body, style={"maxHeight": "800px", "overflowY": "auto", "paddingRight": "15px"})}


def build_knowledge_table(source_keys, search_term: str = "", display_name: str = "Knowledge", page: int = 1, view: str = "list"):
    """Build the knowledge items list or card grid, filtered, highlighted and paginated.

    Returns:
        Tuple of (content, current_page): the page's table or card grid
        (without the pagination bar), and the clamped page actually rendered.
    """
    built = _knowledge_view(source_keys, search_term=search_term, display_name=display_name, page=page, view=view)
    return built["content"], built["page"]


def _page_info(built: dict[str, Any]) -> str:
    """Text of the pagination bar for a built page."""
    if not built["total"]:
        return "Sin elementos."
    return f"Showing {built['showing']} of {built['total']} · Page {built['page']} of {built['total_pages']}"


def _pending_dates(source_keys) -> html.Span:
    """Hidden list of a subtab's first-page dates, for the NUEVO counter.

    The table of a subtab that was not opened yet is not in the page, so
    kg_state.js cannot count its new items from rows. The list carries exactly
    the dates those rows would carry, in the same order, and is replaced
    together with the table.
    """
    dates = ",".join(date for date in (_kg_date_iso(article) for article in _sorted_articles(source_keys)[:MAX_ARTICLES_PER_SOURCE]) if date)
    placeholder = html.Span(hidden=True)
    setattr(placeholder, "data-kg-dates", dates)
    return placeholder


def create_knowledge_source_tab_content(source_keys, combined_name=None):
    """Search bar, pagination bar and an empty results container.

    The table itself is built by the controller when the subtab is first
    opened: building all of them up front sent ~600 KiB of layout and took
    half a second for the one subtab in view (T-136). Everything the
    controller takes as an input is rendered here, because Dash refuses to
    fire a callback whose input is not in the page.
    """
    if isinstance(source_keys, str):
        source_keys = [source_keys]
        source_display_name = KNOWLEDGE_SOURCES_CONFIG[source_keys[0]]["name"]
    else:  # List of source keys (for combined tabs)
        source_display_name = combined_name or "Combined Knowledge"

    tab_search_id = f"knowledge-search-{'-'.join(source_keys)}"

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        create_search_input(
                            input_id=tab_search_id,
                            placeholder=f"Filter {source_display_name} by term...",
                            clear_button=True,
                            debounce=KG_SEARCH_DEBOUNCE_MS,
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
                ],  # no bottom margin: the search box brings its own, and the pagination bar follows
            ),
            pagination_controls("kg", page=0, total_pages=0, showing=0, total=0, id_prefix=tab_search_id, info_id=f"{tab_search_id}-page-info", label="Cargando…"),
            html.Div(
                [_pending_dates(source_keys), html.Div("Cargando…", className="text-muted small")],
                id=f"{tab_search_id}-results",
                style={"maxHeight": "860px", "overflowY": "auto", "paddingRight": "15px"},
            ),
            dcc.Store(id=f"{tab_search_id}-page"),  # empty until the table is first built
            dcc.Store(id=f"{tab_search_id}-view", data="list"),
            # Set to 1 by the dispatcher when the subtab is first opened.
            dcc.Store(id=f"{tab_search_id}-activate", data=0),
        ]
    )


def _kg_activation(active_tab: str | None) -> tuple[Any, ...]:
    """Activation values for the subtab stores, in ``KNOWLEDGE_TAB_DEFINITIONS`` order.

    1 for the open subtab, ``no_update`` for the rest: only the store that
    changes triggers its controller, so a subtab that is opened again keeps
    the table it already has.
    """
    return tuple(1 if _knowledge_tab_id(tab_def) == active_tab else dash.no_update for tab_def in KNOWLEDGE_TAB_DEFINITIONS)


def _kg_controller_plan(triggered_id, activated, current_page, current_view, search_id: str) -> tuple[int, str, bool] | None:
    """Decide what one subtab controller does: (page, view, force_refresh), or None.

    A subtab's table is built lazily, when the dispatcher first marks it as
    activated: until then its page store is empty and the controller stays
    idle. Afterwards only its own controls act. Opening another subtab does
    not reach this controller, and coming back leaves the table as it was;
    Refresh reloads it (T-136).
    """
    if not current_page:
        return (1, "list", False) if activated else None
    page = int(current_page)
    view = current_view if current_view in KG_VIEWS else "list"
    if triggered_id == f"{search_id}-prev":
        return page - 1, view, False
    if triggered_id == f"{search_id}-next":
        return page + 1, view, False
    if triggered_id == f"{search_id}-refresh":
        return page, view, True
    if triggered_id == f"{search_id}-view-toggle":
        return page, ("cards" if view == "list" else "list"), False
    if triggered_id == search_id:
        return 1, view, False  # a new search term restarts from the first page
    return None


def toggle_saved_item(request: Any) -> tuple[Any, Any]:
    """Apply a star click sent by ``kg_state.js``; answer with the state on disk.

    Returns the new content of the "⭐ Guardados" subtab and the outcome text
    (``n|hash|saved``) that the script applies to every star showing the
    item, which undoes its optimistic flip when the change did not stick.

    Args:
        request: ``{"hash": ..., "n": ...}`` as written to the request store.
    """
    if not isinstance(request, dict) or not request.get("hash"):
        return dash.no_update, dash.no_update
    h = request["hash"]
    try:
        # Unstar: the record lives in the saved file. First star: the item
        # comes from the render-time registry (the request only carries a
        # hash). An item the registry no longer knows (the server restarted
        # since the page was rendered) toggles nothing.
        record = saved_items.lookup_candidate(h)
        saved = saved_items.toggle_saved(record) if record is not None else saved_items.is_saved(h)
    except Exception:
        logger.exception(f"Error toggling saved item {h}")
        saved = saved_items.is_saved(h)
    return _render_saved_subtab().children, f"{request.get('n')}|{h}|{int(saved)}"


def register_knowledge_garden_callbacks(app):
    """Register the subtab controllers, the dispatcher that activates a subtab and the star toggle.

    Every subtab's search bar and pagination bar are rendered eagerly, so the
    literal component ids used here as inputs are in the layout before the
    table exists; Dash refuses to fire a callback whose input is not in the
    page.
    """
    idle = (dash.no_update,) * 7
    for tab_def in KNOWLEDGE_TAB_DEFINITIONS:
        search_id = _knowledge_search_id(tab_def)
        keys = tab_def["keys"]
        label = tab_def["label"]

        @app.callback(
            [
                Output(f"{search_id}-results", "children"),
                Output(f"{search_id}-page", "data"),
                Output(f"{search_id}-view", "data"),
                Output(f"{search_id}-view-toggle", "children"),
                Output(f"{search_id}-page-info", "children"),
                Output(f"{search_id}-prev", "disabled"),
                Output(f"{search_id}-next", "disabled"),
            ],
            [
                Input(search_id, "value"),
                Input(f"{search_id}-prev", "n_clicks"),
                Input(f"{search_id}-next", "n_clicks"),
                Input(f"{search_id}-refresh", "n_clicks"),
                Input(f"{search_id}-view-toggle", "n_clicks"),
                Input(f"{search_id}-activate", "data"),
            ],
            [State(f"{search_id}-page", "data"), State(f"{search_id}-view", "data")],
            # Idle on insertion: the table is built when the dispatcher
            # writes the activate store, not when the subtab bar appears.
            prevent_initial_call=True,
        )
        def update_knowledge_controller(search_term, _prev, _next, _refresh, _view_toggle, activated, current_page, current_view, keys=keys, label=label, search_id=search_id, idle=idle):
            try:
                plan = _kg_controller_plan(dash.ctx.triggered_id, activated, current_page, current_view, search_id)
                if plan is None:
                    return idle
                page, view, force_refresh = plan
                if force_refresh:
                    get_all_knowledge_data(force_refresh=True)
                built = _knowledge_view(keys, search_term=(search_term or "").strip(), display_name=label, page=page, view=view)
                return built["content"], built["page"], view, KG_VIEW_TOGGLE_LABELS[view], _page_info(built), built["page"] <= 1, built["page"] >= built["total_pages"]
            except Exception as e:
                logger.error(f"Error in knowledge controller for {label}: {e}")
                return dbc.Alert(f"Error searching: {e}", color="danger"), 1, dash.no_update, dash.no_update, dash.no_update, True, True

        @app.callback(
            Output(search_id, "value", allow_duplicate=True),
            Input(f"{search_id}-clear", "n_clicks"),
            prevent_initial_call=True,
        )
        def clear_knowledge_search(n_clicks):
            if n_clicks:
                return ""
            return dash.no_update

    # One callback listens to the subtab bar and marks the open subtab as
    # activated; only that subtab's controller runs.
    @app.callback(
        [Output(f"{_knowledge_search_id(tab_def)}-activate", "data") for tab_def in KNOWLEDGE_TAB_DEFINITIONS],
        Input(KG_TABS_ID, "active_tab"),
        # Runs on insertion too, to activate the subtab that is open when the
        # tab first renders.
        prevent_initial_call=False,
    )
    def dispatch_kg_activation(active_tab):
        return _kg_activation(active_tab)

    # Save/unsave toggle (spec 03 F3): one callback for every star of the tab
    @app.callback(
        [Output("kg-saved-results", "children"), Output(KG_SAVE_OUTCOME_ID, "children")],
        Input(KG_SAVE_REQUEST_ID, "data"),
        prevent_initial_call=True,
    )
    def toggle_saved_item_callback(request):
        return toggle_saved_item(request)

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
        tab_id = _knowledge_tab_id(tab_def)
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
            html.H3(
                [
                    "Knowledge Garden ",
                    # Filled client-side by assets/js/kg_state.js (T-085):
                    # "N NUEVO" chip counting items newer than the last visit.
                    html.Span(
                        "",
                        id="kg-new-counter",
                        className="ms-2 align-middle",
                        style={"fontSize": "0.8rem", "verticalAlign": "middle"},
                    ),
                ],
                className="mb-3",
            ),
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
            # Star clicks: written by assets/js/kg_state.js, answered below.
            dcc.Store(id=KG_SAVE_REQUEST_ID),
            html.Span(id=KG_SAVE_OUTCOME_ID, hidden=True),
            dbc.Tabs(
                id=KG_TABS_ID,
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
