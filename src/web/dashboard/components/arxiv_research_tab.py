"""ArXiv Research Dashboard Tab - Simplified Paper Browser
Clean, fast interface for discovering ArXiv research papers
Tabbed interface per category, mirroring the News tab style.
"""

import hashlib
import logging
import sys
import time
from pathlib import Path
from typing import Any

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, html

# Ensure path compatibility
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.services.data_loader import (
    ARXIV_SOURCES_CONFIG,
    get_sortable_date,
    load_data_from_file,
)
from src.services.data_loader import (
    format_article_date as format_article_date_shared,
)
from src.web.dashboard.search_utils import (
    create_search_input,
)
from src.web.dashboard.trend_utils import (
    get_trending_items_map,
    match_item_trend,
    render_trend_badge,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Data Loading ---


def get_all_arxiv_data():
    """Load fresh ArXiv data from all configured category sources."""
    # Simple TTL cache to avoid re-reading files on each tab switch
    # Cache in module state for ~60 seconds
    global _ARXIV_CACHE
    now = time.time()
    try:
        if _ARXIV_CACHE and now - _ARXIV_CACHE.get("ts", 0) < 60:
            return _ARXIV_CACHE["data"]
    except NameError:
        pass

    data = {source_key: load_data_from_file(config["path"]) for source_key, config in ARXIV_SOURCES_CONFIG.items()}
    _ARXIV_CACHE = {"ts": now, "data": data}
    return data


# --- Layout Generation ---

MAX_PAPERS_PER_TAB = 150  # Limit initial papers displayed per category

# Subtab that gets the citations column (enriched by the HF papers ETL:
# OpenAlex primary, CrossRef fallback)
CITATIONS_SOURCE_KEY = "hf_trending"

# Provenance tooltip per citation_source value ("openalex" | "doi" | "title")
_CITATION_SOURCE_TOOLTIPS = {
    "openalex": "OpenAlex citation count · matched by title",
    "doi": "CrossRef citation count · matched by DOI",
    "title": "CrossRef citation count · matched by title",
}


def format_article_date(paper):
    """Wrapper for shared formatting."""
    return format_article_date_shared(paper)


def citation_count_display(paper):
    """Return the paper's citation count as a non-negative int, or None when absent/invalid."""
    count = paper.get("citation_count")
    if isinstance(count, bool) or not isinstance(count, (int, float)) or count < 0:
        return None
    return int(count)


def citation_tooltip_label(source):
    """Return the provenance line for the citation badge tooltip (source-aware)."""
    return _CITATION_SOURCE_TOOLTIPS.get(source, "Citation count")


def render_citation_cell(paper):
    """Render the 📝 Citas table cell for a paper (em dash when no data)."""
    count = citation_count_display(paper)
    if count is None:
        return html.Td("—", className="small text-muted")
    source = str(paper.get("citation_source") or "").strip()
    tooltip_parts = [citation_tooltip_label(source)]
    doi = str(paper.get("citation_doi") or "").strip()
    badge = dbc.Badge(
        f"📝 {count:,}",
        color="secondary",
        pill=True,
        className="fw-normal",
        style={"fontSize": "0.75rem"},
    )
    if doi:
        tooltip_parts.append(f"doi.org/{doi}")
        return html.Td(
            html.A(
                badge,
                href=f"https://doi.org/{doi}",
                target="_blank",
                title=" · ".join(tooltip_parts),
                className="text-decoration-none",
            )
        )
    return html.Td(badge, title=" · ".join(tooltip_parts))


def arxiv_table_header(show_citations):
    """Build the table header row, with the optional 📝 Citas column appended."""
    columns = [html.Th(""), html.Th("Title"), html.Th("Authors"), html.Th("Published Date")]
    if show_citations:
        columns.append(html.Th("📝 Citas"))
    return [html.Thead(html.Tr(columns))]


# Expandable-row pattern ids (spec 10 M2): the ▸ button and the collapsed
# detail share the per-paper hash as their pattern index.
ARXIV_EXPAND_BTN_TYPE = "arxiv-expand-btn"
ARXIV_DETAIL_COLLAPSE_TYPE = "arxiv-detail-collapse"


def _paper_hash(paper: dict) -> str:
    """Stable per-paper key for the expand/collapse pattern-matching ids."""
    key = paper.get("link") or paper.get("id") or paper.get("title", "")
    return hashlib.md5(str(key).encode("utf-8")).hexdigest()


def _render_paper_detail(paper: dict) -> dbc.Card:
    """Detail card revealed by the ▸ expander: full abstract + cluster (spec 10 M2).

    Degrades gracefully when the enrichment fields are missing: papers without
    an abstract or cluster render an explicit placeholder instead of nothing.
    """
    summary = str(paper.get("summary") or "").strip()
    cluster_label = str(paper.get("cluster_label") or "").strip()
    keywords = paper.get("cluster_keywords") or paper.get("extracted_keywords")
    if isinstance(keywords, str):
        keyword_items = [k.strip() for k in keywords.split(",") if k.strip()]
    elif isinstance(keywords, (list, tuple)):
        keyword_items = [str(k) for k in keywords if k]
    else:
        keyword_items = []

    body: list[Any] = []
    if summary:
        body.append(
            html.Div(
                [
                    html.Span("Abstract", className="text-uppercase small text-muted me-2"),
                    html.P(summary, className="mb-2", style={"whiteSpace": "pre-line", "fontSize": "0.85rem"}),
                ]
            )
        )
    if cluster_label or keyword_items:
        cluster_bits = []
        if cluster_label:
            cluster_bits.append(dbc.Badge(f"🧩 {cluster_label}", color="info", pill=True, className="me-1"))
        cluster_bits.extend(dbc.Badge(k, color="secondary", pill=True, className="me-1 fw-normal") for k in keyword_items[:8])
        body.append(html.Div(cluster_bits, className="mb-1"))

    if not body:
        body.append(html.P("Sin abstract ni cluster para este paper.", className="text-muted small mb-0"))

    return dbc.Card(dbc.CardBody(body), color="dark", outline=True, className="m-2")


def _build_paper_rows(papers: list, show_citations: bool, trending_map: dict) -> list:
    """Build the table body rows for a list of papers (spec 10 M2).

    Every paper renders as TWO ``html.Tr``: the regular row (title/authors/
    date[/citations]) preceded by a ▸ expander cell, plus a hidden detail row
    holding the collapsed abstract+cluster card. Shared by the eager layout
    render and the search callback so both stay in sync.

    Args:
        papers: Paper dicts as produced by the ArXiv/HF ETLs.
        show_citations: Append the 📝 Citas column (HF Trending feed only).
        trending_map: Pre-loaded trend records for badge matching.

    Returns:
        Flat list of ``html.Tr`` components for the table body.
    """
    detail_colspan = 4 + (1 if show_citations else 0)
    rows: list = []
    for paper in papers:
        trend_record = match_item_trend(paper, trending_map)
        trend_badge = render_trend_badge(trend_record)

        title = str(paper.get("title", "Unknown Title")).replace("\n", " ").strip()
        url = paper.get("link") or paper.get("id")
        github_url = paper.get("github_html_url")

        authors_list = paper.get("authors", [])
        authors_display = ", ".join(authors_list[:3]) + (f" +{len(authors_list) - 3} more" if len(authors_list) > 3 else "") if isinstance(authors_list, list) else str(authors_list)

        date_display = format_article_date(paper)
        row_class = "trending-item" if trend_record is not None else ""

        title_elements: list[Any] = [
            html.A(title, href=url, target="_blank", className="text-decoration-none fw-bold") if url else title,
        ]

        if github_url:
            title_elements.append(
                html.A(
                    html.I(className="fab fa-github ms-2 text-dark"),
                    href=github_url,
                    target="_blank",
                    title="View GitHub Repository",
                    className="text-decoration-none",
                )
            )

        if trend_badge:
            title_elements.append(html.Span(trend_badge, className="ms-2"))

        expand_btn = html.Button(
            "▸",
            id={"type": ARXIV_EXPAND_BTN_TYPE, "index": _paper_hash(paper)},
            n_clicks=0,
            type="button",
            className="btn btn-sm btn-outline-secondary py-0 px-2",
            title="Mostrar abstract y cluster",
            style={"fontSize": "0.7rem", "lineHeight": 1.4},
        )

        row_cells = [
            html.Td(expand_btn, className="align-middle", style={"width": "2.2rem"}),
            html.Td(title_elements),
            html.Td(authors_display, className="small text-muted"),
            html.Td(date_display, className="small text-muted"),
        ]
        if show_citations:
            row_cells.append(render_citation_cell(paper))

        rows.append(html.Tr(row_cells, className=row_class))
        rows.append(
            html.Tr(
                html.Td(
                    dbc.Collapse(
                        _render_paper_detail(paper),
                        id={"type": ARXIV_DETAIL_COLLAPSE_TYPE, "index": _paper_hash(paper)},
                        is_open=False,
                    ),
                    colSpan=detail_colspan,
                    className="p-0",
                ),
                className="arxiv-detail-row",
            )
        )
    return rows


def create_arxiv_category_tab_content(source_key):
    """Creates the content for a specific ArXiv category tab as a table with search functionality.

    Sorts papers by date before limiting.
    """
    source_display_name = ARXIV_SOURCES_CONFIG[source_key]["name"]
    tab_search_id = f"arxiv-search-{source_key}"

    # Load fresh data each time
    all_arxiv_data = get_all_arxiv_data()
    papers_from_source = all_arxiv_data.get(source_key, [])

    if not papers_from_source:
        return dbc.Alert(f"No papers available for {source_display_name}.", color="info", className="mt-3")

    # Sort all papers by date (descending)
    papers_from_source.sort(key=get_sortable_date, reverse=True)

    # Citations column only exists for the CrossRef-enriched HF Trending feed
    show_citations = source_key == CITATIONS_SOURCE_KEY
    table_header = arxiv_table_header(show_citations)

    # Load trend data
    trending_map = get_trending_items_map()

    # Table body: one visible row + one expandable detail row per paper (spec 10 M2)
    table_body_rows = _build_paper_rows(papers_from_source[:MAX_PAPERS_PER_TAB], show_citations, trending_map)

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

    # Return search input and table container
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        # Search input
                        create_search_input(
                            input_id=tab_search_id,
                            placeholder=f"Filter {source_display_name} by title, author, or abstract...",
                            clear_button=True,
                        ),
                        width=True,
                    ),
                ],
                className="mb-3 mt-3 align-items-center",
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


