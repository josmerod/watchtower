import os
import json
import pandas as pd
from datetime import datetime, timezone, timedelta
import dash
from dash import html, dcc, Input, Output, State, Patch
import dash_bootstrap_components as dbc
# Import shared utilities
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_data_path, file_exists, dir_exists

from dash.exceptions import PreventUpdate
import re # For parsing cost

# --- Constants ---
TECH_EVENTS_DATA_PATH = get_data_path("tech_conference", "output/tech_events_latest.json")
TECH_EVENTS_DF = pd.DataFrame()
EVENTS_DATA_LOADED = False
PAGE_SIZE_EVENTS = 10 # For pagination

# --- Utility Functions (Date & Cost Parsing) ---
def parse_event_date(date_str):
    if pd.isna(date_str) or not date_str:
        return None
    try: # ISO format is common
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc)
    except ValueError: # Add more formats if needed based on data
        try:
            dt = datetime.strptime(str(date_str), "%Y-%m-%d")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"Warning (Events): Could not parse date: {date_str}")
            return None

def parse_event_cost(cost_str):
    if pd.isna(cost_str) or cost_str is None: return None
    s_cost = str(cost_str).strip().lower()
    if 'free' in s_cost or 'gratis' in s_cost: return 0.0

    # Attempt to extract numbers, handles formats like "$100 - $200" by taking the first number
    numbers = re.findall(r'\d+[\.,\d]*', s_cost)
    if numbers:
        try:
            # Take the first number found, clean it (remove thousands separators, use . as decimal)
            num_str = numbers[0].replace('.', '').replace(',', '.') if ',' in numbers[0] and '.' in numbers[0] else numbers[0].replace(',', '.')
            return float(num_str)
        except ValueError:
            pass
    return None # Or some indicator of "Varies" / "Check site" if preferred

# --- Data Loading ---
def load_tech_events_data():
    global TECH_EVENTS_DF, EVENTS_DATA_LOADED
    file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), TECH_EVENTS_DATA_PATH))

    if not file_exists(file_path):
        print(f"Warning (Events): File not found at {file_path}")
        TECH_EVENTS_DF = pd.DataFrame()
        EVENTS_DATA_LOADED = True # Mark as attempted
        return

    try:
        df = pd.read_json(file_path)
    except Exception as e:
        print(f"Error (Events): Failed to load or parse {file_path}. Error: {e}")
        TECH_EVENTS_DF = pd.DataFrame()
        EVENTS_DATA_LOADED = True
        return

    if df.empty:
        print(f"Info (Events): {file_path} was empty.")
        TECH_EVENTS_DF = pd.DataFrame()
        EVENTS_DATA_LOADED = True
        return

    # Standardize columns (adjust based on actual JSON keys)
    df.rename(columns={
        'name': 'title', # Common alternative
        'event_name': 'title',
        'date_text': 'date_display_text', # If there's a pre-formatted date string
        'event_date': 'start_date_str', # Assuming this is the start date
        'event_type': 'type',
        'event_cost': 'cost_str',
        'event_score': 'quality_score',
        'event_format': 'format', # e.g., virtual, in-person
        'event_url': 'url',
        'event_location': 'location'
    }, inplace=True)

    expected_cols = ['title', 'url', 'start_date_str', 'location', 'type', 'cost_str', 'quality_score', 'format', 'description']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df['start_date'] = df['start_date_str'].apply(parse_event_date)
    df['cost_numeric'] = df['cost_str'].apply(parse_event_cost)
    df['quality_score_numeric'] = pd.to_numeric(df['quality_score'], errors='coerce')

    # Sort by start_date by default
    df = df.sort_values(by='start_date', ascending=True, na_position='last') # Upcoming first

    TECH_EVENTS_DF = df
    EVENTS_DATA_LOADED = True
    print(f"Info (Events): Loaded {len(df)} tech events.")

load_tech_events_data()

