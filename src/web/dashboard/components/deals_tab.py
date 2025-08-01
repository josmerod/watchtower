"""
Comprehensive Deals Dashboard Tab
Aggregates all deal-related ETLs including bargain deals, software, books, travel, etc.
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

# Comprehensive deals configuration
DEALS_SOURCES_CONFIG = {
    "bargain_deals": {
        "path": get_data_path("deals", "bargain_deals.json"),
        "name": "Bargain Deals",
        "icon": "💰",
        "category": "General",
        "color": "success",
        "description": "Best bargain deals across multiple platforms and categories"
    },
    "software_deals": {
        "path": get_data_path("deals", "software_deals.json"),
        "name": "Software Deals",
        "icon": "💻",
        "category": "Technology",
        "color": "primary",
        "description": "Software licenses, apps, and development tools on sale"
    },
    "book_deals": {
        "path": get_data_path("deals", "book_deals.json"),
        "name": "Book Deals",
        "icon": "📚",
        "category": "Education",
        "color": "info",
        "description": "eBooks, audiobooks, and physical book deals"
    },
    "educational_deals": {
        "path": get_data_path("deals", "educational_deals.json"),
        "name": "Educational Deals",
        "icon": "🎓",
        "category": "Education",
        "color": "warning",
        "description": "Online courses, training programs, and educational resources"
    },
    "travel_deals": {
        "path": get_data_path("deals", "travel_deals.json"),
        "name": "Travel Deals",
        "icon": "✈️",
        "category": "Travel",
        "color": "info",
        "description": "Flight deals, hotel discounts, and travel packages"
    },
    "crypto_finance_deals": {
        "path": get_data_path("deals", "crypto_finance_deals.json"),
        "name": "Crypto & Finance",
        "icon": "₿",
        "category": "Finance",
        "color": "warning",
        "description": "Cryptocurrency tools, trading platforms, and finance apps"
    },
    "fashion_retail_deals": {
        "path": get_data_path("deals", "fashion_retail_deals.json"),
        "name": "Fashion & Retail",
        "icon": "👕",
        "category": "Retail",
        "color": "danger",
        "description": "Clothing, accessories, and retail merchandise deals"
    },
    "health_fitness_deals": {
        "path": get_data_path("deals", "health_fitness_deals.json"),
        "name": "Health & Fitness",
        "icon": "💪",
        "category": "Health",
        "color": "success",
        "description": "Health supplements, fitness equipment, and wellness products"
    },
    "music_deals": {
        "path": get_data_path("deals", "music_deals.json"),
        "name": "Music Deals",
        "icon": "🎵",
        "category": "Entertainment",
        "color": "primary",
        "description": "Music software, instruments, and audio equipment deals"
    },
    "bundle_deals": {
        "path": get_data_path("deals", "bundle_deals.json"),
        "name": "Bundle Deals",
        "icon": "📦",
        "category": "Bundles",
        "color": "secondary",
        "description": "Software bundles, game bundles, and multi-item deal packages"
    }
}

def load_deals_data(file_path):
    """Load and parse deals data from JSON file"""
    try:
        if not file_exists(file_path):
            logger.warning(f"Deals data file not found: {file_path}")
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            processed_data = []
            for deal in data:
                processed_deal = process_deal_item(deal)
                if processed_deal:
                    processed_data.append(processed_deal)
            return processed_data
        
        return []
    except Exception as e:
        logger.error(f"Error loading deals data from {file_path}: {e}")
        return []

def process_deal_item(deal):
    """Process individual deal item with standardized fields"""
    try:
        # Extract common fields
        title = deal.get('title', deal.get('name', deal.get('product_name', 'Unknown Deal')))
        description = deal.get('description', deal.get('summary', 'No description available'))
        
        # Price information
        original_price = deal.get('original_price', deal.get('regular_price', 0))
        current_price = deal.get('current_price', deal.get('sale_price', deal.get('price', 0)))
        
        # Calculate savings if not provided
        discount_percentage = deal.get('discount_percentage', 0)
        savings = deal.get('savings', 0)
        
        if original_price and current_price and original_price > current_price:
            if not discount_percentage:
                discount_percentage = ((original_price - current_price) / original_price) * 100
            if not savings:
                savings = original_price - current_price
        
        # Deal quality metrics
        deal_rating = deal.get('deal_rating', deal.get('rating', 0))
        bargain_score = deal.get('bargain_score', deal.get('score', 0))
        
        # Urgency and timing
        urgency = deal.get('urgency', 'low')
        expires_at = None
        if 'expires_at' in deal or 'expiry_date' in deal:
            expires_at = parse_date_universal(deal.get('expires_at', deal.get('expiry_date')))
        
        # Platform and store info
        platform = deal.get('platform', deal.get('source', 'Unknown'))
        store_name = deal.get('store_name', deal.get('store', deal.get('retailer', platform)))
        
        # Categories and tags
        category = deal.get('category', 'general')
        tags = deal.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
        
        return {
            'title': title,
            'description': description[:150] + '...' if len(description) > 150 else description,
            'original_price': float(original_price) if original_price else 0,
            'current_price': float(current_price) if current_price else 0,
            'savings': float(savings) if savings else 0,
            'discount_percentage': float(discount_percentage) if discount_percentage else 0,
            'deal_rating': float(deal_rating) if deal_rating else 0,
            'bargain_score': float(bargain_score) if bargain_score else 0,
            'urgency': urgency,
            'platform': platform,
            'store_name': store_name,
            'category': category,
            'tags': tags,
            'url': deal.get('url', deal.get('link', '#')),
            'expires_at': expires_at,
            'raw_data': deal
        }
    except Exception as e:
        logger.error(f"Error processing deal item: {e}")
        return None

# Load all deals data
DEALS_DATA = {}
for source_id, config in DEALS_SOURCES_CONFIG.items():
    data = load_deals_data(config["path"])
    DEALS_DATA[source_id] = data
    logger.info(f"Loaded {len(data)} deals for {config['name']}")

# Combine all deals for analytics
ALL_DEALS = []
for source_id, data in DEALS_DATA.items():
    for deal in data:
        deal['source_category'] = DEALS_SOURCES_CONFIG[source_id]['category']
        deal['source_name'] = DEALS_SOURCES_CONFIG[source_id]['name']
        ALL_DEALS.append(deal)

def create_deals_distribution_chart():
    """Create a bar chart showing distribution of deals by category"""
    if not ALL_DEALS:
        return html.Div("No deals data available for visualization")
    
    # Count deals by source category
    category_counts = Counter()
    for deal in ALL_DEALS:
        category_counts[deal['source_category']] += 1
    
    categories = list(category_counts.keys())
    counts = list(category_counts.values())
    
    fig = px.bar(
        x=categories,
        y=counts,
        title="Deals Distribution by Category",
        labels={'x': 'Category', 'y': 'Number of Deals'},
        color=counts,
        color_continuous_scale='Viridis'
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#CDD6F4',
        title_font_color='#A37FFF'
    )
    
    return dcc.Graph(figure=fig)

def create_savings_distribution_chart():
    """Create a histogram showing distribution of savings amounts"""
    if not ALL_DEALS:
        return html.Div("No deals data available")
    
    # Filter deals with valid savings data
    deals_with_savings = [deal for deal in ALL_DEALS if deal['discount_percentage'] > 0]
    
    if not deals_with_savings:
        return html.Div("No savings data available")
    
    discount_percentages = [deal['discount_percentage'] for deal in deals_with_savings]
    
    fig = px.histogram(
        x=discount_percentages,
        nbins=20,
        title="Distribution of Discount Percentages",
        labels={'x': 'Discount Percentage (%)', 'y': 'Number of Deals'},
        color_discrete_sequence=['#A37FFF']
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#CDD6F4',
        title_font_color='#A37FFF'
    )
    
    return dcc.Graph(figure=fig)

def create_deals_summary_cards():
    """Create summary cards for each deals source"""
    cards = []
    
    # Sort by number of deals (descending)
    sorted_sources = sorted(
        DEALS_SOURCES_CONFIG.items(),
        key=lambda x: len(DEALS_DATA[x[0]]),
        reverse=True
    )
    
    for source_id, config in sorted_sources:
        data = DEALS_DATA[source_id]
        deal_count = len(data)
        
        # Calculate average discount
        avg_discount = 0
        if data:
            valid_discounts = [d['discount_percentage'] for d in data if d['discount_percentage'] > 0]
            if valid_discounts:
                avg_discount = sum(valid_discounts) / len(valid_discounts)
        
        # Calculate total savings
        total_savings = sum(d['savings'] for d in data if d['savings'] > 0)
        
        # Status color
        status_color = config['color'] if deal_count > 0 else "secondary"
        
        card = dbc.Card([
            dbc.CardHeader([
                html.H6([
                    html.Span(config["icon"], className="me-2"),
                    config["name"]
                ], className="mb-0"),
                dbc.Badge(f"{deal_count} deals", color=status_color, className="float-end")
            ]),
            dbc.CardBody([
                html.P(config["description"], className="small text-muted mb-2"),
                html.Div([
                    html.Strong("Avg Discount: "),
                    html.Span(f"{avg_discount:.1f}%", className="text-success")
                ], className="mb-1"),
                html.Div([
                    html.Strong("Total Savings: "),
                    html.Span(f"${total_savings:.0f}", className="text-warning")
                ], className="mb-2"),
                dbc.Button(
                    f"View {config['name']}",
                    id=f"btn-deals-{source_id}",
                    color="outline-primary",
                    size="sm",
                    className="w-100"
                )
            ])
        ], className="mb-3 h-100")
        
        cards.append(dbc.Col(card, md=6, lg=4))
    
    return cards

def create_deals_table(source_id, deals):
    """Create a detailed table for deals"""
    if not deals:
        return dbc.Alert(
            "No deals available for this category.",
            color="info",
            className="text-center"
        )
    
    # Sort deals by discount percentage (descending)
    sorted_deals = sorted(deals, key=lambda x: x['discount_percentage'], reverse=True)
    
    # Convert to DataFrame
    df_data = []
    for deal in sorted_deals:
        # Format prices
        original_price_str = f"${deal['original_price']:.2f}" if deal['original_price'] > 0 else "N/A"
        current_price_str = f"${deal['current_price']:.2f}" if deal['current_price'] > 0 else "Free"
        savings_str = f"${deal['savings']:.2f}" if deal['savings'] > 0 else "N/A"
        discount_str = f"{deal['discount_percentage']:.1f}%" if deal['discount_percentage'] > 0 else "N/A"
        
        # Urgency indicator
        urgency_badge = "🔴" if deal['urgency'] == 'high' else "🟡" if deal['urgency'] == 'medium' else "🟢"
        
        row = {
            'Title': deal['title'][:80] + '...' if len(deal['title']) > 80 else deal['title'],
            'Description': deal['description'],
            'Original Price': original_price_str,
            'Current Price': current_price_str,
            'Savings': savings_str,
            'Discount': discount_str,
            'Rating': f"{deal['deal_rating']:.1f}" if deal['deal_rating'] > 0 else "N/A",
            'Store': deal['store_name'],
            'Urgency': f"{urgency_badge} {deal['urgency'].title()}",
            'URL': deal['url']
        }
        df_data.append(row)
    
    df = pd.DataFrame(df_data)
    
    # Create DataTable columns
    columns = [
        {"name": "Title", "id": "Title", "type": "text"},
        {"name": "Description", "id": "Description", "type": "text"},
        {"name": "Original Price", "id": "Original Price", "type": "text"},
        {"name": "Current Price", "id": "Current Price", "type": "text"},
        {"name": "Savings", "id": "Savings", "type": "text"},
        {"name": "Discount", "id": "Discount", "type": "text"},
        {"name": "Rating", "id": "Rating", "type": "text"},
        {"name": "Store", "id": "Store", "type": "text"},
        {"name": "Urgency", "id": "Urgency", "type": "text"},
        {
            "name": "Link",
            "id": "URL",
            "type": "text",
            "presentation": "markdown"
        }
    ]
    
    # Convert URLs to markdown links
    df['URL'] = df.apply(lambda row: f"[🛒 Get Deal]({row['URL']})" if row['URL'] != '#' else 'N/A', axis=1)
    
    return dash_table.DataTable(
        data=df.to_dict('records'),
        columns=columns,
        page_size=15,
        sort_action="native",
        filter_action="native",
        style_cell={
            'textAlign': 'left',
            'padding': '8px',
            'fontFamily': 'Poppins, sans-serif',
            'maxWidth': '150px',
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
            },
            # Highlight high discount deals
            {
                'if': {'filter_query': '{Discount} contains %', 'column_id': 'Discount'},
                'backgroundColor': '#3C5A3C',
                'color': '#AEF4AE'
            }
        ]
    )

def render_deals_tab():
    """Main render function for the Deals dashboard tab"""
    
    total_deals = len(ALL_DEALS)
    total_categories = len(set(deal['source_category'] for deal in ALL_DEALS))
    active_sources = sum(1 for data in DEALS_DATA.values() if len(data) > 0)
    
    # Calculate total potential savings
    total_savings = sum(deal['savings'] for deal in ALL_DEALS if deal['savings'] > 0)
    
    return html.Div([
        # Header with statistics
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="fas fa-tags me-2"),
                    "Comprehensive Deals Dashboard"
                ], className="text-primary mb-3"),
                
                # Summary statistics
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(total_deals, className="text-primary mb-0"),
                                html.P("Total Deals", className="text-muted small mb-0")
                            ])
                        ])
                    ], md=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(f"${total_savings:.0f}", className="text-success mb-0"),
                                html.P("Total Savings", className="text-muted small mb-0")
                            ])
                        ])
                    ], md=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(total_categories, className="text-info mb-0"),
                                html.P("Deal Categories", className="text-muted small mb-0")
                            ])
                        ])
                    ], md=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(active_sources, className="text-warning mb-0"),
                                html.P("Active Sources", className="text-muted small mb-0")
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
                    dbc.CardHeader(html.H5("Deals by Category", className="mb-0")),
                    dbc.CardBody([
                        create_deals_distribution_chart()
                    ])
                ])
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Discount Distribution", className="mb-0")),
                    dbc.CardBody([
                        create_savings_distribution_chart()
                    ])
                ])
            ], md=6)
        ], className="mb-4"),
        
        # Deals categories
        html.H4("Deal Categories", className="text-primary mb-3"),
        dbc.Row(create_deals_summary_cards(), className="mb-4"),
        
        # Data display area
        html.Div(id="deals-data-display"),
        
        # Storage for selected source
        dcc.Store(id="selected-deals-source")
    ])

def register_deals_callbacks(app):
    """Register callbacks for the Deals dashboard tab"""
    
    # Create callbacks for each source button
    for source_id in DEALS_SOURCES_CONFIG.keys():
        @callback(
            Output("deals-data-display", "children"),
            Output("selected-deals-source", "data"),
            Input(f"btn-deals-{source_id}", "n_clicks"),
            prevent_initial_call=True
        )
        def display_deals_data(n_clicks, source_id=source_id):
            if n_clicks:
                config = DEALS_SOURCES_CONFIG[source_id]
                deals = DEALS_DATA[source_id]
                
                return html.Div([
                    html.Hr(),
                    html.H4([
                        html.Span(config["icon"], className="me-2"),
                        f"{config['name']} Deals"
                    ], className="text-primary mb-3"),
                    create_deals_table(source_id, deals)
                ]), source_id
            
            return html.Div(), None

if __name__ == "__main__":
    print("Deals Dashboard Tab - Data Summary:")
    for source_id, config in DEALS_SOURCES_CONFIG.items():
        deal_count = len(DEALS_DATA[source_id])
        print(f"  {config['name']}: {deal_count} deals")
    
    total = len(ALL_DEALS)
    categories = len(set(deal['source_category'] for deal in ALL_DEALS))
    total_savings = sum(deal['savings'] for deal in ALL_DEALS if deal['savings'] > 0)
    print(f"  Total: {total} deals across {categories} categories, ${total_savings:.0f} in potential savings")