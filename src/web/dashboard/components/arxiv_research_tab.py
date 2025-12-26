"""ArXiv Research Dashboard Tab - Simplified Paper Browser
Clean, fast interface for discovering ArXiv research papers
"""

import json
import logging
from pathlib import Path
from typing import Any

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, dcc, html

from src.web.dashboard.components.items_per_page_selector import (
    create_items_per_page_selector,
    load_initial_preference,
    register_items_per_page_callback,
)
from src.web.dashboard.components.trend_filter import render_trend_filter
from src.web.dashboard.trend_utils import (
    get_trending_items_map,
    is_item_trending,
    load_latest_trends,
    render_trend_badge,
)

# Import shared utilities
from src.web.dashboard.utils import file_exists, get_data_path

# Import repository pattern (NEW)
from src.repositories import BaseRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ArXiv data path
ARXIV_DATA_PATH = get_data_path("arxiv", "arxiv_papers_latest.json")

# NEW: Repository-based loading (SOLID Pattern)
class ArXivRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for ArXiv research papers data."""

    def __init__(self):
        """Initialize ArXiv repository."""
        super().__init__(
            data_path=Path(ARXIV_DATA_PATH),
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform JSON data into list of papers.

        Args:
            raw_data: Raw JSON data

        Returns:
            List of paper dictionaries
        """
        if isinstance(raw_data, list):
            return raw_data
        elif isinstance(raw_data, dict):
            return [raw_data]
        else:
            return []

# Create singleton instance
arxiv_repo = ArXivRepository()

# ArXiv category mapping for better display
ARXIV_CATEGORY_MAPPING = {
    "cs.AI": "Artificial Intelligence",
    "cs.LG": "Machine Learning",
    "cs.CV": "Computer Vision",
    "cs.CL": "Natural Language Processing",
    "cs.RO": "Robotics",
    "cs.CR": "Cryptography & Security",
    "cs.DC": "Distributed Computing",
    "cs.DS": "Data Structures & Algorithms",
    "cs.HC": "Human-Computer Interaction",
    "cs.IR": "Information Retrieval",
    "cs.IT": "Information Theory",
    "cs.NE": "Neural Networks",
    "cs.SE": "Software Engineering",
    "stat.ML": "Statistics - Machine Learning",
    "math.ST": "Statistics Theory",
    "physics.data-an": "Data Analysis",
    "q-bio.NC": "Quantitative Biology - Neurons",
}

# Global data storage
ALL_ARXIV_DATA = pd.DataFrame()
ARXIV_DATA_LOADED = False
DEFAULT_PAGE_SIZE = 24


# OLD: Direct file loading (commented out for migration - SAFE TO ROLLBACK)
# def load_arxiv_data():
#     """Load ArXiv papers data from JSON file"""
#     global ALL_ARXIV_DATA, ARXIV_DATA_LOADED
#
#     if not file_exists(ARXIV_DATA_PATH):
#         logger.warning(f"ArXiv data file not found: {ARXIV_DATA_PATH}")
#         ALL_ARXIV_DATA = pd.DataFrame()
#         ARXIV_DATA_LOADED = True
#         return
#
#     try:
#         with open(ARXIV_DATA_PATH, encoding="utf-8") as f:
#             data = json.load(f)
#
#         if not data:
#             logger.warning("ArXiv data file is empty")
#             ALL_ARXIV_DATA = pd.DataFrame()
#             ARXIV_DATA_LOADED = True
#             return
#
#         df = pd.DataFrame(data)
#
#         # Process data for better display
#         df["display_title"] = df["title"].str.replace("\n", " ").str.strip()
#         df["display_summary"] = df["summary"].str.replace("\n", " ").str.strip()
#         df["summary_preview"] = df["display_summary"].apply(lambda x: x[:200] + "..." if len(str(x)) > 200 else x)
#
#         # Process authors
#         df["authors_display"] = df["authors"].apply(lambda x: (", ".join(x[:3]) + (f" +{len(x)-3} more" if len(x) > 3 else "") if isinstance(x, list) else str(x)))
#
#         # Process categories
#         df["primary_category_display"] = df["categories"].apply(lambda x: (ARXIV_CATEGORY_MAPPING.get(x[0], x[0]) if isinstance(x, list) and x else "Unknown"))
#
#         # Process publication date
#         df["published_date"] = pd.to_datetime(df["published"], errors="coerce")
#         df["published_display"] = df["published_date"].dt.strftime("%Y-%m-%d")
#
#         # Sort by publication date (newest first)
#         df = df.sort_values("published_date", ascending=False, na_position="last")
#
#         ALL_ARXIV_DATA = df
#         ARXIV_DATA_LOADED = True
#         logger.info(f"Loaded {len(df)} ArXiv papers")
#
#     except Exception as e:
#         logger.error(f"Error loading ArXiv data: {e}")
#         ALL_ARXIV_DATA = pd.DataFrame()
#         ARXIV_DATA_LOADED = True


