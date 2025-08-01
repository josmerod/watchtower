"""
ArXiv Research Dashboard Tab
Advanced scientific paper analysis and visualization with categorization and trend analysis
"""

import json
import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, callback, dash_table
from datetime import datetime, timezone
import os
import logging
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go

# Import shared utilities
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_data_path, file_exists, parse_date_universal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ArXiv category mapping for better visualization
ARXIV_CATEGORY_MAPPING = {
    'cs.AI': 'Artificial Intelligence',
    'cs.LG': 'Machine Learning',
    'cs.CV': 'Computer Vision',
    'cs.CL': 'Natural Language Processing',
    'cs.RO': 'Robotics',
    'cs.CR': 'Cryptography & Security',
    'cs.DC': 'Distributed Computing',
    'cs.DS': 'Data Structures & Algorithms',
    'cs.HC': 'Human-Computer Interaction',
    'cs.IR': 'Information Retrieval',
    'cs.IT': 'Information Theory',
    'cs.NE': 'Neural Networks',
    'cs.SE': 'Software Engineering',
    'stat.ML': 'Statistics - Machine Learning',
    'math.ST': 'Statistics Theory',
    'physics.data-an': 'Data Analysis',
    'q-bio.NC': 'Quantitative Biology - Neurons',
}

# Enhanced ArXiv configuration with multiple data sources
ARXIV_SOURCES_CONFIG = {
    "arxiv_papers": {
        "path": get_data_path("arxiv", "arxiv_papers_latest.json"),
        "name": "Latest Papers",
        "icon": "📄",
        "description": "Most recent ArXiv papers across all categories"
    },
    "arxiv_machine_learning": {
        "path": get_data_path("arxiv", "arxiv_machine_learning_20250624_050511.json"),
        "name": "Machine Learning",
        "icon": "🤖",
        "description": "Papers focused on machine learning techniques and applications"
    },
    "arxiv_computer_vision": {
        "path": get_data_path("arxiv", "arxiv_computer_vision_20250624_050511.json"),
        "name": "Computer Vision",
        "icon": "👁️",
        "description": "Computer vision and image processing research"
    },
    "arxiv_natural_language": {
        "path": get_data_path("arxiv", "arxiv_natural_language_20250624_050511.json"),
        "name": "Natural Language",
        "icon": "💬",
        "description": "Natural language processing and computational linguistics"
    },
    "arxiv_neural_networks": {
        "path": get_data_path("arxiv", "arxiv_neural_networks_20250624_050511.json"),
        "name": "Neural Networks",
        "icon": "🧠",
        "description": "Neural network architectures and deep learning"
    },
    "arxiv_robotics": {
        "path": get_data_path("arxiv", "arxiv_robotics_20250624_050511.json"),
        "name": "Robotics",
        "icon": "🤖",
        "description": "Robotics research and autonomous systems"
    },
    "arxiv_reinforcement_learning": {
        "path": get_data_path("arxiv", "arxiv_reinforcement_learning_20250624_050511.json"),
        "name": "Reinforcement Learning",
        "icon": "🎯",
        "description": "Reinforcement learning algorithms and applications"
    }
}

def load_arxiv_data(file_path):
    """Load and parse ArXiv data from JSON file"""
    try:
        if not file_exists(file_path):
            logger.warning(f"ArXiv data file not found: {file_path}")
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            processed_data = []
            for paper in data:
                processed_paper = process_arxiv_paper(paper)
                if processed_paper:
                    processed_data.append(processed_paper)
            return processed_data
        
        return []
    except Exception as e:
        logger.error(f"Error loading ArXiv data from {file_path}: {e}")
        return []

def process_arxiv_paper(paper):
    """Process individual ArXiv paper with enhanced metadata"""
    try:
        # Extract and clean title
        title = paper.get('title', 'Unknown Title').strip()
        
        # Extract abstract with length limit
        abstract = paper.get('abstract', 'No abstract available').strip()
        abstract_preview = abstract[:300] + '...' if len(abstract) > 300 else abstract
        
        # Parse publication date
        pub_date = None
        for date_field in ['published_date', 'published', 'date']:
            if date_field in paper:
                pub_date = parse_date_universal(paper[date_field])
                break
        
        # Process authors
        authors = paper.get('authors', [])
        if isinstance(authors, str):
            authors = [authors]
        authors_str = ', '.join(authors[:3])  # Show first 3 authors
        if len(authors) > 3:
            authors_str += f' +{len(authors) - 3} more'
        
        # Process categories
        categories = paper.get('categories', [])
        if isinstance(categories, str):
            categories = [categories]
        
        # Map categories to human-readable names
        category_names = []
        for cat in categories:
            category_names.append(ARXIV_CATEGORY_MAPPING.get(cat, cat))
        
        primary_category = paper.get('primary_category', categories[0] if categories else 'Unknown')
        primary_category_name = ARXIV_CATEGORY_MAPPING.get(primary_category, primary_category)
        
        # Extract search/classification category if available
        search_category = paper.get('search_category', paper.get('classification', 'general'))
        
        return {
            'title': title,
            'abstract': abstract,
            'abstract_preview': abstract_preview,
            'authors': authors,
            'authors_str': authors_str,
            'published_date': pub_date,
            'categories': categories,
            'category_names': category_names,
            'primary_category': primary_category,
            'primary_category_name': primary_category_name,
            'search_category': search_category,
            'arxiv_id': paper.get('arxiv_id', paper.get('id', 'Unknown')),
            'url': paper.get('url', paper.get('link', '#')),
            'doi': paper.get('doi', None),
            'journal_reference': paper.get('journal_reference', None),
            'citation_count': paper.get('citation_count', 0),
            'source': paper.get('source', 'arxiv'),
            'raw_data': paper
        }
    except Exception as e:
        logger.error(f"Error processing ArXiv paper: {e}")
        return None

