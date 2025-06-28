import os
import json
import pandas as pd
from datetime import datetime, timezone
import dash
from dash import html, dcc, Input, Output, State, Patch
import dash_bootstrap_components as dbc
# Import shared utilities
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_data_path, file_exists, dir_exists

from dash.exceptions import PreventUpdate

# --- Constants ---
HOME_SERVER_DATA_PATH = get_data_path("home_server_trends", "home_server_trends_latest.json")
HOME_SERVER_DF = pd.DataFrame()
HOME_SERVER_DATA_LOADED = False
PAGE_SIZE_HOME_SERVER = 10

# --- Date Parsing Utility ---
def parse_hs_date(date_str):
    if pd.isna(date_str) or not date_str: return None
    try:
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc)
    except ValueError: pass
    common_formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%Y/%m/%d %H:%M:%S"]
    for fmt in common_formats:
        try:
            dt = datetime.strptime(str(date_str), fmt)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError: continue
    try:
        ts = float(date_str)
        if ts > 10000000000: ts /= 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except ValueError: pass
    print(f"Warning (HomeServer): Could not parse date: {date_str}")
    return None

# --- Data Loading ---
def load_home_server_data():
    global HOME_SERVER_DF, HOME_SERVER_DATA_LOADED
    file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), HOME_SERVER_DATA_PATH))

    if not file_exists(file_path):
        print(f"Warning (HomeServer): File not found at {file_path}")
        HOME_SERVER_DF = pd.DataFrame()
        HOME_SERVER_DATA_LOADED = True # Mark as attempted
        return

    try:
        df = pd.read_json(file_path)
    except Exception as e:
        print(f"Error (HomeServer): Failed to load or parse {file_path}. Error: {e}")
        HOME_SERVER_DF = pd.DataFrame()
        HOME_SERVER_DATA_LOADED = True
        return

    if df.empty:
        print(f"Info (HomeServer): {file_path} was empty.")
        HOME_SERVER_DF = pd.DataFrame()
        HOME_SERVER_DATA_LOADED = True
        return

    # Standardize columns: name, category, description, url, tags, source, added_date
    df.rename(columns={
        'title': 'name', # common alternative
        'link': 'url',
        'desc': 'description',
        'categories': 'category', # Assuming 'category' is singular, 'categories' might be list
        'published_date': 'added_date_str', # Or 'created_at', 'scraped_at'
        'scraped_at': 'added_date_str'
    }, inplace=True)

    expected_cols = ['name', 'category', 'description', 'url', 'tags', 'source', 'added_date_str']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df['added_date'] = df['added_date_str'].apply(parse_hs_date)

    # Process tags (if list or comma-separated string)
    if 'tags' in df.columns:
        df['tags_str'] = df['tags'].apply(lambda x: ', '.join(x) if isinstance(x, list) else (x if isinstance(x, str) else "N/A"))
    else:
        df['tags_str'] = "N/A"

    # Sort by added_date (newest) or name
    df = df.sort_values(by=['added_date', 'name'], ascending=[False, True], na_position='last')

    HOME_SERVER_DF = df
    HOME_SERVER_DATA_LOADED = True
    print(f"Info (HomeServer): Loaded {len(df)} items.")

load_home_server_data()

# --- Layout Rendering & Callbacks ---
def render_home_server_tab():
    if not HOME_SERVER_DATA_LOADED:
        return dbc.Alert("Home Server data loading or failed. Check logs.", color="danger", className="mt-3")
    # Note: df.empty check is good, but options can still be populated if df is empty but columns exist.
    # If df is truly empty (no columns), then category_options will be [].
    # The callback for table update will handle the empty df case for display.

    # Category options will be populated by a callback
    return html.Div([
        html.H3("Home Server Aplicaciones & Tendencias", className="mb-3"),
        dbc.Row([
            dbc.Col(dcc.Dropdown(id="home-server-category-filter", options=[], placeholder="Filtrar por Categoría..."), md=6, className="mb-2"), # Options initially empty
            dbc.Col(dbc.Input(id="home-server-search-input", placeholder="Buscar por Nombre/Descripción..."), md=6, className="mb-2"),
        ], className="mt-3 mb-3"),
        html.Div(id="home-server-accordion-container", className="mt-2"),
        dbc.Pagination(id="home-server-pagination", max_value=1, active_page=1, className="mt-3 justify-content-center")
    ])

