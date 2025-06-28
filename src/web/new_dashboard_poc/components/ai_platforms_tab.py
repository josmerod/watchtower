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
from utils import get_data_path, file_exists, dir_exists, parse_date_universal, log_missing_file

from dash.exceptions import PreventUpdate
import re

# --- Constants ---
AI_DATA_PATH = get_data_path("ai_models", "ai_models_latest.json") # Assuming one consolidated file
AI_PLATFORMS_DATA = {
    'models': pd.DataFrame(),
    'updates': pd.DataFrame()
}
AI_DATA_LOADED = False
PAGE_SIZE_AI = 10

# Keywords for categorization
MODEL_RELEASE_KEYWORDS = ['model', 'release', 'launch', 'gpt', 'claude', 'gemini', 'llama', 'dall-e', 'stable diffusion', 'transformer', 'diffusion']
PLATFORM_UPDATE_KEYWORDS = ['update', 'announcement', 'feature', 'api', 'pricing', 'policy', 'safety', 'service', 'platform', 'tool', 'integration', 'console']


# --- Date Parsing Utility ---
# Using shared parse_date_universal function from utils.py

# --- Data Loading & Categorization ---
def load_ai_platforms_data():
    global AI_PLATFORMS_DATA, AI_DATA_LOADED
    file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), AI_DATA_PATH))

    if not file_exists(file_path):
        log_missing_file(file_path, "AI Platforms", is_optional=True)
        AI_DATA_LOADED = True # Mark as attempted
        return

    try:
        # Assuming the JSON is a list of dictionaries, each representing an update/release
        df_raw = pd.read_json(file_path)
    except Exception as e:
        print(f"Error (AI Platforms): Failed to load or parse {file_path}. Error: {e}")
        AI_DATA_LOADED = True
        return

    if df_raw.empty:
        print(f"Info (AI Platforms): {file_path} was empty.")
        AI_DATA_LOADED = True
        return

    # Standardize common columns first (adjust based on actual JSON keys)
    df_raw.rename(columns={
        'name': 'title', 'headline': 'title',
        'link': 'url', 'source_url': 'url',
        'published': 'published_date_str', 'date': 'published_date_str', 'created_at': 'published_date_str',
        'description': 'summary', 'content': 'summary', 'text': 'summary',
        'source_name': 'provider', 'author': 'provider', 'company': 'provider' # 'provider' is key
    }, inplace=True)

    # Ensure essential columns exist
    expected_cols = ['title', 'url', 'published_date_str', 'summary', 'provider']
    for col in expected_cols:
        if col not in df_raw.columns:
            df_raw[col] = "N/A" if col != 'summary' else "" # Default for provider, summary can be empty

    # Parse dates with error handling using shared function
    if 'published_date_str' in df_raw.columns:
        df_raw['published_date'] = df_raw['published_date_str'].apply(lambda x: parse_date_universal(x, "AI Platforms"))
    else:
        df_raw['published_date'] = pd.NaT  # Not a Time value
    
    # Only drop rows if the columns exist
    columns_to_check = [col for col in ['published_date', 'title', 'url'] if col in df_raw.columns]
    if columns_to_check:
        df_raw.dropna(subset=columns_to_check, inplace=True)

    # Normalize text for keyword search
    # Add defensive checks to prevent DataFrame.str accessor errors
    if 'title' not in df_raw.columns:
        df_raw['title'] = 'N/A'
    if 'summary' not in df_raw.columns:
        df_raw['summary'] = ''
    
    # Ensure we have valid data before applying string operations
    if not df_raw.empty:
        df_raw['text_for_search'] = df_raw['title'].fillna('').astype(str).str.lower() + " " + df_raw['summary'].fillna('').astype(str).str.lower()
    else:
        df_raw['text_for_search'] = ''

    # Categorize
    model_mask = df_raw['text_for_search'].apply(lambda text: any(keyword in text for keyword in MODEL_RELEASE_KEYWORDS))
    platform_mask = df_raw['text_for_search'].apply(lambda text: any(keyword in text for keyword in PLATFORM_UPDATE_KEYWORDS))

    # Prioritize model releases if overlap
    if 'published_date' in df_raw.columns and not df_raw.empty:
        AI_PLATFORMS_DATA['models'] = df_raw[model_mask].sort_values(by='published_date', ascending=False)
        AI_PLATFORMS_DATA['updates'] = df_raw[platform_mask & ~model_mask].sort_values(by='published_date', ascending=False)
    else:
        AI_PLATFORMS_DATA['models'] = df_raw[model_mask] if not df_raw.empty else pd.DataFrame()
        AI_PLATFORMS_DATA['updates'] = df_raw[platform_mask & ~model_mask] if not df_raw.empty else pd.DataFrame()
    # Alternative: if items can be in both, just use platform_mask
    # AI_PLATFORMS_DATA['updates'] = df_raw[platform_mask].sort_values(by='published_date', ascending=False)


    AI_DATA_LOADED = True
    print(f"Info (AI Platforms): Loaded {len(df_raw)} total items. Categorized into {len(AI_PLATFORMS_DATA['models'])} model releases and {len(AI_PLATFORMS_DATA['updates'])} platform updates.")

