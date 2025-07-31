import json
import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from datetime import datetime, timezone
import os

# Import shared utilities
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_data_path, file_exists, parse_date_universal

# --- Data Loading ---

TRAVEL_SOURCES_CONFIG = {
    "gumroad": {"path": get_data_path("gumroad", "gumroad_products_latest.json"), "name": "Gumroad Products"},
    "viajeros_piratas": {"path": get_data_path("viajeros_piratas", "viajeros_piratas_latest.json"), "name": "Viajeros Piratas"},
}

def load_travel_data(source_key):
    """Load travel data from a specific source."""
    config = TRAVEL_SOURCES_CONFIG.get(source_key)
    if not config:
        return []
    
    file_path = config["path"]
    if not file_exists(file_path):
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Try common keys
                for key in ['items', 'products', 'deals', 'data', 'results']:
                    if key in data and isinstance(data[key], list):
                        return data[key]
                # If single item
                if any(k in data for k in ['title', 'name', 'url']):
                    return [data]
            return []
    except Exception as e:
        print(f"Error loading {source_key} data: {e}")
        return []

def create_travel_cards():
    """Create summary cards for travel data."""
    cards = []
    
    for source_key, config in TRAVEL_SOURCES_CONFIG.items():
        data = load_travel_data(source_key)
        count = len(data)
        
        # Calculate latest update
        latest_date = "No data"
        if data:
            dates = []
            for item in data:
                for date_field in ['date', 'timestamp', 'created_at', 'published_date']:
                    if date_field in item:
                        try:
                            dt = parse_date_universal(item[date_field])
                            if dt:
                                dates.append(dt)
                        except:
                            pass
            
            if dates:
                latest_date = max(dates).strftime("%Y-%m-%d")
        
        color = "success" if count > 0 else "secondary"
        
        card = dbc.Card(
            dbc.CardBody([
                html.H4(f"{count:,}", className=f"card-title text-{color}"),
                html.P(config["name"], className="card-text"),
                html.Small(f"Last update: {latest_date}", className="text-muted")
            ]),
            color=color, outline=True, className="mb-3"
        )
        cards.append(card)
    
    return cards

def create_travel_table(source_key):
    """Create travel data table for a specific source."""
    data = load_travel_data(source_key)
    config = TRAVEL_SOURCES_CONFIG.get(source_key, {})
    
    if not data:
        return html.Div([
            html.P(f"No {config.get('name', source_key)} data available.", 
                   className="text-muted text-center p-4")
        ])
    
    # Limit to 50 most recent items
    recent_data = data[:50]
    
    table_rows = []
    for item in recent_data:
        # Extract common fields
        title = item.get('title', item.get('name', item.get('product_name', 'Untitled')))
        
        url = item.get('url', item.get('link', '#'))
        
        # Price handling
        price = item.get('price', item.get('cost', item.get('value', 'N/A')))
        if isinstance(price, (int, float)):
            price = f"${price:.2f}"
        elif price and str(price).replace('.', '').replace('$', '').replace(',', '').isdigit():
            price = f"${float(str(price).replace('$', '').replace(',', '')):.2f}"
        
        # Date handling
        date_str = "Unknown"
        for date_field in ['date', 'timestamp', 'created_at', 'published_date']:
            if date_field in item:
                try:
                    dt = parse_date_universal(item[date_field])
                    if dt:
                        date_str = dt.strftime("%Y-%m-%d")
                        break
                except:
                    pass
        
        # Description
        description = item.get('description', item.get('summary', ''))[:200]
        if len(item.get('description', item.get('summary', ''))) > 200:
            description += '...'
        
        # Category/Tags
        category = item.get('category', item.get('type', item.get('tag', 'General')))
        
        row = html.Tr([
            html.Td([
                html.A(title, href=url, target="_blank", className="text-decoration-none"),
            ]),
            html.Td(price, className="text-success fw-bold"),
            html.Td(category, className="small"),
            html.Td(date_str, className="text-muted small"),
            html.Td(description, className="small text-muted")
        ])
        table_rows.append(row)
    
    table = dbc.Table([
        html.Thead([
            html.Tr([
                html.Th("Title/Product", style={"width": "25%"}),
                html.Th("Price", style={"width": "10%"}),
                html.Th("Category", style={"width": "15%"}),
                html.Th("Date", style={"width": "10%"}),
                html.Th("Description", style={"width": "40%"})
            ])
        ]),
        html.Tbody(table_rows)
    ], striped=True, bordered=True, hover=True, responsive=True, size="sm")
    
    return table

# --- Main Tab Function ---

def travel_tab():
    """Main travel/deals tab function."""
    
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H2("✈️ Travel & Digital Products", className="mb-3"),
                html.P("Travel deals, digital products, and marketplace intelligence", 
                       className="text-muted mb-4")
            ])
        ]),
        
        # Summary Cards
        dbc.Row([
            dbc.Col(card, md=6) for card in create_travel_cards()
        ], className="mb-4"),
        
        # Data Sections
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🛍️ Gumroad Products"),
                    dbc.CardBody([
                        create_travel_table("gumroad")
                    ])
                ])
            ], md=12, className="mb-4")
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🏴‍☠️ Viajeros Piratas - Travel Deals"),
                    dbc.CardBody([
                        create_travel_table("viajeros_piratas")
                    ])
                ])
            ], md=12)
        ])
    ], fluid=True)