def load_arxiv_data():
    """Load ArXiv papers data using repository pattern (NEW).

    Returns:
        List of paper dictionaries
    """
    global ALL_ARXIV_DATA, ARXIV_DATA_LOADED

    try:
        data = arxiv_repo.get()

        if not data:
            logger.warning("ArXiv data file is empty")
            ALL_ARXIV_DATA = pd.DataFrame()
            ARXIV_DATA_LOADED = True
            return

        df = pd.DataFrame(data)

        # Process data for better display
        df["display_title"] = df["title"].str.replace("\n", " ").str.strip()
        df["display_summary"] = df["summary"].str.replace("\n", " ").str.strip()
        df["summary_preview"] = df["display_summary"].apply(lambda x: x[:200] + "..." if len(str(x)) > 200 else x)

        # Process authors
        df["authors_display"] = df["authors"].apply(lambda x: (", ".join(x[:3]) + (f" +{len(x)-3} more" if len(x) > 3 else "") if isinstance(x, list) else str(x)))

        # Process categories
        df["primary_category_display"] = df["categories"].apply(lambda x: (ARXIV_CATEGORY_MAPPING.get(x[0], x[0]) if isinstance(x, list) and x else "Unknown"))

        # Process publication date
        df["published_date"] = pd.to_datetime(df["published"], errors="coerce")
        df["published_display"] = df["published_date"].dt.strftime("%Y-%m-%d")

        # Sort by publication date (newest first)
        df = df.sort_values("published_date", ascending=False, na_position="last")

        ALL_ARXIV_DATA = df
        ARXIV_DATA_LOADED = True
        logger.info(f"Loaded {len(df)} ArXiv papers")

    except Exception as e:
        logger.error(f"Error loading ArXiv data: {e}")
        ALL_ARXIV_DATA = pd.DataFrame()
        ARXIV_DATA_LOADED = True


def format_date_display(date_str):
    """Format date for display"""
    if pd.isna(date_str) or not date_str:
        return "N/A"
    return date_str


def create_papers_table(df_subset):
    """Create a table displaying ArXiv papers"""
    if df_subset.empty:
        return dbc.Alert("No papers match your criteria.", color="info")

    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Title"),
                    html.Th("Authors"),
                    html.Th("Category"),
                    html.Th("Published"),
                    html.Th("Summary"),
                    html.Th("Trend"),
                    html.Th("Actions"),
                ]
            )
        )
    ]

    # Load trends data for badge creation (do once outside loop)
    trends_data = {}
    trending_items = {}
    try:
        trends_data = load_latest_trends()
        trending_items = get_trending_items_map(trends_data)
    except Exception as e:
        logger.error(f"Error loading trends for badges: {e}")

    table_body_rows = []
    for _, paper in df_subset.iterrows():
        # Create clickable title with ArXiv link
        title_link = html.A(
            paper.get("display_title", "Unknown Title"),
            href=paper.get("link", "#"),
            target="_blank",
            className="text-decoration-none",
        )

        # Add GitHub link if available
        title_cell_content = [title_link]
        if paper.get("github_html_url"):
            github_link = html.A(
                html.I(className="fab fa-github ms-2"),
                href=paper["github_html_url"],
                target="_blank",
                title="View GitHub Repository",
                className="text-muted",
            )
            title_cell_content.append(github_link)

        # Add to Shortcuts button
        shortcut_btn = html.Div(
            [
                dbc.Button(
                    [html.I(className="fas fa-star me-1"), "Add to Shortcuts"],
                    id=f"add-shortcut-arxiv-{paper.name if hasattr(paper, 'name') else paper.get('link', '')[:50]}",
                    color="outline-warning",
                    size="sm",
                    className="me-1",
                    **{
                        "data-source-name": paper.get("display_title", "Unknown Paper"),
                        "data-source-domain": "Papers",
                        "data-source-filter": json.dumps(
                            {
                                "source": "arxiv",
                                "title": paper.get("display_title", ""),
                                "category": paper.get("primary_category_display", ""),
                                "authors": paper.get("authors_display", ""),
                                "link": paper.get("link", ""),
                            }
                        ),
                    },
                )
            ]
        )

        table_body_rows.append(
            html.Tr(
                [
                    html.Td(title_cell_content),
                    html.Td(paper.get("authors_display", "Unknown"), className="small"),
                    html.Td(
                        dbc.Badge(
                            paper.get("primary_category_display", "Unknown"),
                            color="outline-primary",
                            className="small",
                        )
                    ),
                    html.Td(
                        format_date_display(paper.get("published_display")),
                        className="small text-muted",
                    ),
                    html.Td(
                        paper.get("summary_preview", "No summary available"),
                        className="small text-muted",
                        style={"max-width": "250px"},
                    ),
                    html.Td(
                        (render_trend_badge(trending_items.get(f"category:{paper.get('source')}") or trending_items.get(paper.get("id"))) if is_item_trending(paper.to_dict(), trending_items) else None),
                        className="text-nowrap",
                    ),
                    html.Td(shortcut_btn, className="text-nowrap"),
                ]
            )
        )

    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(
        table_header + table_body,
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        size="sm",
        className="table-responsive",
    )


