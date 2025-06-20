import os
import json
import pandas as pd
from datetime import datetime, timezone
import glob # For finding the latest file
import re
import dash
from dash import html, dcc, Input, Output, State, Patch, dash_table
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

# --- Constants ---
AKS_DATA_BASE_PATH = "../../../data/allkeyshop_games/output/" # Relative to this file
ALLKEYSHOP_DF = pd.DataFrame()
AKS_DATA_LOADED = False

# --- Price/Discount Parsing (can reuse or adapt from games_tab.py if needed) ---
def parse_aks_price(price_str):
    if pd.isna(price_str) or price_str is None: return None
    if isinstance(price_str, (int, float)): return float(price_str)

    s_price = str(price_str).strip().lower()
    if not s_price: return None
    if 'free' in s_price or 'gratis' in s_price: return 0.0

    # Remove currency symbols, keep digits, decimal point, and comma
    # Handles "€12,34", "$12.34", "12.34€"
    # First, remove non-numeric except common currency symbols and separators
    s_price = re.sub(r"[^\d\.,€$£]", "", s_price)
    # Remove currency symbols
    s_price = re.sub(r"[€$£]", "", s_price)

    # Standardize decimal separator
    if ',' in s_price and '.' in s_price: # e.g., 1.234,56 (Euro style)
        s_price = s_price.replace('.', '')
        s_price = s_price.replace(',', '.')
    elif ',' in s_price: # e.g., 12,34
        s_price = s_price.replace(',', '.')

    try:
        return float(s_price)
    except ValueError:
        # print(f"Warning (AKS): Could not parse price: {price_str} -> {s_price}")
        return None

def parse_aks_discount(discount_str):
    if pd.isna(discount_str) or not discount_str: return None
    s_discount = str(discount_str).replace('%', '').strip()
    try:
        return float(s_discount)
    except ValueError:
        # print(f"Warning (AKS): Could not parse discount: {discount_str}")
        return None

# --- Data Loading ---
def load_allkeyshop_data():
    global ALLKEYSHOP_DF, AKS_DATA_LOADED

    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    actual_data_path_dir = os.path.normpath(os.path.join(current_script_dir, AKS_DATA_BASE_PATH))

    if not os.path.exists(actual_data_path_dir) or not os.path.isdir(actual_data_path_dir):
        print(f"Warning (AKS): Data directory not found: {actual_data_path_dir}")
        ALLKEYSHOP_DF = pd.DataFrame()
        AKS_DATA_LOADED = True # Prevent reload attempts
        return

    # Find the latest file
    files = glob.glob(os.path.join(actual_data_path_dir, "allkeyshop_games_*.json"))
    latest_file_plain = os.path.join(actual_data_path_dir, "latest_allkeyshop_games.json")

    if os.path.exists(latest_file_plain):
        file_to_load = latest_file_plain
    elif files:
        files.sort(key=os.path.getmtime, reverse=True)
        file_to_load = files[0]
    else:
        print(f"Warning (AKS): No data files found in {actual_data_path_dir}")
        ALLKEYSHOP_DF = pd.DataFrame()
        AKS_DATA_LOADED = True
        return

    print(f"Info (AKS): Loading data from {file_to_load}")
    try:
        df = pd.read_json(file_to_load)
    except ValueError as e:
        print(f"Error (AKS): Could not decode JSON from {file_to_load}. Error: {e}")
        ALLKEYSHOP_DF = pd.DataFrame()
        AKS_DATA_LOADED = True
        return
    except Exception as e:
        print(f"Error (AKS): Failed to read or process {file_to_load}. Error: {e}")
        ALLKEYSHOP_DF = pd.DataFrame()
        AKS_DATA_LOADED = True
        return

    if df.empty:
        print(f"Info (AKS): File {file_to_load} was empty.")
        ALLKEYSHOP_DF = pd.DataFrame()
        AKS_DATA_LOADED = True
        return

    # Standardize columns
    # Example columns: 'title', 'url', 'currentPrice', 'originalPrice', 'discountPercentage', 'storeName', 'dealScore'
    df.rename(columns={
        'name': 'title', # Common alternative for title
        'currentPrice': 'current_price',
        'originalPrice': 'original_price',
        'discountPercentage': 'discount_percentage',
        'storeName': 'store_name',
        'dealScore': 'deal_score',
        'link': 'url' # If 'link' is used for URL
    }, inplace=True)

    expected_cols = ['title', 'url', 'current_price', 'original_price', 'discount_percentage', 'store_name', 'deal_score']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None
            print(f"Info (AKS): Column '{col}' not found, added as None.")

    df['current_price_numeric'] = df['current_price'].apply(parse_aks_price)
    df['original_price_numeric'] = df['original_price'].apply(parse_aks_price)
    df['discount_numeric'] = df['discount_percentage'].apply(parse_aks_discount)
    df['deal_score_numeric'] = pd.to_numeric(df['deal_score'], errors='coerce')

    # Remove rows where essential numeric data might be NaN after parsing if critical
    # df.dropna(subset=['current_price_numeric', 'title', 'url'], inplace=True)

    ALLKEYSHOP_DF = df
    AKS_DATA_LOADED = True
    print(f"Info (AKS): Loaded {len(ALLKEYSHOP_DF)} deals from AllKeyShop.")