# --- Layout Rendering Functions (Placeholders and Initial Structure) ---
def create_events_table(df_subset, table_id, columns_to_display=None):
    if df_subset.empty:
        return dbc.Alert("No events match the current criteria.", color="info")

    # Default columns if not specified
    if columns_to_display is None:
        columns_to_display = ['title', 'start_date', 'location', 'type', 'cost_numeric']
        # Could add more like 'format', 'quality_score_numeric' for the search tab

    header_map = {
        'title': "Name", 'start_date': "Date", 'location': "Location", 'type': "Type",
        'cost_numeric': "Cost (€)", 'format': "Format", 'quality_score_numeric': "Score"
    }

    table_header = [html.Thead(html.Tr([html.Th(header_map.get(col, col.replace('_', ' ').title())) for col in columns_to_display]))]

    table_body_rows = []
    for _, row in df_subset.iterrows():
        cells = []
        for col in columns_to_display:
            val = row.get(col)
            if col == 'title':
                cell_content = html.A(val if pd.notna(val) else 'N/A', href=row.get('url'), target="_blank")
            elif col == 'start_date':
                cell_content = val.strftime('%Y-%m-%d') if pd.notna(val) else 'N/A'
            elif col == 'cost_numeric':
                cell_content = f"€{val:.2f}" if pd.notna(val) and val > 0 else ("Free" if pd.notna(val) and val == 0 else "N/A")
            elif col == 'quality_score_numeric':
                 cell_content = f"{val:.0f}/100" if pd.notna(val) else 'N/A'
            else:
                cell_content = str(val) if pd.notna(val) else 'N/A'
            cells.append(html.Td(cell_content))
        table_body_rows.append(html.Tr(cells))

    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(table_header + table_body, id=table_id, striped=True, bordered=True, hover=True, responsive=True, size="sm")

def render_upcoming_events_sub_tab(df):
    # Initial static render, callback will update this
    return html.Div([
        dbc.Row([
            dbc.Col(dcc.Dropdown(id="upcoming-event-type-filter", placeholder="Filter by Type..."), md=4, className="mb-2"),
            dbc.Col(dbc.Checkbox(id="upcoming-event-free-checkbox", label="Only Free Events"), md=3, className="mb-2 align-self-center"),
        ], className="mt-3 mb-3"),
        html.Div(id="upcoming-events-table-container", children=dbc.Alert("Loading upcoming events...", color="info")),
        dbc.Pagination(id="upcoming-events-pagination", max_value=1, active_page=1, className="mt-3 justify-content-center")
    ])

def render_search_events_sub_tab(df):
    # Initial static render, callback will update this
    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Input(id="search-events-query", placeholder="Search by name, description..."), md=12, className="mb-3")
        ]),
        dbc.Row([
            dbc.Col(dcc.Dropdown(id="search-event-type-filter", placeholder="Filter by Type..."), md=3, className="mb-2"),
            dbc.Col(dcc.Dropdown(id="search-event-format-filter", placeholder="Filter by Format..."), md=3, className="mb-2"),
            # dbc.Col(dcc.RangeSlider(id="search-event-score-slider", min=0, max=100, step=5, value=[0,100], marks={i: str(i) for i in range(0, 101, 20)}), md=4, className="mb-2"), # If score slider needed
            dbc.Col(dcc.Dropdown(id="search-events-sort", placeholder="Sort by...",
                                 options=[
                                     {'label': 'Sort by Date (Upcoming First)', 'value': 'date_asc'},
                                     {'label': 'Sort by Date (Newest Added/Later Date)', 'value': 'date_desc'}, # Assuming 'start_date' can mean this
                                     {'label': 'Sort by Quality Score', 'value': 'score_desc'},
                                 ], value='date_asc'), md=3, className="mb-2")
        ], className="mb-3"),
        html.Div(id="search-events-table-container", children=dbc.Alert("Enter search criteria to find events.", color="info")),
        dbc.Pagination(id="search-events-pagination", max_value=1, active_page=1, className="mt-3 justify-content-center")
    ])