# Load all ArXiv data
ARXIV_DATA = {}
for source_id, config in ARXIV_SOURCES_CONFIG.items():
    data = load_arxiv_data(config["path"])
    ARXIV_DATA[source_id] = data
    logger.info(f"Loaded {len(data)} papers for {config['name']}")

# Combine all data for analytics
ALL_ARXIV_PAPERS = []
for data in ARXIV_DATA.values():
    ALL_ARXIV_PAPERS.extend(data)

def create_category_distribution_chart():
    """Create a pie chart showing distribution of paper categories"""
    if not ALL_ARXIV_PAPERS:
        return html.Div("No data available for visualization")
    
    # Count categories
    category_counts = Counter()
    for paper in ALL_ARXIV_PAPERS:
        category_counts[paper['primary_category_name']] += 1
    
    # Get top 10 categories
    top_categories = dict(category_counts.most_common(10))
    
    fig = px.pie(
        values=list(top_categories.values()),
        names=list(top_categories.keys()),
        title="Distribution of Research Categories",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#CDD6F4',
        title_font_color='#A37FFF'
    )
    
    return dcc.Graph(figure=fig)

def create_timeline_chart():
    """Create a timeline chart showing publication trends"""
    if not ALL_ARXIV_PAPERS:
        return html.Div("No data available for timeline")
    
    # Group papers by date
    papers_with_dates = [p for p in ALL_ARXIV_PAPERS if p['published_date']]
    if not papers_with_dates:
        return html.Div("No date information available")
    
    # Create daily counts
    date_counts = Counter()
    for paper in papers_with_dates:
        date_str = paper['published_date'].strftime('%Y-%m-%d')
        date_counts[date_str] += 1
    
    dates = list(date_counts.keys())
    counts = list(date_counts.values())
    
    fig = go.Figure(data=go.Scatter(
        x=dates,
        y=counts,
        mode='lines+markers',
        name='Papers Published',
        line=dict(color='#A37FFF', width=2),
        marker=dict(color='#A37FFF', size=6)
    ))
    
    fig.update_layout(
        title="Publication Timeline",
        xaxis_title="Date",
        yaxis_title="Number of Papers",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#CDD6F4',
        title_font_color='#A37FFF'
    )
    
    return dcc.Graph(figure=fig)

def create_source_summary_cards():
    """Create summary cards for each ArXiv source"""
    cards = []
    
    for source_id, config in ARXIV_SOURCES_CONFIG.items():
        data = ARXIV_DATA[source_id]
        paper_count = len(data)
        
        # Get latest publication date
        latest_date = "No data"
        if data:
            dates = [p['published_date'] for p in data if p['published_date']]
            if dates:
                latest_date = max(dates).strftime("%Y-%m-%d")
        
        # Status color
        status_color = "success" if paper_count > 0 else "secondary"
        
        card = dbc.Card([
            dbc.CardHeader([
                html.H6([
                    html.Span(config["icon"], className="me-2"),
                    config["name"]
                ], className="mb-0"),
                dbc.Badge(f"{paper_count} papers", color=status_color, className="float-end")
            ]),
            dbc.CardBody([
                html.P(config["description"], className="small text-muted mb-2"),
                html.Div([
                    html.Strong("Latest: "),
                    html.Span(latest_date, className="text-muted small")
                ]),
                dbc.Button(
                    f"View {config['name']}",
                    id=f"btn-arxiv-{source_id}",
                    color="outline-primary",
                    size="sm",
                    className="w-100 mt-2"
                )
            ])
        ], className="mb-3 h-100")
        
        cards.append(dbc.Col(card, md=4, lg=3))
    
    return cards