def render_arxiv_research_tab():
    """Main render function for ArXiv Research tab"""
    # Load data on render
    load_arxiv_data()

    if not ARXIV_DATA_LOADED:
        return dbc.Alert("ArXiv data failed to load. Check logs.", color="danger", className="mt-3")

    if ALL_ARXIV_DATA.empty:
        return dbc.Alert("No ArXiv papers data currently available.", color="info", className="mt-3")

    # Prepare filter options
    categories = ALL_ARXIV_DATA["primary_category_display"].dropna().unique()
    category_options = [{"label": cat, "value": cat} for cat in sorted(categories)]

    total_papers = len(ALL_ARXIV_DATA)
    latest_date = ALL_ARXIV_DATA["published_display"].dropna().iloc[0] if not ALL_ARXIV_DATA.empty else "N/A"

    # Create simple preset controls (HTML-only, no callback conflicts)
    preset_controls = [
        # Preset selector dropdown
        dbc.Select(
            id="arxiv-preset-selector",
            placeholder="Select saved preset...",
            className="mb-2",
        ),
        # Preset action buttons
        html.Div(
            [
                dbc.Button(
                    "Save Current Filters",
                    id="arxiv-save-preset-btn",
                    color="primary",
                    size="sm",
                    className="me-2",
                ),
                dbc.Button(
                    "Update Preset",
                    id="arxiv-update-preset-btn",
                    color="warning",
                    size="sm",
                    className="me-2",
                    style={"display": "none"},
                ),
                dbc.Button(
                    "Delete Preset",
                    id="arxiv-delete-preset-btn",
                    color="danger",
                    size="sm",
                    style={"display": "none"},
                ),
            ],
            className="d-flex gap-2 mb-2",
        ),
        # Hidden storage for current filters (for JavaScript access)
        dcc.Store(id="arxiv-current-filters", data={}),
        # Hidden storage for selected preset
        dcc.Store(id="arxiv-selected-preset", data={}),
        # Hidden storage for show duplicates toggle (Story 4.1: Content Deduplication)
        dcc.Store(id="arxiv-show-duplicates-store", data={"show_duplicates": False}),
        # Dummy output for preset apply clientside callback
        html.Div(id="dummy-output-preset-apply", style={"display": "none"}),
        # Preset save modal
        dbc.Modal(
            [
                dbc.ModalHeader("Save Filter Preset"),
                dbc.ModalBody(
                    [
                        dbc.Label("Preset Name:"),
                        dbc.Input(
                            id="arxiv-preset-name-input",
                            placeholder="Enter preset name...",
                            maxLength=50,
                        ),
                        html.Div(
                            id="arxiv-preset-error",
                            className="text-danger mt-2",
                            style={"display": "none"},
                        ),
                    ]
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button("Cancel", id="arxiv-cancel-save-btn", color="secondary"),
                        dbc.Button("Save", id="arxiv-confirm-save-btn", color="primary"),
                    ]
                ),
            ],
            id="arxiv-save-preset-modal",
            is_open=False,
        ),
    ]

    return html.Div(
        [
            # Header with simple stats
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H3(
                                [
                                    html.I(className="fas fa-graduation-cap me-2"),
                                    "ArXiv Research Papers",
                                ],
                                className="text-primary mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.H5(
                                                f"{total_papers:,}",
                                                className="text-primary mb-0",
                                            ),
                                            html.P(
                                                "Total Papers",
                                                className="text-muted small mb-0",
                                            ),
                                        ],
                                        md=4,
                                    ),
                                    dbc.Col(
                                        [
                                            html.H5(
                                                f"{len(categories)}",
                                                className="text-success mb-0",
                                            ),
                                            html.P(
                                                "Categories",
                                                className="text-muted small mb-0",
                                            ),
                                        ],
                                        md=4,
                                    ),
                                    dbc.Col(
                                        [
                                            html.H5(latest_date, className="text-info mb-0"),
                                            html.P(
                                                "Latest Paper",
                                                className="text-muted small mb-0",
                                            ),
                                        ],
                                        md=4,
                                    ),
                                ],
                                className="mb-4",
                            ),
                        ]
                    )
                ]
            ),
            # Filter presets controls
            html.Div(preset_controls, className="mb-3"),
            # Search and filter controls
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Input(
                                id="arxiv-search-input",
                                placeholder="Search by title or abstract...",
                                className="mb-2",
                            )
                        ],
                        md=4,
                    ),
                    dbc.Col(
                        [
                            dcc.Dropdown(
                                id="arxiv-category-dropdown",
                                options=category_options,
                                placeholder="Filter by category",
                                className="mb-2",
                            )
                        ],
                        md=3,
                    ),
                    create_items_per_page_selector("arxiv", default_value=DEFAULT_PAGE_SIZE),
                    dbc.Col(
                        [
                            dbc.Button(
                                id="arxiv-show-duplicates-btn",
                                color="outline-info",
                                size="sm",
                                className="w-100 mb-2",
                                children="Show Duplicates",
                            )
                        ],
                        md=2,
                    ),
                    dbc.Col([render_trend_filter("arxiv-trend-filter")], md=2),
                    dbc.Col(
                        [
                            dbc.Button(
                                "Clear Filters",
                                id="arxiv-clear-button",
                                color="outline-secondary",
                                size="sm",
                                className="w-100",
                            )
                        ],
                        md=2,
                    ),
                ],
                className="mb-3",
            ),
            # Papers table container
            html.Div(id="arxiv-papers-container"),
            # Hidden element for shortcuts add callback
            html.Div(id="dummy-output-shortcuts-add", style={"display": "none"}),
            # Pagination
            html.Div(
                id="arxiv-pagination-wrapper",
                className="d-flex justify-content-between align-items-center mt-3",
                children=[
                    html.Div(id="arxiv-pagination-info", className="text-muted"),
                    html.Div(
                        className="d-flex align-items-center gap-2",
                        children=[
                            dbc.Button(
                                "« Previous",
                                id="arxiv-prev-btn",
                                size="sm",
                                outline=True,
                                color="primary",
                                disabled=True,
                            ),
                            dbc.Input(
                                id="arxiv-page-input",
                                type="number",
                                value=1,
                                min=1,
                                max=1,
                                style={"width": "80px", "textAlign": "center"},
                                size="sm",
                            ),
                            html.Span("of", className="mx-2 text-muted"),
                            html.Span(id="arxiv-total-pages", className="text-muted"),
                            dbc.Button(
                                "Next »",
                                id="arxiv-next-btn",
                                size="sm",
                                outline=True,
                                color="primary",
                                disabled=True,
                            ),
                        ],
                    ),
                ],
            ),
            # Script to initialize items-per-page selector from localStorage
            html.Script(load_initial_preference("arxiv")),
        ]
    )