load_allkeyshop_data()

# --- Helper Functions for Sub-Tabs ---
def create_aks_table(df_subset, table_id=None):
    """Helper function to create a dbc.Table from a DataFrame subset."""
    if df_subset.empty:
        return dbc.Alert("No deals match the current criteria.", color="info")

    table_header = [
        html.Thead(html.Tr([
            html.Th("Title"),
            html.Th("Store"),
            html.Th("Price"),
            html.Th("Old Price"),
            html.Th("Discount"),
            html.Th("Deal Score")
        ]))
    ]
    table_body_rows = []
    for _, row in df_subset.iterrows():
        price_str = f"€{row.get('current_price_numeric', 0.0):.2f}" if pd.notna(row.get('current_price_numeric')) else "N/A"
        if row.get('current_price_numeric', -1) == 0: price_str = "Free"

        old_price_str = f"€{row.get('original_price_numeric', 0.0):.2f}" if pd.notna(row.get('original_price_numeric')) else "N/A"
        discount_str = f"{int(row.get('discount_numeric', 0))}%" if pd.notna(row.get('discount_numeric')) else "N/A"
        score_str = f"{int(row.get('deal_score_numeric', 0))}/100" if pd.notna(row.get('deal_score_numeric')) else "N/A"

        table_body_rows.append(html.Tr([
            html.Td(html.A(row.get('title', 'N/A'), href=row.get('url'), target="_blank", rel="noopener noreferrer")),
            html.Td(row.get('store_name', 'N/A')),
            html.Td(price_str),
            html.Td(old_price_str),
            html.Td(discount_str),
            html.Td(score_str)
        ]))
    table_body = [html.Tbody(table_body_rows)]

    return dbc.Table(table_header + table_body, id=table_id if table_id else dash.no_update, striped=True, bordered=True, hover=True, responsive=True)

def render_best_deals_sub_tab(df_full):
    if df_full.empty: return dbc.Alert("No AllKeyShop data available.", color="info", className="mt-3")

    # Define "best deals": High discount, high score, or free
    # This logic can be refined
    best_deals_df = df_full[
        (df_full['discount_numeric'] >= 75) |
        (df_full['deal_score_numeric'] >= 85) |
        (df_full['current_price_numeric'] == 0)
    ].copy()

    # Sort by a combination or primarily by score/discount
    # For example, prioritize free, then high score, then high discount
    best_deals_df['sort_key'] = best_deals_df.apply(
        lambda x: (
            0 if x['current_price_numeric'] == 0 else 1, # Free items first
            -x.get('deal_score_numeric', 0),             # Then by highest deal score
            -x.get('discount_numeric', 0)                # Then by highest discount
        ), axis=1
    )
    best_deals_df = best_deals_df.sort_values('sort_key').head(20) # Display top 20

    if best_deals_df.empty:
        return dbc.Alert("No deals currently meet the 'best deals' criteria (e.g., >=75% discount, >=85 score, or Free).", color="info", className="mt-3")

    return html.Div(create_aks_table(best_deals_df, table_id="aks-best-deals-table"), className="mt-3")

