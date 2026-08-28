"""ArXiv Research Dashboard Tab - Simplified Paper Browser
Clean, fast interface for discovering ArXiv research papers
Tabbed interface per category, mirroring the News tab style.
"""

import logging
import sys
import time
from pathlib import Path

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
    global _ARXIV_CACHE  # type: ignore
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

# Subtab that gets the CrossRef citations column (enriched by the HF papers ETL)
CITATIONS_SOURCE_KEY = "hf_trending"


def format_article_date(paper):
    """Wrapper for shared formatting."""
    return format_article_date_shared(paper)


def citation_count_display(paper):
    """Return the paper's citation count as a non-negative int, or None when absent/invalid."""
    count = paper.get("citation_count")
    if isinstance(count, bool) or not isinstance(count, (int, float)) or count < 0:
        return None
    return int(count)


def render_citation_cell(paper):
    """Render the 📝 Citas table cell for a paper (em dash when no data)."""
    count = citation_count_display(paper)
    if count is None:
        return html.Td("—", className="small text-muted")
    source = str(paper.get("citation_source") or "").strip()
    tooltip_parts = ["CrossRef citation count"]
    if source:
        tooltip_parts.append(f"matched by {source}")
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
    columns = [html.Th("Title"), html.Th("Authors"), html.Th("Published Date")]
    if show_citations:
        columns.append(html.Th("📝 Citas"))
    return [html.Thead(html.Tr(columns))]


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

    # Create table body with robust field fallbacks
    table_body_rows = []
    for _i, paper in enumerate(papers_from_source[:MAX_PAPERS_PER_TAB]):
        # Match by id, url, source or trending term in the title
        trend_record = match_item_trend(paper, trending_map)
        trend_badge = render_trend_badge(trend_record)

        # Title
        title = paper.get("title", "Unknown Title")
        title = title.replace("\n", " ").strip()

        # Original Link
        url = paper.get("link") or paper.get("id")

        # GitHub Link (if enriched by ETL)
        github_url = paper.get("github_html_url")

        # Authors
        authors_list = paper.get("authors", [])
        authors_display = ", ".join(authors_list[:3]) + (f" +{len(authors_list) - 3} more" if len(authors_list) > 3 else "") if isinstance(authors_list, list) else str(authors_list)

        # Date
        date_display = format_article_date(paper)

        # Add trending class for styling
        row_class = "trending-item" if trend_record is not None else ""

        title_elements = [
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

        row_cells = [
            html.Td(title_elements),
            html.Td(authors_display, className="small text-muted"),
            html.Td(date_display, className="small text-muted"),
        ]
        if show_citations:
            row_cells.append(render_citation_cell(paper))

        table_body_rows.append(
            html.Tr(
                row_cells,
                className=row_class,
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

                table_body_rows = []
                for _i, paper in enumerate(filtered_papers):
                    # Match by id, url, source or trending term in the title
                    trend_record = match_item_trend(paper, trending_map)
                    trend_badge = render_trend_badge(trend_record)

                    title = str(paper.get("title", "Unknown Title")).replace("\n", " ").strip()
                    url = paper.get("link") or paper.get("id")
                    github_url = paper.get("github_html_url")

                    authors_list = paper.get("authors", [])
                    authors_display = ", ".join(authors_list[:3]) + (f" +{len(authors_list) - 3} more" if len(authors_list) > 3 else "") if isinstance(authors_list, list) else str(authors_list)

                    date_display = format_article_date(paper)

                    row_class = "trending-item" if trend_record is not None else ""

                    title_elements = [
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

                    row_cells = [
                        html.Td(title_elements),
                        html.Td(authors_display, className="small text-muted"),
                        html.Td(date_display, className="small text-muted"),
                    ]
                    if show_citations:
                        row_cells.append(render_citation_cell(paper))

                    table_body_rows.append(
                        html.Tr(
                            row_cells,
                            className=row_class,
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