load_ai_platforms_data()

# --- Layout Rendering & Callbacks ---
def create_ai_table(df_subset, table_id_suffix):
    if df_subset.empty:
        return dbc.Alert("No items match the current criteria.", color="info")

    table_header = [html.Thead(html.Tr([
        html.Th("Provider"), html.Th("Title/Update"), html.Th("Date"), html.Th("Summary (hover)")
    ]))]

    table_body_rows = []
    for _, row in df_subset.iterrows():
        summary_snippet = str(row.get('summary', ''))[:150] + "..." if pd.notna(row.get('summary')) and len(str(row.get('summary',''))) > 150 else str(row.get('summary',''))
        title_cell = html.A(row.get('title', 'N/A'), href=row.get('url'), target="_blank", rel="noopener noreferrer", title=summary_snippet if len(summary_snippet)>50 else None)

        table_body_rows.append(html.Tr([
            html.Td(row.get('provider', 'N/A')),
            html.Td(title_cell),
            html.Td(row['published_date'].strftime('%Y-%m-%d') if pd.notna(row.get('published_date')) else 'N/A'),
            html.Td(summary_snippet if len(summary_snippet) <= 50 else html.Abbr("Hover", title=summary_snippet)) # Show short summary or use Abbr for hover
        ]))
    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(table_header + table_body, id=f"ai-{table_id_suffix}-table", striped=True, bordered=True, hover=True, responsive=True, size="sm")

def render_single_ai_sub_tab(df, source_category_key): # e.g. source_category_key = 'models' or 'updates'
    source_name_display = "Model Releases" if source_category_key == 'models' else "Platform Updates"

    if not AI_DATA_LOADED: # General load check
        return dbc.Alert("AI Platforms data is still loading or failed to load.", color="warning", className="mt-3")
    if df.empty:
        return dbc.Alert(f"No {source_name_display.lower()} found or data is unavailable.", color="info", className="mt-3")

    # Dynamic options for provider filter
    provider_options = []
    if 'provider' in df.columns and df['provider'].notna().any():
        provider_options = [{'label': p, 'value': p} for p in sorted(df['provider'].dropna().unique()) if p != "N/A"]

    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Input(id=f"ai-{source_category_key}-search-input", placeholder=f"Search in {source_name_display}..."), md=8, className="mb-2"),
            dbc.Col(dcc.Dropdown(id=f"ai-{source_category_key}-provider-filter", options=provider_options, placeholder="Filter by Provider..."), md=4, className="mb-2"),
        ], className="mt-3 mb-3"),
        html.Div(f"Total {source_name_display.lower()}: {len(df)}", className="text-muted small mb-2"),
        html.Div(id=f"ai-{source_category_key}-table-container"),
        dbc.Pagination(id=f"ai-{source_category_key}-pagination", max_value=1, active_page=1, className="mt-3 justify-content-center")
    ])

def render_ai_platforms_tab():
    if not AI_DATA_LOADED:
        return dbc.Alert("AI Platforms data is loading or could not be loaded. Please check data sources.", color="danger", className="mt-3")

    total_items_loaded = len(AI_PLATFORMS_DATA.get('models', pd.DataFrame())) + len(AI_PLATFORMS_DATA.get('updates', pd.DataFrame()))

    # Consolidate all providers for unique count
    all_providers = []
    if not AI_PLATFORMS_DATA['models'].empty and 'provider' in AI_PLATFORMS_DATA['models'].columns:
        all_providers.extend(AI_PLATFORMS_DATA['models']['provider'].dropna().tolist())
    if not AI_PLATFORMS_DATA['updates'].empty and 'provider' in AI_PLATFORMS_DATA['updates'].columns:
        all_providers.extend(AI_PLATFORMS_DATA['updates']['provider'].dropna().tolist())
    unique_providers_count = len(set(all_providers))


    summary_stats = dbc.Row([
        dbc.Col(dbc.Card([dbc.CardHeader("Total Items Analizados"), dbc.CardBody(f"{total_items_loaded:,}")], color="primary", inverse=True), md=6, className="mb-2"),
        dbc.Col(dbc.Card([dbc.CardHeader("Proveedores Únicos"), dbc.CardBody(f"{unique_providers_count:,}")], color="info", inverse=True), md=6, className="mb-2"),
    ], className="mb-4")

    return html.Div([
        html.H3("Plataformas IA", className="mb-3"),
        summary_stats,
        dbc.Tabs(id="ai-platforms-main-tabs", active_tab="tab-ai-models", children=[
            dbc.Tab(label="Modelos Recientes", tab_id="tab-ai-models",
                    children=render_single_ai_sub_tab(AI_PLATFORMS_DATA['models'], 'models')),
            dbc.Tab(label="Actualizaciones de Plataforma", tab_id="tab-ai-updates",
                    children=render_single_ai_sub_tab(AI_PLATFORMS_DATA['updates'], 'updates')),
        ])
    ])

