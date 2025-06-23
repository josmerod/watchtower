import os
import json
import pandas as pd
from datetime import datetime, timezone
import dash
from dash import html, dcc, Input, Output, State, Patch
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import re

# --- Constants ---
INNOVATION_DATA_SOURCES = {
    'product_hunt': {"path": "../../../data/product_hunt/producthunt_products_latest.json", "name": "Product Hunt"},
    'github_trends': {"path": "../../../data/github_trends/github_trending_latest.json", "name": "GitHub Trends"},
    'tech_jobs': {"path": "../../../data/tech_jobs/tech_jobs_latest.json", "name": "Tech Jobs"},
}

ALL_INNOVATION_DATA = {} # Stores DataFrames
INNOVATION_DATA_LOADED = {} # Tracks loading status
PAGE_SIZE_INNOVATION = 10

# --- Utility Functions (Date & Numeric Parsing) ---
def parse_innovation_date(date_str, source_key=None):
    if pd.isna(date_str) or not date_str: return None
    try:
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc)
    except ValueError: pass

    common_formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%a, %d %b %Y %H:%M:%S %Z"]
    if source_key == 'product_hunt': # PH uses "%Y-%m-%dT%H:%M:%S.%fZ" for 'created_at' which might be used as launch_date
         common_formats.insert(0, "%Y-%m-%dT%H:%M:%S.%fZ")

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

    print(f"Warning (Innovation-{source_key}): Could not parse date: {date_str}")
    return None

def parse_salary(salary_str):
    if pd.isna(salary_str) or not salary_str : return None
    # Extracts numbers, assumes first is min, second is max if present.
    # Handles ranges like "$50k - $70k", "Up to $100000", "€60000"
    numbers = re.findall(r'\d+[\.,\d]*', str(salary_str).replace('k', '000'))
    if not numbers: return None
    try:
        return float(numbers[0].replace('.', '').replace(',', '.'))
    except ValueError: return None


# --- Data Loading ---
def load_single_innovation_source(source_key, file_info):
    global ALL_INNOVATION_DATA, INNOVATION_DATA_LOADED
    file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), file_info["path"]))

    if not os.path.exists(file_path):
        print(f"Warning ({file_info['name']}): File not found at {file_path}")
        ALL_INNOVATION_DATA[source_key] = pd.DataFrame()
        INNOVATION_DATA_LOADED[source_key] = True # Attempted
        return

    try:
        df = pd.read_json(file_path)
    except Exception as e:
        print(f"Error ({file_info['name']}): Failed to load or parse {file_path}. Error: {e}")
        ALL_INNOVATION_DATA[source_key] = pd.DataFrame()
        INNOVATION_DATA_LOADED[source_key] = True
        return

    if df.empty:
        print(f"Info ({file_info['name']}): {file_path} was empty.")
        ALL_INNOVATION_DATA[source_key] = pd.DataFrame()
        INNOVATION_DATA_LOADED[source_key] = True
        return

    df['source_name_display'] = file_info['name'] # For display if needed

    if source_key == 'product_hunt':
        df.rename(columns={'name': 'title', 'votes_count': 'votes',
                           'created_at': 'date_str', # This is product submission date
                           'discussion_url': 'url', 'tagline':'description'}, inplace=True)
        # 'category' might be nested or need extraction, e.g. topics
        if 'topics' in df.columns and df['topics'].apply(lambda x: isinstance(x, list) and len(x) > 0 and 'name' in x[0]).any():
             df['category'] = df['topics'].apply(lambda x: x[0]['name'] if (isinstance(x, list) and len(x)>0 and 'name' in x[0]) else "N/A")
        else:
            df['category'] = "N/A"
        df['launch_date_str'] = df['date_str'] # Use created_at as launch_date for PH

    elif source_key == 'github_trends':
        df.rename(columns={'repo_name': 'title', 'repo_url': 'url',
                           'stars_today': 'score', # Or 'stars_total'
                           'description': 'description', 'language': 'language',
                           'forks_total': 'forks', 'stars_total':'stars',
                           'scrape_date': 'date_str'}, inplace=True)
        df['votes'] = df['stars'] # For a generic 'votes' like column if needed for sorting later

    elif source_key == 'tech_jobs':
        df.rename(columns={'job_title': 'title', 'job_url': 'url',
                           'company_name': 'company', 'job_location': 'location',
                           'salary_range_min': 'salary_min_str',
                           'salary_range_max': 'salary_max_str',
                           'job_category': 'role_category', # Or 'category'
                           'posted_date': 'date_str'}, inplace=True) # Or 'scrape_date'
        df['salary_min_numeric'] = df['salary_min_str'].apply(parse_salary)
        df['salary_max_numeric'] = df['salary_max_str'].apply(parse_salary)

    # Generic date parsing
    if 'date_str' in df.columns:
        df['date'] = df['date_str'].apply(lambda x: parse_innovation_date(x, source_key=source_key))
        df = df.sort_values(by='date', ascending=False, na_position='last')

    # Generic numeric parsing for votes/stars if not handled already
    for col in ['votes', 'stars', 'forks']:
        if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    ALL_INNOVATION_DATA[source_key] = df
    INNOVATION_DATA_LOADED[source_key] = True
    print(f"Info ({file_info['name']}): Loaded {len(df)} items.")

