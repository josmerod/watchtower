import os
import json
import pandas as pd
from datetime import datetime, timezone
import dash
from dash import html, dcc, Input, Output, State, Patch, callback_context
import dash_bootstrap_components as dbc
# Import shared utilities
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_data_path, file_exists, dir_exists

from dash.exceptions import PreventUpdate

# --- Constants ---
DEV_DATA_SOURCES = {
    'devto': {"path": get_data_path("dev_community", "dev_community_latest.json"), "name": "DEV.to"},
    'hackernews_ask': {"path": get_data_path("hackernews_ask", "hackernews_ask_latest.json"), "name": "Hacker News Ask"},
    'hackernews_show': {"path": get_data_path("hackernews_show", "hackernews_show_latest.json"), "name": "Hacker News Show"},
    'indiehackers': {"path": get_data_path("indiehackers", "indiehackers_latest.json"), "name": "Indie Hackers"},
    'lobsters': {"path": get_data_path("lobsters", "lobsters_latest.json"), "name": "Lobsters"},
    'producthunt': {"path": get_data_path("producthunt", "producthunt_latest.json"), "name": "Product Hunt"},
    'stackoverflow': {"path": get_data_path("stackoverflow_trends", "stackoverflow_trends_latest.json"), "name": "Stack Overflow"},
    # Add more sources here as they are created by ETLs
    # e.g. 'reddit_programming': {"path": get_data_path("reddit_programming", "..."), "name": "r/programming"},
}

ALL_DEV_COMMUNITY_DATA = {} # Stores DataFrames
DEV_DATA_LOADED = {}      # Tracks loading status for each source
PAGE_SIZE_DEV = 10

# --- Date Parsing Utility ---
def parse_dev_date(date_str, source_key=None): # source_key can be used for specific format hints
    if pd.isna(date_str) or not date_str: return None
    try: # ISO format
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc)
    except ValueError: pass

    common_formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%a, %d %b %Y %H:%M:%S %Z"] # Added RSS format
    if source_key == 'producthunt': # Product Hunt often uses "%Y-%m-%dT%H:%M:%S.%fZ"
        common_formats.insert(0, "%Y-%m-%dT%H:%M:%S.%fZ")

    for fmt in common_formats:
        try:
            dt = datetime.strptime(str(date_str), fmt)
            # If naive, assume UTC. If aware, convert to UTC.
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError: continue

    try: # Epoch timestamp
        ts = float(date_str)
        if ts > 10000000000: ts /= 1000 # ms to s
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except ValueError: pass

    print(f"Warning (DevComm-{source_key}): Could not parse date: {date_str}")
    return None

