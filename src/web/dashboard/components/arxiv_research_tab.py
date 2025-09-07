"""
ArXiv Research Dashboard Tab - Simplified Paper Browser
Clean, fast interface for discovering ArXiv research papers
"""

import json
import logging
from datetime import datetime, timezone

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, dcc, html

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
PAGE_SIZE = 15

def load_arxiv_data():
    """Load ArXiv papers data from JSON file"""
    global ALL_ARXIV_DATA, ARXIV_DATA_LOADED
    
    if not file_exists(ARXIV_DATA_PATH):
        logger.warning(f"ArXiv data file not found: {ARXIV_DATA_PATH}")
        ALL_ARXIV_DATA = pd.DataFrame()
        ARXIV_DATA_LOADED = True
        return
    
    try:
        with open(ARXIV_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            logger.warning("ArXiv data file is empty")
            ALL_ARXIV_DATA = pd.DataFrame()
            ARXIV_DATA_LOADED = True
            return
        
        df = pd.DataFrame(data)
        
        # Process data for better display
        df['display_title'] = df['title'].str.replace('\n', ' ').str.strip()
        df['display_summary'] = df['summary'].str.replace('\n', ' ').str.strip()
        df['summary_preview'] = df['display_summary'].apply(
            lambda x: x[:200] + "..." if len(str(x)) > 200 else x
        )
        
        # Process authors
        df['authors_display'] = df['authors'].apply(
            lambda x: ', '.join(x[:3]) + (f' +{len(x)-3} more' if len(x) > 3 else '') 
            if isinstance(x, list) else str(x)
        )
        
        # Process categories
        df['primary_category_display'] = df['categories'].apply(
            lambda x: ARXIV_CATEGORY_MAPPING.get(x[0], x[0]) if isinstance(x, list) and x else 'Unknown'
        )
        
        # Process publication date
        df['published_date'] = pd.to_datetime(df['published'], errors='coerce')
        df['published_display'] = df['published_date'].dt.strftime('%Y-%m-%d')
        
        # Sort by publication date (newest first)
        df = df.sort_values('published_date', ascending=False, na_position='last')
        
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
            html.Tr([
                html.Th("Title"),
                html.Th("Authors"),
                html.Th("Category"),
                html.Th("Published"),
                html.Th("Summary"),
            ])
        )
    ]
    
    table_body_rows = []
    for _, paper in df_subset.iterrows():
        # Create clickable title with ArXiv link
        title_link = html.A(
            paper.get('display_title', 'Unknown Title'),
            href=paper.get('link', '#'),
            target="_blank",
            className="text-decoration-none"
        )
        
        # Add GitHub link if available
        title_cell_content = [title_link]
        if paper.get('github_html_url'):
            github_link = html.A(
                html.I(className="fab fa-github ms-2"),
                href=paper['github_html_url'],
                target="_blank",
                title="View GitHub Repository",
                className="text-muted"
            )
            title_cell_content.append(github_link)
        
        table_body_rows.append(
            html.Tr([
                html.Td(title_cell_content),
                html.Td(
                    paper.get('authors_display', 'Unknown'),
                    className="small"
                ),
                html.Td(
                    dbc.Badge(
                        paper.get('primary_category_display', 'Unknown'),
                        color="outline-primary",
                        className="small"
                    )
                ),
                html.Td(
                    format_date_display(paper.get('published_display')),
                    className="small text-muted"
                ),
                html.Td(
                    paper.get('summary_preview', 'No summary available'),
                    className="small text-muted",
                    style={"max-width": "300px"}
                ),
            ])
        )
    
    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(
        table_header + table_body,
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        size="sm",
        className="table-responsive"
    )