def load_all_innovation_data():
    for key, file_info in INNOVATION_DATA_SOURCES.items():
        load_single_innovation_source(key, file_info)
    print("Attempted to load all innovation data.")

load_all_innovation_data()

# --- Layout Rendering & Callbacks (Placeholders and structure) ---
# Helper to create table (can be more generic or specific per tab)
def create_innovation_table(df_subset, source_key):
    if df_subset.empty:
        return dbc.Alert(f"No items match your criteria for {INNOVATION_DATA_SOURCES[source_key]['name']}.", color="info")

    cols_map = {
        'product_hunt': ["title", "tagline", "votes", "category", "date"],
        'github_trends': ["title", "description", "stars", "forks", "language", "date"],
        'tech_jobs': ["title", "company", "location", "salary_min_numeric", "salary_max_numeric", "role_category", "date"]
    }
    header_map = {
        'product_hunt': {"title": "Name", "tagline":"Tagline", "votes":"Votes", "category":"Category", "date":"Launch Date"},
        'github_trends': {"title": "Repository", "description":"Description", "stars":"Stars", "forks":"Forks", "language":"Language", "date":"Scraped Date"},
        'tech_jobs': {"title": "Job Title", "company":"Company", "location":"Location", "salary_min_numeric":"Salary Min", "salary_max_numeric":"Salary Max", "role_category":"Role", "date":"Posted/Scraped"}
    }

    columns = cols_map.get(source_key, df_subset.columns.tolist()[:5]) # Default to first 5 if not mapped
    headers = [html.Th(header_map.get(source_key, {}).get(col, col.replace('_',' ').title())) for col in columns]
    table_header = [html.Thead(html.Tr(headers))]

    table_body_rows = []
    for _, row in df_subset.iterrows():
        cells = []
        for col in columns:
            val = row.get(col)
            if col == 'title':
                cell_content = html.A(val if pd.notna(val) else 'N/A', href=row.get('url'), target="_blank")
            elif col == 'date':
                cell_content = val.strftime('%Y-%m-%d') if pd.notna(val) else 'N/A'
            elif 'salary' in col and pd.notna(val):
                cell_content = f"€{val:,.0f}" # Basic salary formatting
            elif col in ['votes', 'stars', 'forks'] and pd.notna(val):
                cell_content = f"{int(val):,}"
            else:
                cell_content = str(val) if pd.notna(val) else 'N/A'
            cells.append(html.Td(cell_content))
        table_body_rows.append(html.Tr(cells))
    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(table_header + table_body, striped=True, bordered=True, hover=True, responsive=True, size="sm")