def register_arxiv_callbacks(app):
    """Register all ArXiv tab callbacks including filter presets"""
    # Register ArXiv tab callbacks including filter presets

    # Store current filters for preset functionality
    @app.callback(
        Output("arxiv-current-filters", "data"),
        [
            Input("arxiv-search-input", "value"),
            Input("arxiv-category-dropdown", "value"),
        ],
    )
    def update_current_filters(search_term, category):
        """Store current filter values for preset functionality"""
        return {"search_term": search_term, "category": category}

    # Apply preset callback
    @app.callback(
        [
            Output("arxiv-search-input", "value", allow_duplicate=True),
            Output("arxiv-category-dropdown", "value", allow_duplicate=True),
        ],
        [Input("arxiv-preset-selector", "value")],
        [State("arxiv-selected-preset", "data")],
        prevent_initial_call=True,
    )
    def apply_preset(selected_preset_name, selected_preset_data):
        """Apply selected preset to filter inputs"""
        if not selected_preset_name or not selected_preset_data:
            return [None, None]

        filters = selected_preset_data.get("filters", {})
        return [filters.get("search_term"), filters.get("category")]

    # Delete preset callback
    @app.callback(
        Output("arxiv-preset-selector", "value", allow_duplicate=True),
        [Input("arxiv-delete-preset-btn", "n_clicks")],
        prevent_initial_call=True,
    )
    def delete_preset(n_clicks):
        """Delete selected preset"""
        if n_clicks:
            return None
        return dash.no_update

    # Update preset callback
    @app.callback(
        Output("arxiv-save-preset-modal", "is_open", allow_duplicate=True),
        [Input("arxiv-update-preset-btn", "n_clicks")],
        prevent_initial_call=True,
    )
    def update_preset(n_clicks):
        """Open modal for updating preset"""
        if n_clicks:
            return True
        return dash.no_update

    # Original ArXiv papers callback
    @app.callback(
        [
            Output("arxiv-papers-container", "children"),
            Output("arxiv-pagination-info", "children"),
            Output("arxiv-total-pages", "children"),
            Output("arxiv-page-input", "max"),
            Output("arxiv-page-input", "value"),
            Output("arxiv-prev-btn", "disabled"),
            Output("arxiv-next-btn", "disabled"),
        ],
        [
            Input("arxiv-search-input", "value"),
            Input("arxiv-category-dropdown", "value"),
            Input("arxiv-page-input", "value"),
            Input("arxiv-prev-btn", "n_clicks"),
            Input("arxiv-items-per-page-select", "value"),
            Input("arxiv-next-btn", "n_clicks"),
            Input("arxiv-preset-selector", "value"),
            Input("arxiv-show-duplicates-store", "data"),
            Input("arxiv-trend-filter-store", "data"),
        ],
        prevent_initial_call=False,
    )
    def update_arxiv_papers(
        search_term,
        category,
        current_page,
        prev_clicks,
        items_per_page,
        next_clicks,
        selected_preset,
        duplicates_store,
        trend_filter_store,
    ):
        try:
            if not ARXIV_DATA_LOADED:
                return (
                    dbc.Alert("Loading ArXiv data...", color="info"),
                    "",
                    "1",
                    1,
                    1,
                    True,
                    True,
                )

            if ALL_ARXIV_DATA.empty:
                return (
                    dbc.Alert("No ArXiv data available.", color="warning"),
                    "",
                    "1",
                    1,
                    1,
                    True,
                    True,
                )

            # Apply filters
            df_filtered = ALL_ARXIV_DATA.copy()

            # Handle duplicates filtering (Story 4.1: Content Deduplication Engine)
            show_duplicates = duplicates_store.get("show_duplicates", False) if duplicates_store else False
            if not show_duplicates:
                df_filtered = df_filtered[df_filtered.get("is_duplicate", False) == False]

            if search_term:
                search_lower = search_term.lower()
                df_filtered = df_filtered[df_filtered["display_title"].str.lower().contains(search_lower, na=False) | df_filtered["display_summary"].str.lower().contains(search_lower, na=False)]

            if category:
                df_filtered = df_filtered[df_filtered["primary_category_display"] == category]

            # Apply trend filtering (Story 8.2: Simple Trend Indicators)
            if trend_filter_store and trend_filter_store.get("show_trending_only", False):
                try:
                    trending_items_map = get_trending_items_map()

                    # Convert DataFrame to list for trend filtering
                    filtered_list = df_filtered.to_dict("records")
                    trend_filtered_list = [item for item in filtered_list if is_item_trending(item, trending_items_map)]

                    if trend_filtered_list:
                        df_filtered = pd.DataFrame(trend_filtered_list)
                    else:
                        df_filtered = pd.DataFrame()  # Empty if no trending items

                except Exception as e:
                    logger.error(f"Error applying trend filter: {e}")

            if df_filtered.empty:
                return (
                    dbc.Alert("No papers match your filters.", color="info"),
                    "",
                    "1",
                    1,
                    1,
                    True,
                    True,
                )

            # Use items_per_page from selector, fallback to default
            if items_per_page is None:
                items_per_page = DEFAULT_PAGE_SIZE

            # Calculate pagination
            total_items = len(df_filtered)
            max_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

            # Handle pagination button clicks
            ctx = dash.callback_context
            if ctx.triggered:
                prop_id = ctx.triggered[0]["prop_id"]
                if "prev-btn" in prop_id:
                    current_page = max(1, (current_page or 1) - 1)
                elif "next-btn" in prop_id:
                    current_page = min(max_pages, (current_page or 1) + 1)
                elif "items-per-page-select" in prop_id:
                    # Reset to first page when items per page changes
                    current_page = 1

            current_page = max(1, min(current_page or 1, max_pages))

            # Get page data
            start_idx = (current_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            df_paginated = df_filtered.iloc[start_idx:end_idx]

            # Create table
            table = create_papers_table(df_paginated)

            # Pagination info
            pagination_info = f"Showing {start_idx + 1}-{min(end_idx, total_items)} of {total_items} papers"

            # Button states
            prev_disabled = current_page <= 1
            next_disabled = current_page >= max_pages

            return (
                table,
                pagination_info,
                str(max_pages),
                max_pages,
                current_page,
                prev_disabled,
                next_disabled,
            )

        except Exception as e:
            logger.error(f"Error updating ArXiv papers: {e}")
            return (
                dbc.Alert(f"Error loading ArXiv data: {e!s}", color="danger"),
                "",
                "1",
                1,
                1,
                True,
                True,
            )

    # Reset pagination when filters change
    @app.callback(
        Output("arxiv-page-input", "value", allow_duplicate=True),
        [
            Input("arxiv-search-input", "value"),
            Input("arxiv-category-dropdown", "value"),
        ],
        prevent_initial_call=True,
    )
    def reset_arxiv_pagination(search_term, category):
        return 1

    # Clear filters callback
    @app.callback(
        [
            Output("arxiv-search-input", "value", allow_duplicate=True),
            Output("arxiv-category-dropdown", "value", allow_duplicate=True),
        ],
        Input("arxiv-clear-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_arxiv_filters(n_clicks):
        if n_clicks:
            return "", None
        return dash.no_update, dash.no_update

    # Clientside callbacks for filter preset functionality
    app.clientside_callback(
        """
        function(trigger_id) {
            // Load preset options from localStorage
            try {
                const storageKey = 'watchtower_filter_presets';
                const stored = localStorage.getItem(storageKey);
                const presets = stored ? JSON.parse(stored) : {};
                const tabPresets = presets['arxiv_research'] || [];

                return tabPresets.map(preset => ({
                    label: preset.name,
                    value: preset.name
                }));
            } catch (error) {
                console.error('Error loading presets:', error);
                return [];
            }
        }
        """,
        Output("arxiv-preset-selector", "options"),
        Input("arxiv-preset-selector", "id"),
    )

    # Apply selected preset
    app.clientside_callback(
        """
        function(selected_preset, current_filters) {
            if (!selected_preset || !current_filters) {
                return window.dash_clientside.no_update;
            }

            try {
                const storageKey = 'watchtower_filter_presets';
                const stored = localStorage.getItem(storageKey);
                const presets = stored ? JSON.parse(stored) : {};
                const tabPresets = presets['arxiv_research'] || [];

                const selectedPresetData = tabPresets.find(p => p.name === selected_preset);
                if (selectedPresetData) {
                    // Store selected preset data for the Python callback to use
                    return selectedPresetData.filters;
                }
            } catch (error) {
                console.error('Error applying preset:', error);
            }

            return window.dash_clientside.no_update;
        }
        """,
        Output("arxiv-selected-preset", "data"),
        [Input("arxiv-preset-selector", "value")],
        [State("arxiv-current-filters", "data")],
    )

    # Save preset functionality
    app.clientside_callback(
        """
        function(confirm_clicks, cancel_clicks, is_open, preset_name, current_filters) {
            const ctx = window.dash_clientside.callback_context;

            if (!ctx || !ctx.triggered) {
                return window.dash_clientside.no_update;
            }

            const trigger_id = ctx.triggered[0]['prop_id'].split('.')[0];

            if (trigger_id === 'arxiv-confirm-save-btn' && preset_name && current_filters) {
                try {
                    const storageKey = 'watchtower_filter_presets';
                    const stored = localStorage.getItem(storageKey);
                    const presets = stored ? JSON.parse(stored) : {};

                    // Initialize tab if not exists
                    if (!presets['arxiv_research']) {
                        presets['arxiv_research'] = [];
                    }

                    // Check maximum presets limit
                    if (presets['arxiv_research'].length >= 10) {
                        alert('Maximum 10 presets allowed per tab');
                        return false;
                    }

                    // Check for duplicate names
                    const existingIndex = presets['arxiv_research'].findIndex(p => p.name === preset_name);
                    if (existingIndex !== -1) {
                        alert('Preset name already exists');
                        return false;
                    }

                    // Add new preset
                    const newPreset = {
                        name: preset_name,
                        filters: current_filters,
                        created_at: new Date().toISOString(),
                        updated_at: new Date().toISOString()
                    };

                    presets['arxiv_research'].push(newPreset);
                    localStorage.setItem(storageKey, JSON.stringify(presets));

                    // Trigger preset dropdown refresh
                    const presetSelector = document.getElementById('arxiv-preset-selector');
                    if (presetSelector) {
                        // Force dropdown update by triggering change event
                        presetSelector.dispatchEvent(new Event('change'));
                    }

                    alert('Preset saved successfully!');
                    return false; // Close modal
                } catch (error) {
                    console.error('Error saving preset:', error);
                    alert('Error saving preset: ' + error.message);
                    return is_open; // Keep modal open on error
                }
            }

            if (trigger_id === 'arxiv-cancel-save-btn') {
                return false; // Close modal
            }

            return is_open;
        }
        """,
        Output("arxiv-save-preset-modal", "is_open", allow_duplicate=True),
        [
            Input("arxiv-confirm-save-btn", "n_clicks"),
            Input("arxiv-cancel-save-btn", "n_clicks"),
        ],
        [
            State("arxiv-save-preset-modal", "is_open"),
            State("arxiv-preset-name-input", "value"),
            State("arxiv-current-filters", "data"),
        ],
        prevent_initial_call=True,
    )

    # Apply selected preset to filters
    app.clientside_callback(
        """
        function(selected_preset_name, selected_preset_data) {
            if (!selected_preset_name || !selected_preset_data || !selected_preset_data.filters) {
                return window.dash_clientside.no_update;
            }

            const filters = selected_preset_data.filters;

            // Apply filters to the form inputs
            if (filters.search !== undefined) {
                const searchInput = document.getElementById('arxiv-search-input');
                if (searchInput) {
                    searchInput.value = filters.search;
                    searchInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }

            if (filters.category !== undefined) {
                const categoryDropdown = document.getElementById('arxiv-category-dropdown');
                if (categoryDropdown) {
                    categoryDropdown.value = filters.category;
                    categoryDropdown.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }

            return window.dash_clientside.no_update;
        }
        """,
        Output("dummy-output-preset-apply", "children"),
        [Input("arxiv-selected-preset", "data")],
        [State("arxiv-preset-selector", "value")],
    )

    # Add to Shortcuts functionality
    app.clientside_callback(
        """
        function(n_clicks) {
            const ctx = window.dash_clientside.callback_context;

            if (!ctx || !ctx.triggered || n_clicks === null) {
                return window.dash_clientside.no_update;
            }

            const trigger_id = ctx.triggered[0]['prop_id'].split('.')[0];

            // Check if this is an "Add to Shortcuts" button click
            if (trigger_id && trigger_id.startsWith('add-shortcut-arxiv-')) {
                try {
                    const button = document.getElementById(trigger_id);
                    if (!button) {
                        console.error('Button not found:', trigger_id);
                        return window.dash_clientside.no_update;
                    }

                    // Get the parent div that contains the data attributes
                    const parentDiv = button.closest('div[data-source-name]');
                    const sourceName = parentDiv.getAttribute('data-source-name');
                    const sourceDomain = parentDiv.getAttribute('data-source-domain');
                    const sourceFilterStr = parentDiv.getAttribute('data-source-filter');

                    if (!sourceName || !sourceDomain || !sourceFilterStr) {
                        console.error('Missing shortcut data attributes');
                        return window.dash_clientside.no_update;
                    }

                    let sourceFilter;
                    try {
                        sourceFilter = JSON.parse(sourceFilterStr);
                    } catch (parseError) {
                        console.error('Error parsing source filter:', parseError);
                        return window.dash_clientside.no_update;
                    }

                    // Add shortcut using the ShortcutsManager
                    if (window.shortcutsManager) {
                        const result = window.shortcutsManager.addShortcut(sourceName, sourceDomain, sourceFilter);

                        if (result) {
                            // Show success message
                            const successAlert = document.createElement('div');
                            successAlert.className = 'alert alert-success alert-dismissible fade show position-fixed';
                            successAlert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
                            successAlert.innerHTML = `
                                <i class="fas fa-check-circle me-2"></i>
                                <strong>Success!</strong> "${sourceName}" added to shortcuts.
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            `;
                            document.body.appendChild(successAlert);

                            // Auto-remove after 3 seconds
                            setTimeout(() => {
                                if (successAlert.parentNode) {
                                    successAlert.parentNode.removeChild(successAlert);
                                }
                            }, 3000);

                            // Trigger shortcuts sidebar refresh
                            const trigger = document.getElementById('shortcuts-updates-trigger');
                            if (trigger) {
                                trigger.innerHTML = Date.now();
                            }

                            console.log('Shortcut added successfully:', result);
                        } else {
                            throw new Error('Failed to add shortcut');
                        }
                    } else {
                        console.error('ShortcutsManager not available');
                        alert('Shortcuts functionality not available. Please refresh the page.');
                    }

                } catch (error) {
                    console.error('Error adding shortcut:', error);

                    // Show error message
                    const errorAlert = document.createElement('div');
                    errorAlert.className = 'alert alert-warning alert-dismissible fade show position-fixed';
                    errorAlert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
                    errorAlert.innerHTML = `
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        <strong>Error:</strong> ${error.message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    `;
                    document.body.appendChild(errorAlert);

                    // Auto-remove after 5 seconds
                    setTimeout(() => {
                        if (errorAlert.parentNode) {
                            errorAlert.parentNode.removeChild(errorAlert);
                        }
                    }, 5000);
                }
            }

            return window.dash_clientside.no_update;
        }
        """,
        Output("dummy-output-shortcuts-add", "children", allow_duplicate=True),
        [Input({"type": "add-shortcut-arxiv", "index": dash.ALL}, "n_clicks")],
        prevent_initial_call=True,
    )

    # Callback for toggling duplicates visibility (Story 4.1: Content Deduplication)
    @app.callback(
        Output("arxiv-show-duplicates-store", "data"),
        Output("arxiv-show-duplicates-btn", "children"),
        Output("arxiv-show-duplicates-btn", "color"),
        Input("arxiv-show-duplicates-btn", "n_clicks"),
        State("arxiv-show-duplicates-store", "data"),
    )
    def toggle_duplicates_visibility(n_clicks, store_data):
        """Toggle visibility of duplicate content."""
        if n_clicks is None:
            return store_data, "Show Duplicates", "outline-info"

        show_duplicates = store_data.get("show_duplicates", False)
        show_duplicates = not show_duplicates

        # Count duplicates to show appropriate button text
        if ALL_ARXIV_DATA.empty:
            duplicate_count = 0
        else:
            duplicate_count = len(ALL_ARXIV_DATA[ALL_ARXIV_DATA.get("is_duplicate", False) == True])

        if show_duplicates:
            button_text = f"Hide Duplicates ({duplicate_count})" if duplicate_count > 0 else "Hide Duplicates"
            button_color = "info"
        else:
            button_text = f"Show Duplicates ({duplicate_count})" if duplicate_count > 0 else "Show Duplicates"
            button_color = "outline-info"

        new_store_data = {"show_duplicates": show_duplicates}
        return new_store_data, button_text, button_color

    # Register client-side callback for items-per-page preference saving
    register_items_per_page_callback("arxiv")

    # Register trend filter callbacks (Story 8.2: Simple Trend Indicators)
    @app.callback(
        Output("arxiv-trend-filter-store", "data"),
        Output("arxiv-trend-filter-btn", "children"),
        Output("arxiv-trend-filter-btn", "color"),
        Output("arxiv-trend-filter-btn", "style"),
        Input("arxiv-trend-filter-btn", "n_clicks"),
        State("arxiv-trend-filter-store", "data"),
    )
    def toggle_trend_filter(n_clicks, current_filter):
        """Toggle trend filter state and button appearance."""
        if n_clicks is None:
            # Initial load - check if we have trend data
            trends_data = load_latest_trends()
            trending_count = len(trends_data.get("trending_items", []))

            if trending_count > 0:
                # Show button if we have trend data
                return (
                    current_filter,
                    f"🔥 Trending ({trending_count})",
                    "outline-info",
                    {"display": "block", "fontSize": "0.85em"},
                )
            else:
                # Hide button if no trend data
                return (
                    current_filter,
                    "🔥 Trending",
                    "outline-info",
                    {"display": "none"},
                )

        # Toggle filter state
        show_trending = current_filter.get("show_trending_only", False)
        new_filter = current_filter.copy()
        new_filter["show_trending_only"] = not show_trending

        # Update button text and color based on state
        if new_filter["show_trending_only"]:
            button_text = "🔥 All Content"
            button_color = "info"
            button_style = {"display": "block", "fontSize": "0.85em"}
        else:
            trends_data = load_latest_trends()
            trending_count = len(trends_data.get("trending_items", []))
            button_text = f"🔥 Trending ({trending_count})"
            button_color = "outline-info"
            button_style = {"display": "block", "fontSize": "0.85em"}

        return new_filter, button_text, button_color, button_style


# Load data when module is imported
load_arxiv_data()

if __name__ == "__main__":
    print("ArXiv Research Tab - Data Summary:")
    print(f"  Papers loaded: {len(ALL_ARXIV_DATA)}")
    if not ALL_ARXIV_DATA.empty:
        categories = ALL_ARXIV_DATA["primary_category_display"].nunique()
        print(f"  Categories: {categories}")
        latest = ALL_ARXIV_DATA["published_display"].dropna().iloc[0]
        print(f"  Latest paper: {latest}")