# --- Main Layout ---
def render_tech_events_tab():
    if not EVENTS_DATA_LOADED or TECH_EVENTS_DF.empty:
        return html.Div([
            html.H3("Eventos Tech", className="mb-3"),
            dbc.Alert("Tech Events data could not be loaded or is empty. Please check data sources and ETLs.", color="danger")
        ])

    total_events = len(TECH_EVENTS_DF)
    upcoming_df = TECH_EVENTS_DF[TECH_EVENTS_DF['start_date'] >= datetime.now(timezone.utc)] if 'start_date' in TECH_EVENTS_DF.columns else pd.DataFrame()
    upcoming_count = len(upcoming_df)
    avg_score = TECH_EVENTS_DF['quality_score_numeric'].mean() if 'quality_score_numeric' in TECH_EVENTS_DF and TECH_EVENTS_DF['quality_score_numeric'].notna().any() else 0

    summary_stats = dbc.Row([
        dbc.Col(dbc.Card([dbc.CardHeader("Total Eventos Listados"), dbc.CardBody(f"{total_events:,}")], color="primary", inverse=True), md=4, className="mb-2"),
        dbc.Col(dbc.Card([dbc.CardHeader("Próximos Eventos"), dbc.CardBody(f"{upcoming_count:,}")], color="info", inverse=True), md=4, className="mb-2"),
        dbc.Col(dbc.Card([dbc.CardHeader("Puntuación Media Calidad"), dbc.CardBody(f"{avg_score:.0f}/100" if avg_score > 0 else "N/A")], color="success", inverse=True), md=4, className="mb-2"),
    ], className="mb-4")

    main_tabs = dbc.Tabs(id="events-main-tabs", active_tab="tab-upcoming-events", children=[
        dbc.Tab(label="Próximos Eventos", tab_id="tab-upcoming-events", children=render_upcoming_events_sub_tab(TECH_EVENTS_DF)),
        dbc.Tab(label="Buscar Eventos", tab_id="tab-search-events", children=render_search_events_sub_tab(TECH_EVENTS_DF)),
    ])

    return html.Div([
        html.H3("Eventos Tech", className="mb-3"),
        summary_stats,
        main_tabs
    ])