def render_by_price_sub_tab(df_full): # df_full is ALLKEYSHOP_DF
    if df_full.empty: return dbc.Alert("No AllKeyShop data available for price filtering.", color="info", className="mt-3")

    price_ranges = [
        {"label": "Gratis", "lower": 0, "upper": 0, "id": "price-free"},
        {"label": "Menos de €10", "lower": 0.01, "upper": 10, "id": "price-under10"},
        {"label": "€10 - €29.99", "lower": 10, "upper": 29.99, "id": "price-10-30"},
        {"label": "€30 - €59.99", "lower": 30, "upper": 59.99, "id": "price-30-60"},
        {"label": "€60+", "lower": 60, "upper": float('inf'), "id": "price-over60"},
    ]

    price_tabs_children = []
    for pr in price_ranges:
        if pr['label'] == "Gratis": # Specific filter for free games
            range_df = df_full[df_full['current_price_numeric'] == 0].copy()
        else:
            range_df = df_full[
                (df_full['current_price_numeric'] >= pr['lower']) &
                (df_full['current_price_numeric'] <= pr['upper'])
            ].copy()

        range_df = range_df.sort_values(by=['discount_numeric', 'deal_score_numeric'], ascending=[False, False]).head(30) # Top 30 by discount, then score

        table_content = create_aks_table(range_df, table_id=f"aks-table-{pr['id']}")
        tab_content = html.Div(table_content if not range_df.empty else dbc.Alert(f"No hay juegos en el rango de precios: {pr['label']}", color="info", className="mt-2"), className="mt-2")

        price_tabs_children.append(
            dbc.Tab(label=pr['label'], tab_id=f"subtab-{pr['id']}", children=tab_content)
        )

    return dbc.Tabs(id="aks-by-price-nested-tabs", children=price_tabs_children, className="mt-3")


def render_explore_all_sub_tab(df):
    if df.empty: return dbc.Alert("No AllKeyShop data available to explore.", color="info", className="mt-3")
    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Input(id="aks-search-input", placeholder="Search by title..."), md=6, className="mb-2"),
            dbc.Col(dcc.Dropdown(
                id="aks-sort-dropdown",
                options=[
                    {'label': 'Sort by Best Deal Score', 'value': 'deal_score'},
                    {'label': 'Sort by Discount %', 'value': 'discount'},
                    {'label': 'Sort by Lowest Price', 'value': 'price_asc'},
                    {'label': 'Sort by Highest Price', 'value': 'price_desc'},
                    {'label': 'Sort by Title', 'value': 'title'},
                ],
                value='deal_score', placeholder="Sort by..."
            ), md=6, className="mb-2"),
        ]),
        html.Div(id="aks-table-container", className="mt-3"),
        dbc.Pagination(id="aks-pagination", max_value=1, active_page=1, className="mt-3 justify-content-center")
    ], className="mt-3")

# --- Main Layout ---
def render_allkeyshop_tab():
    if not AKS_DATA_LOADED or ALLKEYSHOP_DF.empty:
        return html.Div([
            html.H3("AllKeyShop Deals", className="mb-3"),
            dbc.Alert("AllKeyShop data could not be loaded or is empty. Please check data sources and ETLs.", color="danger")
        ])

    # Summary Stats
    total_games = len(ALLKEYSHOP_DF)
    avg_price = ALLKEYSHOP_DF['current_price_numeric'].mean() if 'current_price_numeric' in ALLKEYSHOP_DF and ALLKEYSHOP_DF['current_price_numeric'].notna().any() else 0
    avg_discount = ALLKEYSHOP_DF['discount_numeric'].mean() if 'discount_numeric' in ALLKEYSHOP_DF and ALLKEYSHOP_DF['discount_numeric'].notna().any() else 0

    summary_stats = dbc.Row([
        dbc.Col(dbc.Card([dbc.CardHeader("Total Games Listed"), dbc.CardBody(f"{total_games:,}")], color="primary", inverse=True), md=4, className="mb-2"),
        dbc.Col(dbc.Card([dbc.CardHeader("Average Price"), dbc.CardBody(f"€{avg_price:.2f}")], color="info", inverse=True), md=4, className="mb-2"),
        dbc.Col(dbc.Card([dbc.CardHeader("Average Discount"), dbc.CardBody(f"{avg_discount:.0f}%")], color="success", inverse=True), md=4, className="mb-2"),
    ], className="mb-4")

    main_tabs = dbc.Tabs(id="aks-main-tabs", children=[
        dbc.Tab(label="Mejores Deals", tab_id="aks-best-deals", children=[render_best_deals_sub_tab(ALLKEYSHOP_DF)]),
        dbc.Tab(label="Por Precio", tab_id="aks-by-price", children=[render_by_price_sub_tab(ALLKEYSHOP_DF)]),
        dbc.Tab(label="Explorar Todo", tab_id="aks-explore-all", children=[render_explore_all_sub_tab(ALLKEYSHOP_DF)]),
    ])

    return html.Div([
        html.H3("AllKeyShop Deals", className="mb-3"),
        summary_stats,
        main_tabs
    ])