def create_papers_table(source_id, papers):
    """Create a detailed table for papers"""
    if not papers:
        return dbc.Alert(
            "No papers available for this category.",
            color="info",
            className="text-center"
        )
    
    # Convert to DataFrame
    df_data = []
    for paper in papers:
        row = {
            'Title': paper['title'][:100] + '...' if len(paper['title']) > 100 else paper['title'],
            'Authors': paper['authors_str'],
            'Category': paper['primary_category_name'],
            'Published': paper['published_date'].strftime("%Y-%m-%d") if paper['published_date'] else 'N/A',
            'ArXiv ID': paper['arxiv_id'],
            'Abstract': paper['abstract_preview'],
            'URL': paper['url']
        }
        df_data.append(row)
    
    df = pd.DataFrame(df_data)
    
    # Create DataTable columns
    columns = [
        {"name": "Title", "id": "Title", "type": "text"},
        {"name": "Authors", "id": "Authors", "type": "text"},
        {"name": "Category", "id": "Category", "type": "text"},
        {"name": "Published", "id": "Published", "type": "text"},
        {"name": "ArXiv ID", "id": "ArXiv ID", "type": "text"},
        {"name": "Abstract", "id": "Abstract", "type": "text"},
        {
            "name": "Link",
            "id": "URL",
            "type": "text",
            "presentation": "markdown"
        }
    ]
    
    # Convert URLs to markdown links
    df['URL'] = df.apply(lambda row: f"[📄 ArXiv]({row['URL']})" if row['URL'] != '#' else 'N/A', axis=1)
    
    return dash_table.DataTable(
        data=df.to_dict('records'),
        columns=columns,
        page_size=10,
        sort_action="native",
        filter_action="native",
        style_cell={
            'textAlign': 'left',
            'padding': '8px',
            'fontFamily': 'Poppins, sans-serif',
            'maxWidth': '200px',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis'
        },
        style_header={
            'backgroundColor': '#3C3970',
            'color': '#E2E8F0',
            'fontWeight': 'bold'
        },
        style_data={
            'backgroundColor': '#2D2B55',
            'color': '#CDD6F4',
            'whiteSpace': 'normal',
            'height': 'auto'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#252343'
            }
        ],
        tooltip_data=[
            {
                'Abstract': {'value': paper['abstract'], 'type': 'markdown'}
                for paper in papers
            }
        ],
        tooltip_duration=None
    )

def render_arxiv_research_tab():
    """Main render function for the ArXiv Research tab"""
    
    total_papers = len(ALL_ARXIV_PAPERS)
    total_categories = len(set(p['primary_category_name'] for p in ALL_ARXIV_PAPERS))
    active_sources = sum(1 for data in ARXIV_DATA.values() if len(data) > 0)
    
    return html.Div([
        # Header with statistics
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="fas fa-graduation-cap me-2"),
                    "ArXiv Research Papers"
                ], className="text-primary mb-3"),
                
                # Summary statistics
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(total_papers, className="text-primary mb-0"),
                                html.P("Total Papers", className="text-muted small mb-0")
                            ])
                        ])
                    ], md=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(total_categories, className="text-success mb-0"),
                                html.P("Research Categories", className="text-muted small mb-0")
                            ])
                        ])
                    ], md=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(active_sources, className="text-info mb-0"),
                                html.P("Active Sources", className="text-muted small mb-0")
                            ])
                        ])
                    ], md=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4("Live", className="text-warning mb-0"),
                                html.P("Status", className="text-muted small mb-0")
                            ])
                        ])
                    ], md=3)
                ], className="mb-4")
            ])
        ]),
        
        # Analytics charts
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Category Distribution", className="mb-0")),
                    dbc.CardBody([
                        create_category_distribution_chart()
                    ])
                ])
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Publication Timeline", className="mb-0")),
                    dbc.CardBody([
                        create_timeline_chart()
                    ])
                ])
            ], md=6)
        ], className="mb-4"),
        
        # Source summary cards
        html.H4("Research Categories", className="text-primary mb-3"),
        dbc.Row(create_source_summary_cards(), className="mb-4"),
        
        # Data display area
        html.Div(id="arxiv-data-display"),
        
        # Storage for selected source
        dcc.Store(id="selected-arxiv-source")
    ])

def register_arxiv_callbacks(app):
    """Register callbacks for the ArXiv Research tab"""
    
    # Create callbacks for each source button
    for source_id in ARXIV_SOURCES_CONFIG.keys():
        @callback(
            Output("arxiv-data-display", "children"),
            Output("selected-arxiv-source", "data"),
            Input(f"btn-arxiv-{source_id}", "n_clicks"),
            prevent_initial_call=True
        )
        def display_arxiv_data(n_clicks, source_id=source_id):
            if n_clicks:
                config = ARXIV_SOURCES_CONFIG[source_id]
                papers = ARXIV_DATA[source_id]
                
                return html.Div([
                    html.Hr(),
                    html.H4([
                        html.Span(config["icon"], className="me-2"),
                        f"{config['name']} Papers"
                    ], className="text-primary mb-3"),
                    create_papers_table(source_id, papers)
                ]), source_id
            
            return html.Div(), None

if __name__ == "__main__":
    print("ArXiv Research Tab - Data Summary:")
    for source_id, config in ARXIV_SOURCES_CONFIG.items():
        paper_count = len(ARXIV_DATA[source_id])
        print(f"  {config['name']}: {paper_count} papers")
    
    total = len(ALL_ARXIV_PAPERS)
    categories = len(set(p['primary_category_name'] for p in ALL_ARXIV_PAPERS))
    print(f"  Total: {total} papers across {categories} categories")