"""ArXiv Research Dashboard Tab - Enhanced with Duplicate Filtering

This is an enhanced version of the arxiv_research_tab.py that demonstrates
how to integrate duplicate filtering into dashboard components.
"""

import json
import logging

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, dcc, html

from src.web.dashboard.components.duplicate_filter import (
    create_duplicate_filter_component,
    register_duplicate_filter_callback,
    register_filtered_data_callback,
)
from src.web.dashboard.components.items_per_page_selector import (
    create_items_per_page_selector,
    register_items_per_page_callback,
)

# Import shared utilities
from src.web.dashboard.utils import file_exists, get_data_path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ArXiv data path
ARXIV_DATA_PATH = get_data_path("arxiv", "arxiv_papers_latest.json")

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


def load_arxiv_data():
    """Load ArXiv papers data from JSON file with duplicate information."""
    global ALL_ARXIV_DATA, ARXIV_DATA_LOADED

    if not file_exists(ARXIV_DATA_PATH):
        logger.warning(f"ArXiv data file not found: {ARXIV_DATA_PATH}")
        ALL_ARXIV_DATA = pd.DataFrame()
        ARXIV_DATA_LOADED = True
        return

    try:
        with open(ARXIV_DATA_PATH, encoding="utf-8") as f:
            data = json.load(f)

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

        # Process duplicate information
        df["duplicate_display"] = df.apply(lambda row: create_duplicate_badge(row), axis=1)

        # Process quality score
        df["quality_display"] = df.apply(lambda row: create_quality_badge(row), axis=1)

        # Sort by publication date (newest first), then by quality score (highest first)
        df = df.sort_values(
            ["published_date", "quality_score"],
            ascending=[False, True],
            na_position="last",
        )

        ALL_ARXIV_DATA = df
        ARXIV_DATA_LOADED = True
        logger.info(f"Loaded {len(df)} ArXiv papers")

    except Exception as e:
        logger.error(f"Error loading ArXiv data: {e}")
        ALL_ARXIV_DATA = pd.DataFrame()
        ARXIV_DATA_LOADED = True


def create_duplicate_badge(row):
    """Create a duplicate status badge for a paper."""
    is_duplicate = row.get("is_duplicate", False)
    group_id = row.get("duplicate_group_id")

    if is_duplicate:
        return dbc.Badge(
            "Duplicate",
            color="warning",
            className="me-2",
            title=f"Duplicate group: {group_id}",
        )
    elif group_id:
        return dbc.Badge(
            "Original",
            color="success",
            className="me-2",
            title=f"Original item in group: {group_id}",
        )
    else:
        return None


def create_quality_badge(row):
    """Create a quality score badge for a paper."""
    quality_score = row.get("quality_score")
    if quality_score is not None:
        if quality_score >= 90:
            color = "success"
        elif quality_score >= 80:
            color = "info"
        elif quality_score >= 70:
            color = "warning"
        else:
            color = "secondary"

        return dbc.Badge(
            f"Q: {quality_score:.0f}",
            color=color,
            className="ms-2",
            title=f"Quality Score: {quality_score:.1f}/100",
        )
    return None


def create_papers_table(df_subset):
    """Create a table displaying ArXiv papers with duplicate information."""
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
                    html.Th("Quality"),
                    html.Th("Summary"),
                    html.Th("Actions"),
                ]
            )
        )
    ]

    table_body_rows = []
    for _, paper in df_subset.iterrows():
        # Create clickable title with ArXiv link
        title_link = html.A(
            paper.get("display_title", "Unknown Title"),
            href=paper.get("link", "#"),
            target="_blank",
            className="text-decoration-none",
        )

        # Add duplicate and quality badges
        title_cell_content = [title_link]

        # Add duplicate badge if present
        duplicate_badge = paper.get("duplicate_display")
        if duplicate_badge:
            title_cell_content.append(duplicate_badge)

        # Add GitHub link if available
        if paper.get("github_html_url"):
            github_link = html.A(
                html.I(className="fab fa-github ms-2"),
                href=paper["github_html_url"],
                target="_blank",
                className="text-decoration-none text-muted",
            )
            title_cell_content.append(github_link)

        title_cell = html.Td(title_cell_content)

        # Authors cell
        authors_cell = html.Td(paper.get("authors_display", "Unknown"), className="small")

        # Category cell
        category_cell = html.Td(
            html.Span(
                paper.get("primary_category_display", "Unknown"),
                className="badge bg-secondary",
            )
        )

        # Published date cell
        published_cell = html.Td(paper.get("published_display", "N/A"), className="small")

        # Quality score cell
        quality_cell = html.Td(paper.get("quality_display"))

        # Summary cell
        summary_cell = html.Td(html.Div(paper.get("summary_preview", "No summary available"), className="small"))

        # Actions cell
        actions_cell = html.Td(
            [
                html.A(
                    html.I(className="fas fa-external-link-alt me-1"),
                    href=paper.get("link", "#"),
                    target="_blank",
                    className="btn btn-sm btn-outline-primary me-1",
                    title="View on ArXiv",
                ),
                html.A(
                    html.I(className="fas fa-download"),
                    href=paper.get("pdf_url", paper.get("link", "#")),
                    target="_blank",
                    className="btn btn-sm btn-outline-secondary",
                    title="Download PDF",
                ),
            ]
        )

        # Create row with conditional styling for duplicates
        row_class = ""
        if paper.get("is_duplicate", False):
            row_class = "table-warning"  # Highlight duplicates

        table_body_rows.append(
            html.Tr(
                [
                    title_cell,
                    authors_cell,
                    category_cell,
                    published_cell,
                    quality_cell,
                    summary_cell,
                    actions_cell,
                ],
                className=row_class,
            )
        )

    table_body = [html.Tbody(table_body_rows)]

    return dbc.Table(
        table_header + table_body,
        striped=True,
        bordered=True,
        hover=True,
        responsive=True,
    )