def render_single_innovation_sub_tab(source_key, source_df):
    source_name = INNOVATION_DATA_SOURCES.get(source_key, {}).get('name', "Source")
    if not INNOVATION_DATA_LOADED.get(source_key, False):
        return dbc.Alert(f"Data for {source_name} failed to load.", color="danger", className="mt-3")
    if source_df.empty:
        return dbc.Alert(f"No data currently available for {source_name}.", color="info", className="mt-3")

    # Define specific filters based on source_key
    filter_dropdown = None
    if source_key == 'product_hunt' and 'category' in source_df.columns:
        options = [{'label': i, 'value': i} for i in sorted(source_df['category'].dropna().unique()) if i]
        filter_dropdown = dcc.Dropdown(id=f"innovation-{source_key}-filter-dropdown", options=options, placeholder=f"Filter by Category...")
    elif source_key == 'github_trends' and 'language' in source_df.columns:
        options = [{'label': i, 'value': i} for i in sorted(source_df['language'].dropna().unique()) if i]
        filter_dropdown = dcc.Dropdown(id=f"innovation-{source_key}-filter-dropdown", options=options, placeholder=f"Filter by Language...")
    elif source_key == 'tech_jobs' and 'role_category' in source_df.columns: # Assuming 'role_category'
        options = [{'label': i, 'value': i} for i in sorted(source_df['role_category'].dropna().unique()) if i]
        filter_dropdown = dcc.Dropdown(id=f"innovation-{source_key}-filter-dropdown", options=options, placeholder=f"Filter by Role...")

    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Input(id=f"innovation-{source_key}-search-input", placeholder=f"Search in {source_name}..."), md=8 if filter_dropdown else 12, className="mb-2"),
            dbc.Col(filter_dropdown, md=4, className="mb-2") if filter_dropdown else None
        ], className="mt-3 mb-3"),
        html.Div(id=f"innovation-{source_key}-table-container"),
        dbc.Pagination(id=f"innovation-{source_key}-pagination", max_value=1, active_page=1, className="mt-3 justify-content-center")
    ])

def render_innovation_tab():
    if not any(INNOVATION_DATA_LOADED.values()):
        return dbc.Alert("All Innovation data failed to load.", color="danger", className="mt-3")

    tabs_children = []
    active_tab_id = None
    for key, source_info in INNOVATION_DATA_SOURCES.items():
        tab_id = f"tab-innovation-{key}"
        if active_tab_id is None: active_tab_id = tab_id
        tabs_children.append(
            dbc.Tab(label=source_info['name'], tab_id=tab_id,
                    children=render_single_innovation_sub_tab(key, ALL_INNOVATION_DATA.get(key, pd.DataFrame())))
        )

    return html.Div([
        html.H3("Innovación", className="mb-3"),
        dbc.Tabs(id="innovation-main-tabs", active_tab=active_tab_id, children=tabs_children)
    ])