# --- Data Loading ---
def load_single_dev_source(source_key, file_info):
    global ALL_DEV_COMMUNITY_DATA, DEV_DATA_LOADED
    file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), file_info["path"]))

    if not file_exists(file_path):
        print(f"Warning ({file_info['name']}): File not found at {file_path}")
        ALL_DEV_COMMUNITY_DATA[source_key] = pd.DataFrame()
        DEV_DATA_LOADED[source_key] = True # Attempted
        return

    try:
        df = pd.read_json(file_path)
    except Exception as e:
        print(f"Error ({file_info['name']}): Failed to load or parse {file_path}. Error: {e}")
        ALL_DEV_COMMUNITY_DATA[source_key] = pd.DataFrame()
        DEV_DATA_LOADED[source_key] = True
        return

    if df.empty:
        print(f"Info ({file_info['name']}): {file_path} was empty.")
        ALL_DEV_COMMUNITY_DATA[source_key] = pd.DataFrame()
        DEV_DATA_LOADED[source_key] = True
        return

    # Standardize columns - this will need adjustment per source
    # title, url, score, date, source_name, display_content
    df['source_name'] = file_info['name']

    # DEV.to specific (example)
    if source_key == 'devto':
        df.rename(columns={'article_title': 'title', 'article_url': 'url',
                           'article_reactions': 'score', 'article_published_at': 'date_str',
                           'article_description': 'display_content'}, inplace=True)
    # Stack Overflow specific (example)
    elif source_key == 'stackoverflow':
        df.rename(columns={'title': 'title', 'link': 'url',
                           'score': 'score', 'last_activity_date': 'date_str', # or creation_date
                           'body_markdown': 'display_content'}, inplace=True) # May need stripping
    # Hacker News (Ask/Show)
    elif source_key in ['hackernews_ask', 'hackernews_show']:
         df.rename(columns={'item_title': 'title', 'item_url': 'url',
                           'item_score': 'score', 'item_time': 'date_str', # item_time is epoch
                           'item_text': 'display_content'}, inplace=True)
    # Indie Hackers
    elif source_key == 'indiehackers':
        df.rename(columns={'post_title': 'title', 'post_url': 'url',
                           'post_upvotes': 'score', 'post_date': 'date_str',
                           'post_content': 'display_content'}, inplace=True)
    # Lobsters
    elif source_key == 'lobsters':
        df.rename(columns={'comment_created_at': 'date_str', # Assuming we use comment time as primary sort for lobsters
                           'title': 'title', 'short_id_url': 'url', 'score':'score',
                           'comment': 'display_content'}, inplace=True) # or 'description' if available at top level
        if 'date_str' not in df.columns and 'created_at' in df.columns: # Fallback for main post date
            df['date_str'] = df['created_at']

    # Product Hunt
    elif source_key == 'producthunt':
         df.rename(columns={'name': 'title', 'discussion_url': 'url', # or product 'url'
                           'votes_count': 'score', 'created_at': 'date_str', # This is product creation
                           'tagline': 'display_content'}, inplace=True)
    else: # Generic fallback (might need per-source handling)
        df.rename(columns={'name': 'title', 'link': 'url', 'published_at': 'date_str', 'description': 'display_content'}, inplace=True)


    # Ensure core columns exist
    core_cols = ['title', 'url', 'score', 'date_str', 'display_content']
    for col in core_cols:
        if col not in df.columns:
            df[col] = None if col != 'score' else 0 # Default score to 0

    df['date'] = df['date_str'].apply(lambda x: parse_dev_date(x, source_key=source_key))
    df['score'] = pd.to_numeric(df['score'], errors='coerce').fillna(0)

    # Sort by date
    df = df.sort_values(by='date', ascending=False, na_position='last')

    ALL_DEV_COMMUNITY_DATA[source_key] = df
    DEV_DATA_LOADED[source_key] = True
    print(f"Info ({file_info['name']}): Loaded {len(df)} items.")

def load_all_dev_community_data():
    for key, file_info in DEV_DATA_SOURCES.items():
        load_single_dev_source(key, file_info)
    print("Attempted to load all dev community data.")

load_all_dev_community_data()

# --- Layout Rendering ---
def create_dev_community_table(df_subset, source_key):
    if df_subset.empty:
        return dbc.Alert(f"No items match your criteria for {DEV_DATA_SOURCES.get(source_key,{}).get('name', source_key)}.", color="info")

    table_header = [html.Thead(html.Tr([
        html.Th("Title"), html.Th("Score", style={'width': '100px'}), html.Th("Date", style={'width': '150px'})
        # Consider adding a snippet column later if 'display_content' is clean enough
    ]))]

    table_body_rows = []
    for _, row in df_subset.iterrows():
        title_cell = html.A(row.get('title', 'N/A'), href=row.get('url'), target="_blank", rel="noopener noreferrer")
        # Optionally, add tooltip for display_content if it's too long for a cell
        # if pd.notna(row.get('display_content')):
        #     title_cell = html.Span(title_cell, title=str(row['display_content'])[:200]) # Basic tooltip

        table_body_rows.append(html.Tr([
            html.Td(title_cell),
            html.Td(f"{int(row.get('score',0))}" if pd.notna(row.get('score')) else "N/A"),
            html.Td(row['date'].strftime('%Y-%m-%d %H:%M') if pd.notna(row.get('date')) else 'N/A')
        ]))
    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(table_header + table_body, striped=True, bordered=True, hover=True, responsive=True, size="sm")

def render_single_community_sub_tab(source_key, source_df):
    source_name = DEV_DATA_SOURCES.get(source_key, {}).get('name', "Community")

    if not DEV_DATA_LOADED.get(source_key, False):
        return dbc.Alert(f"Data for {source_name} failed to load. Check logs.", color="danger", className="mt-3")
    if source_df.empty:
        return dbc.Alert(f"No data currently available for {source_name}.", color="info", className="mt-3")

    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Input(id=f"dev-{source_key}-search-input", placeholder=f"Search in {source_name}..."), md=9, className="mb-2"),
            dbc.Col(html.Div(f"Total: {len(source_df)} items", className="text-muted small align-self-center"), md=3)
        ], className="mt-3 mb-3"),
        html.Div(id=f"dev-{source_key}-table-container"),
        dbc.Pagination(id=f"dev-{source_key}-pagination", max_value=1, active_page=1, className="mt-3 justify-content-center")
    ], className="mt-2")