def register_arxiv_callbacks(app):
    """Register search callbacks for all ArXiv tabs."""
    # Get all unique search IDs from the source config
    search_ids = [f"arxiv-search-{key}" for key in ARXIV_SOURCES_CONFIG]

    for search_id in search_ids:

        @app.callback(
            Output(f"{search_id}-results", "children"),
            [Input(search_id, "value")],
        )
        def update_arxiv_search(search_term, current_search_id=search_id):
            """Update ArXiv display based on search term."""
            try:
                # 1. Determine Source Key from Search ID
                source_key = current_search_id.replace("arxiv-search-", "")

                # 2. Fetch Fresh Data (CACHE HIT usually)
                all_arxiv_data = get_all_arxiv_data()
                papers_data = all_arxiv_data.get(source_key, [])

                if not papers_data:
                    return dbc.Alert("No data available for this category.", color="warning")

                # 3. Sort
                papers_data.sort(key=get_sortable_date, reverse=True)

                # 4. Filter (Search)
                if search_term:
                    search_lower = search_term.lower()
                    filtered_papers = []
                    for p in papers_data:
                        title = str(p.get("title", "")).lower()
                        summary = str(p.get("summary", "")).lower()
                        authors = str(p.get("authors", "")).lower()
                        if search_lower in title or search_lower in summary or search_lower in authors:
                            filtered_papers.append(p)
                else:
                    filtered_papers = papers_data[:MAX_PAPERS_PER_TAB]  # Limit initial view

                # Create table for filtered results (citations column for the HF feed)
                show_citations = source_key == CITATIONS_SOURCE_KEY
                table_header = arxiv_table_header(show_citations)

                # Load trend data for rendering badges
                trending_map = get_trending_items_map()

                # Table body: visible row + expandable detail row per paper (spec 10 M2)
                table_body_rows = _build_paper_rows(filtered_papers, show_citations, trending_map)

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
                        f"📰 Found {len(filtered_papers)} papers matching '{search_term}'",
                        color="success",
                        className="mb-3 mt-3",
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
                logger.error(f"Error in ArXiv search callback for {current_search_id}: {e}")
                return dbc.Alert(f"Error filtering papers: {e}", color="danger")

        # Clear search callback
        @app.callback(
            Output(search_id, "value", allow_duplicate=True),
            Input(f"{search_id}-clear", "n_clicks"),
            prevent_initial_call=True,
        )
        def clear_arxiv_search(n_clicks):
            """Clear search input."""
            if n_clicks:
                return ""
            return dash.no_update

    # Expandable rows (spec 10 M2): one pattern-matching callback serves every
    # paper's ▸ expander — buttons and collapses share the per-paper hash as
    # their pattern index, so each pair toggles independently.
    @app.callback(
        Output({"type": ARXIV_DETAIL_COLLAPSE_TYPE, "index": dash.MATCH}, "is_open"),
        Input({"type": ARXIV_EXPAND_BTN_TYPE, "index": dash.MATCH}, "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_arxiv_paper_detail(n_clicks):
        """Toggle the paper's collapsed detail row (odd clicks open)."""
        return bool(n_clicks % 2)


# Main function to render the ArXiv tab
def render_arxiv_research_tab():
    """Render the complete ArXiv research tab with all category sub-tabs."""

    tabs_children = []

    # Order of tabs to display (HF trending first — the community-ranked feed,
    # then All, then categories)
    ordered_keys = [
        "hf_trending",
        "all_arxiv",
        "machine_learning",
        "computer_vision",
        "nlp",
        "neural_networks",
        "robotics",
        "reinforcement_learning",
        "security",
        "systems_cloud",
        "quantum",
        "data_engineering",
    ]

    for key in ordered_keys:
        if key in ARXIV_SOURCES_CONFIG:
            config = ARXIV_SOURCES_CONFIG[key]
            tab_id = f"arxiv-tab-{key}"
            content = create_arxiv_category_tab_content(key)
            tabs_children.append(
                dbc.Tab(
                    label=config["name"],
                    tab_id=tab_id,
                    children=content,
                    id=tab_id + "-container",
                )
            )

    return html.Div(
        [
            html.H3([html.I(className="fas fa-graduation-cap me-2 text-primary"), "ArXiv Research"], className="mb-3"),
            dbc.Tabs(
                id="arxiv-category-tabs-main",
                children=tabs_children,
            ),
        ]
    )
