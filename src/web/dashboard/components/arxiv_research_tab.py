"""ArXiv Research Dashboard Tab - Simplified Paper Browser
Clean, fast interface for discovering ArXiv research papers
Tabbed interface per category, mirroring the News tab style.
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, html

# Ensure path compatibility
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.services.data_loader import (
    ARXIV_SOURCES_CONFIG,
    format_article_date as format_article_date_shared,
    get_sortable_date,
    load_data_from_file,
    parse_date,
)
from src.web.dashboard.search_utils import (
    create_search_input,
    filter_content,
    get_common_searchable_fields,
)
from src.web.dashboard.trend_utils import (
    get_trending_items_map,
    is_item_trending,
    render_trend_badge,
)
from src.web.dashboard.utils import get_data_path

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


def format_article_date(paper):
    """Wrapper for shared formatting."""
    return format_article_date_shared(paper)


def create_arxiv_category_tab_content(source_key):
    """Creates the content for a specific ArXiv category tab as a table with search functionality.
    
    Sorts papers by date before limiting.
    """
    source_display_name = ARXIV_SOURCES_CONFIG[source_key]["name"]
    tab_search_id = f"arxiv-search-{source_key}"

    # Load fresh data each time
    all_arxiv_data = get_all_arxiv_data()
    papers_from_source = all_arxiv_data.get(source_key, [])
    
    # Store all papers in a hidden div for search filtering
    papers_data_store = html.Div(
        papers_from_source[:MAX_PAPERS_PER_TAB],
        id=f"{tab_search_id}-data",
        style={"display": "none"},
    )

    if not papers_from_source:
        return dbc.Alert(f"No papers available for {source_display_name}.", color="info", className="mt-3")

    # Sort all papers by date (descending)
    papers_from_source.sort(key=get_sortable_date, reverse=True)

    # Create table header
    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Title"),
                    html.Th("Authors"),
                    html.Th("Published Date"),
                ]
            )
        )
    ]

    # Load trend data
    trending_map = get_trending_items_map()

    # Create table body with robust field fallbacks
    table_body_rows = []
    for i, paper in enumerate(papers_from_source[:MAX_PAPERS_PER_TAB]):
        # Check trend status
        is_trending = is_item_trending(paper, trending_map)
        
        # Use primary category for trend checking if available
        primary_cat = paper.get("categories", [""])[0] if isinstance(paper.get("categories"), list) and paper.get("categories") else ""
        trend_badge = render_trend_badge(trending_map.get(f"category:{primary_cat}") or trending_map.get(paper.get("id"))) if is_trending else None

        # Title
        title = paper.get("title", "Unknown Title")
        title = title.replace("\n", " ").strip()
        
        # Original Link
        url = paper.get("link") or paper.get("id")
        
        # GitHub Link (if enriched by ETL)
        github_url = paper.get("github_html_url")
        
        # Authors
        authors_list = paper.get("authors", [])
        authors_display = ", ".join(authors_list[:3]) + (f" +{len(authors_list)-3} more" if len(authors_list) > 3 else "") if isinstance(authors_list, list) else str(authors_list)
        
        # Date
        date_display = format_article_date(paper)

        # Add trending class for styling
        row_class = "trending-item" if is_trending else ""

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

        table_body_rows.append(
            html.Tr(
                [
                    html.Td(title_elements),
                    html.Td(authors_display, className="small text-muted"),
                    html.Td(date_display, className="small text-muted"),
                ],
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
            # Hidden data storage for search filtering
            papers_data_store,
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
    search_ids = [f"arxiv-search-{key}" for key in ARXIV_SOURCES_CONFIG.keys()]

    for search_id in search_ids:

        @app.callback(
            Output(f"{search_id}-results", "children"),
            [Input(search_id, "value")],
            State(f"{search_id}-data", "children"),
        )
        def update_arxiv_search(search_term, _unused_state_data, current_search_id=search_id):
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
                     filtered_papers = papers_data[:MAX_PAPERS_PER_TAB] # Limit initial view

                # Create table for filtered results
                table_header = [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Title"),
                                html.Th("Authors"),
                                html.Th("Published Date"),
                            ]
                        )
                    )
                ]

                # Load trend data for rendering badges
                trending_map = get_trending_items_map()

                table_body_rows = []
                for i, paper in enumerate(filtered_papers):
                    # Check trend status
                    is_trending = is_item_trending(paper, trending_map)
                    primary_cat = paper.get("categories", [""])[0] if isinstance(paper.get("categories"), list) and paper.get("categories") else ""
                    trend_badge = render_trend_badge(trending_map.get(f"category:{primary_cat}") or trending_map.get(paper.get("id"))) if is_trending else None

                    title = str(paper.get("title", "Unknown Title")).replace("\n", " ").strip()
                    url = paper.get("link") or paper.get("id")
                    github_url = paper.get("github_html_url")
                    
                    authors_list = paper.get("authors", [])
                    authors_display = ", ".join(authors_list[:3]) + (f" +{len(authors_list)-3} more" if len(authors_list) > 3 else "") if isinstance(authors_list, list) else str(authors_list)
                    
                    date_display = format_article_date(paper)

                    row_class = "trending-item" if is_trending else ""

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

                    table_body_rows.append(
                        html.Tr(
                            [
                                html.Td(title_elements),
                                html.Td(authors_display, className="small text-muted"),
                                html.Td(date_display, className="small text-muted"),
                            ],
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
    
    # Order of tabs to display (All first, then categories)
    ordered_keys = [
        "all_arxiv",
        "machine_learning",
        "computer_vision",
        "nlp",
        "neural_networks",
        "robotics",
        "reinforcement_learning"
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
        ]
    )


def register_arxiv_callbacks(app):
    """Register search callbacks for all ArXiv tabs."""
    # Get all unique search IDs from the source config
    search_ids = [f"arxiv-search-{key}" for key in ARXIV_SOURCES_CONFIG.keys()]

    for search_id in search_ids:

        @app.callback(
            Output(f"{search_id}-results", "children"),
            [Input(search_id, "value")],
            State(f"{search_id}-data", "children"),
        )
        def update_arxiv_search(search_term, _unused_state_data, current_search_id=search_id):
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
                     filtered_papers = papers_data[:MAX_PAPERS_PER_TAB] # Limit initial view

                # Create table for filtered results
                table_header = [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Title"),
                                html.Th("Authors"),
                                html.Th("Published Date"),
                            ]
                        )
                    )
                ]

                # Load trend data for rendering badges
                trending_map = get_trending_items_map()

                table_body_rows = []
                for i, paper in enumerate(filtered_papers):
                    # Check trend status
                    is_trending = is_item_trending(paper, trending_map)
                    primary_cat = paper.get("categories", [""])[0] if isinstance(paper.get("categories"), list) and paper.get("categories") else ""
                    trend_badge = render_trend_badge(trending_map.get(f"category:{primary_cat}") or trending_map.get(paper.get("id"))) if is_trending else None

                    title = str(paper.get("title", "Unknown Title")).replace("\n", " ").strip()
                    url = paper.get("link") or paper.get("id")
                    github_url = paper.get("github_html_url")
                    
                    authors_list = paper.get("authors", [])
                    authors_display = ", ".join(authors_list[:3]) + (f" +{len(authors_list)-3} more" if len(authors_list) > 3 else "") if isinstance(authors_list, list) else str(authors_list)
                    
                    date_display = format_article_date(paper)

                    row_class = "trending-item" if is_trending else ""

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

                    table_body_rows.append(
                        html.Tr(
                            [
                                html.Td(title_elements),
                                html.Td(authors_display, className="small text-muted"),
                                html.Td(date_display, className="small text-muted"),
                            ],
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
    
    # Order of tabs to display (All first, then categories)
    ordered_keys = [
        "all_arxiv",
        "machine_learning",
        "computer_vision",
        "nlp",
        "neural_networks",
        "robotics",
        "reinforcement_learning"
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