# --- Callbacks ---
PAGE_SIZE_EXPLORE_ALL = 15 # Number of items per page for the "Explore All" tab

def register_allkeyshop_callbacks(app):
    @app.callback(
        Output("aks-table-container", "children"),
        Output("aks-pagination", "max_value"),
        Output("aks-pagination", "active_page"), # Ensure pagination reflects current page
        Input("aks-search-input", "value"),
        Input("aks-sort-dropdown", "value"),
        Input("aks-pagination", "active_page")
    )
    def update_explore_all_table(search_term, sort_by, current_page):
        if not AKS_DATA_LOADED or ALLKEYSHOP_DF.empty:
            return dbc.Alert("AllKeyShop data is not available.", color="warning"), 1, 1

        df_filtered = ALLKEYSHOP_DF.copy()

        # Apply search filter (only on 'title' for simplicity now)
        if search_term:
            search_term_lower = search_term.lower()
            df_filtered = df_filtered[df_filtered['title'].str.lower().contains(search_term_lower, na=False)]

        # Apply sorting
        if sort_by == 'deal_score':
            df_filtered = df_filtered.sort_values(by='deal_score_numeric', ascending=False, na_position='last')
        elif sort_by == 'discount':
            df_filtered = df_filtered.sort_values(by='discount_numeric', ascending=False, na_position='last')
        elif sort_by == 'price_asc':
            df_filtered = df_filtered.sort_values(by='current_price_numeric', ascending=True, na_position='last')
        elif sort_by == 'price_desc':
            df_filtered = df_filtered.sort_values(by='current_price_numeric', ascending=False, na_position='last')
        elif sort_by == 'title':
            df_filtered = df_filtered.sort_values(by='title', ascending=True, na_position='last')

        if df_filtered.empty:
            return dbc.Alert("No deals match your search criteria.", color="info"), 1, 1

        # Pagination
        current_page = current_page if current_page else 1
        total_items = len(df_filtered)
        max_pages = (total_items + PAGE_SIZE_EXPLORE_ALL - 1) // PAGE_SIZE_EXPLORE_ALL

        start_idx = (current_page - 1) * PAGE_SIZE_EXPLORE_ALL
        end_idx = start_idx + PAGE_SIZE_EXPLORE_ALL
        df_paginated = df_filtered.iloc[start_idx:end_idx]

        table = create_aks_table(df_paginated, table_id="aks-explore-all-table")

        actual_page = min(current_page, max_pages) if max_pages > 0 else 1

        return table, max_pages if max_pages > 0 else 1, actual_page

    # Callback to reset pagination to page 1 when search or sort changes
    @app.callback(
        Output("aks-pagination", "active_page", allow_duplicate=True),
        Input("aks-search-input", "value"),
        Input("aks-sort-dropdown", "value"),
        prevent_initial_call=True
    )
    def reset_explore_all_pagination(_, __):
        return 1


if __name__ == '__main__':
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_allkeyshop_tab(), fluid=True, className="py-4")
    register_allkeyshop_callbacks(app_test) # Register callbacks for the test app

    print(f"AKS Test: Data loaded - {AKS_DATA_LOADED}, DataFrame empty - {ALLKEYSHOP_DF.empty}")
    if AKS_DATA_LOADED and not ALLKEYSHOP_DF.empty:
        print(ALLKEYSHOP_DF.head(2))
        # print(ALLKEYSHOP_DF.info())
    elif not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), AKS_DATA_BASE_PATH))):
         print(f"  Data directory missing: {os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), AKS_DATA_BASE_PATH))}")

    app_test.run_server(debug=True, port=8058)