# --- Callbacks ---
def register_innovation_callbacks(app):
    for source_key in INNOVATION_DATA_SOURCES.keys():
        @app.callback(
            Output(f"innovation-{source_key}-table-container", "children"),
            Output(f"innovation-{source_key}-pagination", "max_value"),
            Output(f"innovation-{source_key}-pagination", "active_page"),
            Input(f"innovation-{source_key}-search-input", "value"),
            Input(f"innovation-{source_key}-filter-dropdown", "value"), # Will be None if dropdown doesn't exist for a source
            Input(f"innovation-{source_key}-pagination", "active_page"),
            prevent_initial_call=True
        )
        def update_innovation_table(search_term, filter_value, current_page, sk=source_key):
            # Check if the specific filter dropdown exists for this source_key to avoid errors if it's not in the layout
            # This is more of a conceptual check as Dash requires all Input/State to be present in the layout.
            # The layout function render_single_innovation_sub_tab conditionally creates this dropdown.
            # A better approach for truly optional inputs in dynamic callbacks might involve pattern-matching IDs or clientside callbacks.
            # For now, we assume if the ID is listed as an Input, it must exist in the layout served to the client.
            # The filter_value will be None if the dropdown is not present OR if it's present but has no value selected.

            if not INNOVATION_DATA_LOADED.get(sk, False) or ALL_INNOVATION_DATA.get(sk, pd.DataFrame()).empty:
                return dbc.Alert(f"Data for {INNOVATION_DATA_SOURCES[sk]['name']} not available.", color="warning"), 1, 1

            df_source = ALL_INNOVATION_DATA[sk].copy()
            df_filtered = df_source

            # Search
            if search_term:
                search_lower = search_term.lower()
                title_col = 'title' # Standardized
                desc_cols = ['description', 'tagline'] # Possible description columns

                search_condition = df_filtered[title_col].astype(str).str.lower().contains(search_lower, na=False)
                for desc_col in desc_cols:
                    if desc_col in df_filtered.columns:
                        search_condition |= df_filtered[desc_col].astype(str).str.lower().contains(search_lower, na=False)
                df_filtered = df_filtered[search_condition]

            # Filter (specific to source)
            filter_column = None
            if sk == 'product_hunt': filter_column = 'category'
            elif sk == 'github_trends': filter_column = 'language'
            elif sk == 'tech_jobs': filter_column = 'role_category'

            if filter_value and filter_column and filter_column in df_filtered.columns:
                 df_filtered = df_filtered[df_filtered[filter_column] == filter_value]

            if df_filtered.empty:
                return dbc.Alert(f"No items match your criteria in {INNOVATION_DATA_SOURCES[sk]['name']}.", color="info"), 1, 1

            current_page = current_page if current_page else 1
            total_items = len(df_filtered)
            max_pages = (total_items + PAGE_SIZE_INNOVATION - 1) // PAGE_SIZE_INNOVATION

            start_idx = (current_page - 1) * PAGE_SIZE_INNOVATION
            end_idx = start_idx + PAGE_SIZE_INNOVATION
            df_paginated = df_filtered.iloc[start_idx:end_idx]

            table = create_innovation_table(df_paginated, sk)
            actual_page = min(current_page, max_pages) if max_pages > 0 else 1
            return table, max_pages if max_pages > 0 else 1, actual_page

        @app.callback(
            Output(f"innovation-{source_key}-pagination", "active_page", allow_duplicate=True),
            Input(f"innovation-{source_key}-search-input", "value"),
            Input(f"innovation-{source_key}-filter-dropdown", "value"), # This Input must exist in the layout for all source_keys
            prevent_initial_call=True
        )
        def reset_innovation_pagination(_, __, sk=source_key): # filter_value is now a required arg
            return 1

        # Callback to populate filter dropdown options
        # This callback will only effectively run if the dropdown with this ID exists in the current layout.
        # If a source_key does not have a filter dropdown defined in render_single_innovation_sub_tab,
        # this callback output will target a non-existent component for that source_key, which Dash handles gracefully (no update).
        @app.callback(
            Output(f"innovation-{source_key}-filter-dropdown", "options"),
            Input(f"innovation-{source_key}-filter-dropdown", "id"), # Trigger on load (if it exists)
            # prevent_initial_call=False # Allow to run on load for existing dropdowns
        )
        def populate_innovation_filters(_, sk_filter=source_key):
            # Check if this source is supposed to have this filter
            filter_column = None
            if sk_filter == 'product_hunt': filter_column = 'category'
            elif sk_filter == 'github_trends': filter_column = 'language'
            elif sk_filter == 'tech_jobs': filter_column = 'role_category'
            else: # This source_key does not have a specific filter dropdown defined in its layout
                raise PreventUpdate # Or return dash.no_update or []

            if INNOVATION_DATA_LOADED.get(sk_filter, False) and not ALL_INNOVATION_DATA.get(sk_filter, pd.DataFrame()).empty:
                df_source = ALL_INNOVATION_DATA[sk_filter]
                if filter_column and filter_column in df_source.columns:
                    unique_values = sorted(df_source[filter_column].dropna().unique())
                    return [{'label': i, 'value': i} for i in unique_values if i]
            return []


if __name__ == '__main__':
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_innovation_tab(), fluid=True, className="py-4")
    register_innovation_callbacks(app_test)

    for key, loaded in INNOVATION_DATA_LOADED.items():
        df_len = len(ALL_INNOVATION_DATA.get(key, []))
        print(f"Innovation Test ({INNOVATION_DATA_SOURCES[key]['name']}): Loaded - {loaded}, Count - {df_len}")
    app_test.run_server(debug=True, port=8063)