def render_arxiv_research_tab():
    """Main render function for ArXiv Research tab"""
    # Load data on render
    load_arxiv_data()
    
    if not ARXIV_DATA_LOADED:
        return dbc.Alert(
            "ArXiv data failed to load. Check logs.", 
            color="danger", 
            className="mt-3"
        )
    
    if ALL_ARXIV_DATA.empty:
        return dbc.Alert(
            "No ArXiv papers data currently available.", 
            color="info", 
            className="mt-3"
        )
    
    # Prepare filter options
    categories = ALL_ARXIV_DATA['primary_category_display'].dropna().unique()
    category_options = [{"label": cat, "value": cat} for cat in sorted(categories)]
    
    total_papers = len(ALL_ARXIV_DATA)
    latest_date = ALL_ARXIV_DATA['published_display'].dropna().iloc[0] if not ALL_ARXIV_DATA.empty else "N/A"
    
    return html.Div([
        # Header with simple stats
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="fas fa-graduation-cap me-2"),
                    "ArXiv Research Papers"
                ], className="text-primary mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.H5(f"{total_papers:,}", className="text-primary mb-0"),
                        html.P("Total Papers", className="text-muted small mb-0")
                    ], md=4),
                    dbc.Col([
                        html.H5(f"{len(categories)}", className="text-success mb-0"), 
                        html.P("Categories", className="text-muted small mb-0")
                    ], md=4),
                    dbc.Col([
                        html.H5(latest_date, className="text-info mb-0"),
                        html.P("Latest Paper", className="text-muted small mb-0")
                    ], md=4),
                ], className="mb-4")
            ])
        ]),
        
        # Search and filter controls
        dbc.Row([
            dbc.Col([
                dbc.Input(
                    id="arxiv-search-input",
                    placeholder="Search by title or abstract...",
                    className="mb-2"
                )
            ], md=6),
            dbc.Col([
                dcc.Dropdown(
                    id="arxiv-category-dropdown",
                    options=category_options,
                    placeholder="Filter by category",
                    className="mb-2"
                )
            ], md=4),
            dbc.Col([
                dbc.Button(
                    "Clear Filters",
                    id="arxiv-clear-button",
                    color="outline-secondary",
                    size="sm",
                    className="w-100"
                )
            ], md=2)
        ], className="mb-3"),
        
        # Papers table container
        html.Div(id="arxiv-papers-container"),
        
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
    ])

def register_arxiv_callbacks(app):
    """Register callbacks for ArXiv Research tab"""
    
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
            Input("arxiv-next-btn", "n_clicks"),
        ],
        prevent_initial_call=False,
    )
    def update_arxiv_papers(search_term, category, current_page, prev_clicks, next_clicks):
        try:
            if not ARXIV_DATA_LOADED:
                return (
                    dbc.Alert("Loading ArXiv data...", color="info"),
                    "", "1", 1, 1, True, True
                )
            
            if ALL_ARXIV_DATA.empty:
                return (
                    dbc.Alert("No ArXiv data available.", color="warning"),
                    "", "1", 1, 1, True, True
                )
            
            # Apply filters
            df_filtered = ALL_ARXIV_DATA.copy()
            
            if search_term:
                search_lower = search_term.lower()
                df_filtered = df_filtered[
                    df_filtered['display_title'].str.lower().contains(search_lower, na=False) |
                    df_filtered['display_summary'].str.lower().contains(search_lower, na=False)
                ]
            
            if category:
                df_filtered = df_filtered[df_filtered['primary_category_display'] == category]
            
            if df_filtered.empty:
                return (
                    dbc.Alert("No papers match your filters.", color="info"),
                    "", "1", 1, 1, True, True
                )
            
            # Calculate pagination
            total_items = len(df_filtered)
            max_pages = max(1, (total_items + PAGE_SIZE - 1) // PAGE_SIZE)
            
            # Handle pagination button clicks
            ctx = dash.callback_context
            if ctx.triggered:
                prop_id = ctx.triggered[0]["prop_id"]
                if "prev-btn" in prop_id:
                    current_page = max(1, (current_page or 1) - 1)
                elif "next-btn" in prop_id:
                    current_page = min(max_pages, (current_page or 1) + 1)
            
            current_page = max(1, min(current_page or 1, max_pages))
            
            # Get page data
            start_idx = (current_page - 1) * PAGE_SIZE
            end_idx = start_idx + PAGE_SIZE
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
                dbc.Alert(f"Error loading ArXiv data: {str(e)}", color="danger"),
                "", "1", 1, 1, True, True
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
            Output("arxiv-search-input", "value"),
            Output("arxiv-category-dropdown", "value"),
        ],
        Input("arxiv-clear-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_arxiv_filters(n_clicks):
        if n_clicks:
            return "", None
        return dash.no_update, dash.no_update

# Load data when module is imported
load_arxiv_data()

if __name__ == "__main__":
    print("ArXiv Research Tab - Data Summary:")
    print(f"  Papers loaded: {len(ALL_ARXIV_DATA)}")
    if not ALL_ARXIV_DATA.empty:
        categories = ALL_ARXIV_DATA['primary_category_display'].nunique()
        print(f"  Categories: {categories}")
        latest = ALL_ARXIV_DATA['published_display'].dropna().iloc[0]
        print(f"  Latest paper: {latest}")