def create_layout():
    """Create the ArXiv research tab layout with duplicate filtering."""
    return html.Div(
        [
            dcc.Store(id="arxiv-data-store"),  # Store for raw arxiv data
            dcc.Store(id="arxiv-filtered-data"),  # Store for filtered data
            # Header
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("🔬 ArXiv Research Papers", className="mb-3"),
                            html.P(
                                "Latest research papers from ArXiv with intelligent duplicate filtering and quality scoring.",
                                className="text-muted",
                            ),
                        ]
                    )
                ]
            ),
            # Duplicate filter component
            *create_duplicate_filter_component("arxiv", "arxiv-data-store", "papers"),
            # Controls
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            # Search input will be added here
                                        ],
                                        width=8,
                                    ),
                                    dbc.Col(
                                        [
                                            # Items per page selector
                                            create_items_per_page_selector("arxiv", DEFAULT_PAGE_SIZE)
                                        ],
                                        width=4,
                                    ),
                                ]
                            )
                        ]
                    )
                ],
                className="mb-4",
            ),
            # Content
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div(
                                id="arxiv-content",
                                children=[
                                    # Content will be loaded here
                                ],
                            )
                        ]
                    )
                ]
            ),
            # Loading indicator
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div(
                                id="arxiv-loading",
                                className="text-center my-5",
                                children=[
                                    dbc.Spinner(color="primary", size="lg"),
                                    html.P(
                                        "Loading ArXiv papers...",
                                        className="mt-3 text-muted",
                                    ),
                                ],
                            )
                        ]
                    )
                ]
            ),
        ]
    )


def register_callbacks(app):
    """Register all callbacks for the ArXiv research tab."""

    # Load data on page load
    @app.callback(
        Output("arxiv-data-store", "data"),
        Input("arxiv-data-store", "data"),
        prevent_initial_call=False,
    )
    def load_data_on_start(_):
        """Load ArXiv data when the tab is first accessed."""
        load_arxiv_data()
        if not ALL_ARXIV_DATA.empty:
            return ALL_ARXIV_DATA.to_dict("records")
        return []

    # Register duplicate filter callbacks
    register_duplicate_filter_callback("arxiv", "arxiv-data-store", "papers")
    register_filtered_data_callback("arxiv", "arxiv-data-store", ("arxiv-filtered-data", "data"))

    # Register items per page callback
    register_items_per_page_callback("arxiv")

    # Update content based on filtered data
    @app.callback(
        [Output("arxiv-content", "children"), Output("arxiv-loading", "children")],
        [Input("arxiv-filtered-data", "data"), Input("arxiv-items-per-page", "data")],
    )
    def update_arxiv_content(filtered_data, items_per_page):
        """Update the ArXiv content based on filtered data."""
        # Hide loading indicator
        loading_content = html.Div()

        if not filtered_data:
            empty_content = dbc.Alert("No papers found matching your criteria.", color="info")
            return empty_content, loading_content

        # Apply pagination
        items_per_page = items_per_page or DEFAULT_PAGE_SIZE
        paginated_data = filtered_data[:items_per_page]

        # Create DataFrame for table
        df = pd.DataFrame(paginated_data)

        # Create table
        table = create_papers_table(df)

        # Create summary stats
        total_items = len(filtered_data)
        showing_items = len(paginated_data)

        summary = html.P(
            f"Showing {showing_items} of {total_items} papers",
            className="text-muted mb-3",
        )

        return [summary, table], loading_content


# Example usage in main dashboard app:
# Example usage in main dashboard app:
# from src.web.dashboard.components.arxiv_research_tab_with_duplicates import create_layout, register_callbacks
#
# # In your main dashboard app:
# arxiv_layout = create_layout()
# register_callbacks(app)