# --- Callbacks ---
def register_tech_events_callbacks(app):
    @app.callback(
        Output("upcoming-events-table-container", "children"),
        Output("upcoming-events-pagination", "max_value"),
        Output("upcoming-events-pagination", "active_page"),
        Input("upcoming-event-type-filter", "value"),
        Input("upcoming-event-free-checkbox", "value"), # List of values if checked
        Input("upcoming-events-pagination", "active_page")
    )
    def update_upcoming_events(selected_type, free_only_checked, current_page):
        if not EVENTS_DATA_LOADED or TECH_EVENTS_DF.empty:
            return dbc.Alert("Tech Events data not available.", color="warning"), 1, 1

        df_filtered = TECH_EVENTS_DF[TECH_EVENTS_DF['start_date'] >= datetime.now(timezone.utc)].copy()

        if selected_type:
            df_filtered = df_filtered[df_filtered['type'] == selected_type]

        if free_only_checked: # Checkbox value is a list, e.g. [True] if checked
            df_filtered = df_filtered[df_filtered['cost_numeric'] == 0]

        if df_filtered.empty:
            return dbc.Alert("No upcoming events match your filters.", color="info"), 1, 1

        current_page = current_page if current_page else 1
        total_items = len(df_filtered)
        max_pages = (total_items + PAGE_SIZE_EVENTS - 1) // PAGE_SIZE_EVENTS

        start_idx = (current_page - 1) * PAGE_SIZE_EVENTS
        end_idx = start_idx + PAGE_SIZE_EVENTS
        df_paginated = df_filtered.iloc[start_idx:end_idx]

        # Define columns for the upcoming events table
        columns_to_display = ['title', 'start_date', 'location', 'type', 'cost_numeric']
        table = create_events_table(df_paginated, table_id="upcoming-events-table", columns_to_display=columns_to_display)

        actual_page = min(current_page, max_pages) if max_pages > 0 else 1
        return table, max_pages if max_pages > 0 else 1, actual_page

    @app.callback(
        Output("upcoming-events-pagination", "active_page", allow_duplicate=True),
        Input("upcoming-event-type-filter", "value"),
        Input("upcoming-event-free-checkbox", "value"),
        prevent_initial_call=True
    )
    def reset_upcoming_pagination(_, __):
        return 1

    # Populate filter dropdowns for upcoming events (could also be done for search tab)
    @app.callback(
        Output("upcoming-event-type-filter", "options"),
        Input("upcoming-event-type-filter", "id") # Dummy input to trigger on load
    )
    def populate_upcoming_event_type_filters(_):
        if EVENTS_DATA_LOADED and not TECH_EVENTS_DF.empty and 'type' in TECH_EVENTS_DF.columns:
            types = sorted(TECH_EVENTS_DF['type'].dropna().unique().tolist())
            return [{'label': t, 'value': t} for t in types]
        return []

    # Callbacks for "Search Events" Tab
    @app.callback(
        Output("search-events-table-container", "children"),
        Output("search-events-pagination", "max_value"),
        Output("search-events-pagination", "active_page"),
        Input("search-events-query", "value"),
        Input("search-event-type-filter", "value"),
        Input("search-event-format-filter", "value"),
        Input("search-events-sort", "value"),
        # Input("search-event-score-slider", "value"), # If slider is added
        Input("search-events-pagination", "active_page")
    )
    def update_search_events_table(query, event_type, event_format, sort_by, current_page): #, score_range
        if not EVENTS_DATA_LOADED or TECH_EVENTS_DF.empty:
            return dbc.Alert("Tech Events data not available.", color="warning"), 1, 1

        df_filtered = TECH_EVENTS_DF.copy()

        if query:
            query_lower = query.lower()
            df_filtered = df_filtered[
                df_filtered['title'].str.lower().contains(query_lower, na=False) |
                df_filtered['description'].fillna('').str.lower().contains(query_lower, na=False)
            ]
        if event_type:
            df_filtered = df_filtered[df_filtered['type'] == event_type]
        if event_format:
            df_filtered = df_filtered[df_filtered['format'] == event_format]
        # if score_range: # If slider is used
        #     df_filtered = df_filtered[
        #         (df_filtered['quality_score_numeric'] >= score_range[0]) &
        #         (df_filtered['quality_score_numeric'] <= score_range[1])
        #     ]

        if sort_by == 'date_asc': # Upcoming first
            df_filtered = df_filtered.sort_values(by='start_date', ascending=True, na_position='last')
        elif sort_by == 'date_desc': # Newest added / later events
            df_filtered = df_filtered.sort_values(by='start_date', ascending=False, na_position='last')
        elif sort_by == 'score_desc':
            df_filtered = df_filtered.sort_values(by='quality_score_numeric', ascending=False, na_position='last')

        if df_filtered.empty:
            return dbc.Alert("No events match your search criteria.", color="info"), 1, 1

        current_page = current_page if current_page else 1
        total_items = len(df_filtered)
        max_pages = (total_items + PAGE_SIZE_EVENTS - 1) // PAGE_SIZE_EVENTS

        start_idx = (current_page - 1) * PAGE_SIZE_EVENTS
        end_idx = start_idx + PAGE_SIZE_EVENTS
        df_paginated = df_filtered.iloc[start_idx:end_idx]

        columns_to_display = ['title', 'start_date', 'location', 'type', 'format', 'cost_numeric', 'quality_score_numeric']
        table = create_events_table(df_paginated, table_id="search-events-table", columns_to_display=columns_to_display)

        actual_page = min(current_page, max_pages) if max_pages > 0 else 1
        return table, max_pages if max_pages > 0 else 1, actual_page

    @app.callback(
        Output("search-events-pagination", "active_page", allow_duplicate=True),
        Input("search-events-query", "value"),
        Input("search-event-type-filter", "value"),
        Input("search-event-format-filter", "value"),
        Input("search-events-sort", "value"),
        # Input("search-event-score-slider", "value"),
        prevent_initial_call=True
    )
    def reset_search_events_pagination(_, __, ___, ____): #, _____
        return 1

    # Populate filter dropdowns for search events tab
    @app.callback(
        Output("search-event-type-filter", "options"),
        Output("search-event-format-filter", "options"),
        Input("search-event-type-filter", "id") # Dummy input
    )
    def populate_search_event_filters(_):
        if EVENTS_DATA_LOADED and not TECH_EVENTS_DF.empty:
            type_options = []
            if 'type' in TECH_EVENTS_DF.columns:
                types = sorted(TECH_EVENTS_DF['type'].dropna().unique().tolist())
                type_options = [{'label': t, 'value': t} for t in types]

            format_options = []
            if 'format' in TECH_EVENTS_DF.columns:
                formats = sorted(TECH_EVENTS_DF['format'].dropna().unique().tolist())
                format_options = [{'label': f, 'value': f} for f in formats]
            return type_options, format_options
        return [], []


if __name__ == '__main__':
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_tech_events_tab(), fluid=True, className="py-4")
    register_tech_events_callbacks(app_test) # Register callbacks
    print(f"Events Test: Data loaded - {EVENTS_DATA_LOADED}, DataFrame empty - {TECH_EVENTS_DF.empty}")
    if EVENTS_DATA_LOADED and not TECH_EVENTS_DF.empty:
        print(TECH_EVENTS_DF.head(2))
    app_test.run_server(debug=True, port=8060)