def register_home_server_callbacks(app):
    @app.callback(
        Output("home-server-accordion-container", "children"),
        Output("home-server-pagination", "max_value"),
        Output("home-server-pagination", "active_page"),
        Input("home-server-category-filter", "value"),
        Input("home-server-search-input", "value"),
        Input("home-server-pagination", "active_page")
    )
    def update_home_server_display(selected_category, search_term, current_page):
        if not HOME_SERVER_DATA_LOADED or HOME_SERVER_DF.empty:
            return dbc.Alert("Home Server data not available.", color="warning"), 1, 1

        df_filtered = HOME_SERVER_DF.copy()

        if selected_category and selected_category != 'all': # Handle 'all' option
            df_filtered = df_filtered[df_filtered['category'].astype(str) == str(selected_category)]

        if search_term:
            search_lower = search_term.lower()
            df_filtered = df_filtered[
                df_filtered['name'].astype(str).str.lower().contains(search_lower, na=False) |
                df_filtered['description'].astype(str).str.lower().contains(search_lower, na=False) |
                df_filtered['tags_str'].astype(str).str.lower().contains(search_lower, na=False) # Search tags too
            ]

        if df_filtered.empty:
            return dbc.Alert("No items match your filters.", color="info"), 1, 1

        current_page = current_page if current_page else 1
        total_items = len(df_filtered)
        max_pages = (total_items + PAGE_SIZE_HOME_SERVER - 1) // PAGE_SIZE_HOME_SERVER

        start_idx = (current_page - 1) * PAGE_SIZE_HOME_SERVER
        end_idx = start_idx + PAGE_SIZE_HOME_SERVER
        df_paginated = df_filtered.iloc[start_idx:end_idx]

        if df_paginated.empty and total_items > 0 and current_page > 1: # If current page became empty due to filtering, reset to page 1
            current_page = 1
            start_idx = (current_page - 1) * PAGE_SIZE_HOME_SERVER
            end_idx = start_idx + PAGE_SIZE_HOME_SERVER
            df_paginated = df_filtered.iloc[start_idx:end_idx]


        accordion_items = []
        for index, row in df_paginated.iterrows():
            item_title = f"{row.get('name', 'N/A')} ({row.get('category', 'N/A')})"
            item_body = html.Div([
                html.P(row.get('description', 'No description available.')),
                html.P(html.Strong("URL: "), html.A(row.get('url'), href=row.get('url'), target="_blank") if pd.notna(row.get('url')) else "N/A"),
                html.P(html.Strong("Tags: "), html.Span(row.get('tags_str', 'N/A'))),
                html.P(html.Strong("Fuente: "), html.Span(row.get('source', 'N/A'))),
                html.P(html.Strong("Añadido: "), html.Span(row['added_date'].strftime('%Y-%m-%d') if pd.notna(row.get('added_date')) else 'N/A')),
            ])
            accordion_items.append(dbc.AccordionItem(children=item_body, title=item_title, item_id=f"hs-item-{index}"))

        accordion = dbc.Accordion(accordion_items, flush=True, always_open=False, active_item=None) # Start collapsed
        actual_page = min(current_page, max_pages) if max_pages > 0 else 1
        return accordion, max_pages if max_pages > 0 else 1, actual_page

    @app.callback(
        Output("home-server-pagination", "active_page", allow_duplicate=True),
        Input("home-server-category-filter", "value"),
        Input("home-server-search-input", "value"),
        prevent_initial_call=True
    )
    def reset_home_server_pagination(_, __):
        return 1

    @app.callback(
        Output("home-server-category-filter", "options"),
        Input("home-server-category-filter", "id") # Dummy input to trigger on load
    )
    def populate_home_server_category_filter(_):
        if HOME_SERVER_DATA_LOADED and not HOME_SERVER_DF.empty and 'category' in HOME_SERVER_DF.columns:
            try:
                categories = sorted(HOME_SERVER_DF['category'].astype(str).dropna().unique())
                options = [{'label': 'Todas las Categorías', 'value': 'all'}] + \
                          [{'label': c, 'value': c} for c in categories if c and c.lower() != 'nan']
                return options
            except Exception as e:
                print(f"Error creating category options for Home Server: {e}")
                return [{'label': 'Error cargando categorías', 'value': ''}]
        return [{'label': 'No hay categorías disponibles', 'value': ''}]

if __name__ == '__main__':
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_home_server_tab(), fluid=True, className="py-4")
    register_home_server_callbacks(app_test)
    print(f"Home Server Test: Data loaded - {HOME_SERVER_DATA_LOADED}, DataFrame empty - {HOME_SERVER_DF.empty}")
    if HOME_SERVER_DATA_LOADED and not HOME_SERVER_DF.empty:
        print(HOME_SERVER_DF.head(2))
    app_test.run_server(debug=True, port=8065)