def render_dev_communities_tab():
    if not any(DEV_DATA_LOADED.values()):
        return dbc.Alert("All Dev Community data failed to load.", color="danger", className="mt-3")

    tabs_children = []
    active_tab_id = None
    for key, source_info in DEV_DATA_SOURCES.items():
        tab_id = f"tab-dev-{key}"
        if active_tab_id is None: active_tab_id = tab_id # Default to first tab

        tabs_children.append(
            dbc.Tab(label=source_info['name'], tab_id=tab_id,
                    children=render_single_community_sub_tab(key, ALL_DEV_COMMUNITY_DATA.get(key, pd.DataFrame())))
        )

    return html.Div([
        html.H3("Comunidades Dev", className="mb-3"),
        dbc.Tabs(id="devcomm-main-tabs", active_tab=active_tab_id, children=tabs_children)
    ])

# --- Callbacks ---
def register_dev_communities_callbacks(app):
    for source_key in DEV_DATA_SOURCES.keys():
        @app.callback(
            Output(f"dev-{source_key}-table-container", "children"),
            Output(f"dev-{source_key}-pagination", "max_value"),
            Output(f"dev-{source_key}-pagination", "active_page"),
            Input(f"dev-{source_key}-search-input", "value"),
            Input(f"dev-{source_key}-pagination", "active_page"),
            State("devcomm-main-tabs", "active_tab"), # To only update visible tab (optimization)
            prevent_initial_call=True
        )
        def update_dev_community_table(search_term, current_page, active_main_tab_id, sk=source_key): # sk=source_key to capture loop variable
            # Optimization: Only update if this source's tab is active or about to be active
            # However, Dash might still compute callbacks for non-visible tabs if inputs change.
            # A more robust way if needed is dcc.Store for active tab and use that as input,
            # or accept that callbacks run but don't update layout if not visible.
            # For now, simple check:
            # triggered_input = callback_context.triggered[0]['prop_id'].split('.')[0]
            # if active_main_tab_id != f"tab-dev-{sk}" and not triggered_input.startswith(f"dev-{sk}"):
            #     raise PreventUpdate

            if not DEV_DATA_LOADED.get(sk, False) or ALL_DEV_COMMUNITY_DATA.get(sk, pd.DataFrame()).empty:
                return dbc.Alert(f"Data for {DEV_DATA_SOURCES[sk]['name']} not available.", color="warning"), 1, 1

            df_source = ALL_DEV_COMMUNITY_DATA[sk].copy()
            df_filtered = df_source

            if search_term:
                search_lower = search_term.lower()
                # Search in title and display_content (if it exists and is text)
                df_filtered = df_filtered[
                    df_filtered['title'].astype(str).str.lower().contains(search_lower, na=False) |
                    (df_filtered['display_content'].astype(str).str.lower().contains(search_lower, na=False) if 'display_content' in df_filtered.columns else False)
                ]

            if df_filtered.empty:
                return dbc.Alert(f"No items match your search in {DEV_DATA_SOURCES[sk]['name']}.", color="info"), 1, 1

            current_page = current_page if current_page else 1
            total_items = len(df_filtered)
            max_pages = (total_items + PAGE_SIZE_DEV - 1) // PAGE_SIZE_DEV

            start_idx = (current_page - 1) * PAGE_SIZE_DEV
            end_idx = start_idx + PAGE_SIZE_DEV
            df_paginated = df_filtered.iloc[start_idx:end_idx]

            table = create_dev_community_table(df_paginated, sk)
            actual_page = min(current_page, max_pages) if max_pages > 0 else 1
            return table, max_pages if max_pages > 0 else 1, actual_page

        @app.callback(
            Output(f"dev-{source_key}-pagination", "active_page", allow_duplicate=True),
            Input(f"dev-{source_key}-search-input", "value"),
            prevent_initial_call=True
        )
        def reset_dev_community_pagination(_, sk=source_key): # sk to capture loop variable
            return 1

if __name__ == '__main__':
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_dev_communities_tab(), fluid=True, className="py-4")
    register_dev_communities_callbacks(app_test)

    for key, loaded in DEV_DATA_LOADED.items():
        df_len = len(ALL_DEV_COMMUNITY_DATA.get(key, []))
        print(f"DevComm Test ({DEV_DATA_SOURCES[key]['name']}): Loaded - {loaded}, Count - {df_len}")
        if not loaded and df_len == 0:
             print(f"  Check path: {DEV_DATA_SOURCES[key]['path']}")

    app_test.run_server(debug=True, port=8061)