# --- Callbacks ---
def register_ai_platforms_callbacks(app):
    for category_key in ['models', 'updates']:
        @app.callback(
            Output(f"ai-{category_key}-table-container", "children"),
            Output(f"ai-{category_key}-pagination", "max_value"),
            Output(f"ai-{category_key}-pagination", "active_page"),
            Input(f"ai-{category_key}-search-input", "value"),
            Input(f"ai-{category_key}-provider-filter", "value"),
            Input(f"ai-{category_key}-pagination", "active_page"),
            prevent_initial_call=True
        )
        def update_ai_table(search_term, provider_filter, current_page, cat_key=category_key):
            if not AI_DATA_LOADED or AI_PLATFORMS_DATA.get(cat_key, pd.DataFrame()).empty:
                return dbc.Alert(f"Data for {cat_key} not available.", color="warning"), 1, 1

            df_category = AI_PLATFORMS_DATA[cat_key].copy()
            df_filtered = df_category

            if provider_filter:
                df_filtered = df_filtered[df_filtered['provider'] == provider_filter]

            if search_term and not df_filtered.empty:
                search_lower = search_term.lower()
                # Add defensive checks for the search filtering
                title_mask = df_filtered['title'].fillna('').astype(str).str.lower().contains(search_lower, na=False) if 'title' in df_filtered.columns else pd.Series([False] * len(df_filtered))
                summary_mask = df_filtered['summary'].fillna('').astype(str).str.lower().contains(search_lower, na=False) if 'summary' in df_filtered.columns else pd.Series([False] * len(df_filtered))
                df_filtered = df_filtered[title_mask | summary_mask]

            if df_filtered.empty:
                return dbc.Alert(f"No items match your criteria in {cat_key}.", color="info"), 1, 1

            current_page = current_page if current_page else 1
            total_items = len(df_filtered)
            max_pages = (total_items + PAGE_SIZE_AI - 1) // PAGE_SIZE_AI

            start_idx = (current_page - 1) * PAGE_SIZE_AI
            end_idx = start_idx + PAGE_SIZE_AI
            df_paginated = df_filtered.iloc[start_idx:end_idx]

            table = create_ai_table(df_paginated, cat_key)
            actual_page = min(current_page, max_pages) if max_pages > 0 else 1
            return table, max_pages if max_pages > 0 else 1, actual_page

        @app.callback(
            Output(f"ai-{category_key}-pagination", "active_page", allow_duplicate=True),
            Input(f"ai-{category_key}-search-input", "value"),
            Input(f"ai-{category_key}-provider-filter", "value"),
            prevent_initial_call=True
        )
        def reset_ai_pagination(_, __, cat_key_reset=category_key):
            return 1

        # Populate provider filter options
        @app.callback(
            Output(f"ai-{category_key}-provider-filter", "options"),
            Input(f"ai-{category_key}-provider-filter", "id"), # Trigger on load
        )
        def populate_ai_provider_filters(_, cat_key_filter=category_key):
            if AI_DATA_LOADED and not AI_PLATFORMS_DATA.get(cat_key_filter, pd.DataFrame()).empty:
                df_source = AI_PLATFORMS_DATA[cat_key_filter]
                if 'provider' in df_source.columns and df_source['provider'].notna().any():
                    providers = sorted(df_source['provider'].dropna().unique())
                    return [{'label': p, 'value': p} for p in providers if p != "N/A"]
            return []


if __name__ == '__main__':
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_ai_platforms_tab(), fluid=True, className="py-4")
    register_ai_platforms_callbacks(app_test)

    print(f"AI Platforms Data Loaded: {AI_DATA_LOADED}")
    print(f"Model Releases Count: {len(AI_PLATFORMS_DATA['models'])}")
    print(f"Platform Updates Count: {len(AI_PLATFORMS_DATA['updates'])}")
    app_test.run_server(debug=True, port=8064)
