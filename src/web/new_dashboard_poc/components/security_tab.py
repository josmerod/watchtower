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
SECURITY_DATA_PATH = get_data_path("security_vulnerabilities", "vulnerabilities_latest.json")
SECURITY_VULNS_DF = pd.DataFrame()
SECURITY_DATA_LOADED = False
PAGE_SIZE_SECURITY = 15

# --- Date Parsing Utility ---
def parse_security_date(date_str):
    if pd.isna(date_str) or not date_str: return None
    try: # ISO format
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc)
    except ValueError: pass
    # Add other common formats if needed
    common_formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%Y/%m/%d"]
    for fmt in common_formats:
        try:
            dt = datetime.strptime(str(date_str), fmt)
            return dt.replace(tzinfo=timezone.utc) # Assume UTC if naive
        except ValueError: continue
    try: # Epoch timestamp
        ts = float(date_str)
        if ts > 10000000000: ts /= 1000 # ms to s
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except ValueError: pass
    print(f"Warning (Security): Could not parse date: {date_str}")
    return None

# --- Data Loading ---
def load_security_vulnerabilities():
    global SECURITY_VULNS_DF, SECURITY_DATA_LOADED
    file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), SECURITY_DATA_PATH))

    if not file_exists(file_path):
        print(f"Warning (Security): File not found at {file_path}")
        SECURITY_VULNS_DF = pd.DataFrame()
        SECURITY_DATA_LOADED = True # Mark as attempted
        return

    try:
        df = pd.read_json(file_path)
    except Exception as e:
        print(f"Error (Security): Failed to load or parse {file_path}. Error: {e}")
        SECURITY_VULNS_DF = pd.DataFrame()
        SECURITY_DATA_LOADED = True
        return

    if df.empty:
        print(f"Info (Security): {file_path} was empty.")
        SECURITY_VULNS_DF = pd.DataFrame()
        SECURITY_DATA_LOADED = True
        return

    # Standardize columns
    # cve_id, title, severity_score, risk_level, source_name, source_url, affected_packages_str, patch_available, published_date
    df.rename(columns={
        'id': 'cve_id', # Common for CVE ID
        'name': 'title', # Common for vulnerability title/name
        'cvss_score': 'severity_score', # Example CVSS score field
        'severity': 'risk_level', # Example risk level field (e.g., Critical, High)
        'source': 'source_name',
        'url': 'source_url',
        'link': 'source_url', # Alternative
        'affects': 'affected_packages_raw', # Assuming this might be a list or complex obj
        'has_patch': 'patch_available', # Boolean
        'published': 'published_date_str',
        'publishedDate': 'published_date_str',
        'created_at': 'published_date_str'
    }, inplace=True)

    expected_cols = ['cve_id', 'title', 'severity_score', 'risk_level', 'source_name', 'source_url', 'affected_packages_raw', 'patch_available', 'published_date_str']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df['published_date'] = df['published_date_str'].apply(parse_security_date)
    df['severity_score_numeric'] = pd.to_numeric(df['severity_score'], errors='coerce')

    # Process affected_packages
    def format_affected_packages(data):
        if pd.isna(data): return "N/A"
        try:
            if isinstance(data, str): # If it's a JSON string
                data = json.loads(data)

            if isinstance(data, list):
                if not data: return "None"
                # If list of strings
                if all(isinstance(item, str) for item in data):
                    return ", ".join(data[:3]) + (", ..." if len(data) > 3 else "")
                # If list of dicts, e.g., [{'name': 'pkg1', 'version': '1.0'}, ...]
                elif all(isinstance(item, dict) and 'name' in item for item in data):
                    names = [f"{item['name']}{'@'+item.get('version','*') if item.get('version') else ''}" for item in data]
                    return ", ".join(names[:3]) + (", ..." if len(names) > 3 else "")
            return str(data)[:100] # Fallback for other types, truncated
        except json.JSONDecodeError:
            return str(data)[:100] # If not valid JSON string, just show as is (truncated)
        except Exception:
            return "Error processing"

    df['affected_packages_str'] = df['affected_packages_raw'].apply(format_affected_packages)

    # Default sort: newest published, then highest severity
    df = df.sort_values(by=['published_date', 'severity_score_numeric'], ascending=[False, False], na_position='last')

    SECURITY_VULNS_DF = df
    SECURITY_DATA_LOADED = True
    print(f"Info (Security): Loaded {len(df)} vulnerabilities.")

load_security_vulnerabilities()

# --- Layout Rendering Functions ---
def create_security_table(df_subset, table_id="security-table"):
    if df_subset.empty:
        return dbc.Alert("No vulnerabilities match the current criteria.", color="info")

    header_map = {
        'cve_id': "CVE ID", 'title': "Title", 'severity_score_numeric': "Score",
        'risk_level': "Risk", 'source_name': "Source",
        'affected_packages_str': "Affected Packages",
        'patch_available': "Patch?", 'published_date': "Published"
    }
    cols_to_display = list(header_map.keys())

    table_header = [html.Thead(html.Tr([html.Th(header_map.get(col, col)) for col in cols_to_display]))]

    table_body_rows = []
    for _, row in df_subset.iterrows():
        cells = []
        for col in cols_to_display:
            val = row.get(col)
            if col == 'cve_id':
                cell_content = html.A(val if pd.notna(val) else 'N/A', href=row.get('source_url'), target="_blank")
            elif col == 'published_date':
                cell_content = val.strftime('%Y-%m-%d') if pd.notna(val) else 'N/A'
            elif col == 'patch_available':
                cell_content = "Yes" if val == True else ("No" if val == False else "N/A")
            elif col == 'severity_score_numeric':
                cell_content = f"{val:.1f}" if pd.notna(val) else "N/A"
            elif col == 'risk_level': # Could use dbc.Badge here
                risk_color_map = {"critical": "danger", "high": "warning", "medium": "info", "low": "success"}
                color = risk_color_map.get(str(val).lower(), "secondary")
                cell_content = dbc.Badge(str(val) if pd.notna(val) else "N/A", color=color, className="me-1")
            else:
                cell_content = str(val) if pd.notna(val) else 'N/A'
            cells.append(html.Td(cell_content))
        table_body_rows.append(html.Tr(cells))

    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(table_header + table_body, id=table_id, striped=True, bordered=True, hover=True, responsive=True, size="sm")

def render_security_tab():
    if not SECURITY_DATA_LOADED or SECURITY_VULNS_DF.empty:
        return html.Div([
            html.H3("Vulnerabilidades de Seguridad", className="mb-3"),
            dbc.Alert("Security vulnerabilities data could not be loaded or is empty.", color="danger")
        ])

    # Summary Stats
    total_vulns = len(SECURITY_VULNS_DF)
    # Assuming 'risk_level' contains 'Critical' or 'CRITICAL'
    critical_count = len(SECURITY_VULNS_DF[SECURITY_VULNS_DF['risk_level'].astype(str).str.lower() == 'critical']) if 'risk_level' in SECURITY_VULNS_DF.columns else 0
    avg_severity = SECURITY_VULNS_DF['severity_score_numeric'].mean() if 'severity_score_numeric' in SECURITY_VULNS_DF.columns and SECURITY_VULNS_DF['severity_score_numeric'].notna().any() else 0

    summary_stats = dbc.Row([
        dbc.Col(dbc.Card([dbc.CardHeader("Total Vulnerabilidades"), dbc.CardBody(f"{total_vulns:,}")], color="primary", inverse=True), md=4),
        dbc.Col(dbc.Card([dbc.CardHeader("Críticas"), dbc.CardBody(f"{critical_count:,}")], color="danger", inverse=True), md=4),
        dbc.Col(dbc.Card([dbc.CardHeader("Severidad Media"), dbc.CardBody(f"{avg_severity:.1f}" if avg_severity > 0 else "N/A")], color="warning", inverse=True), md=4),
    ], className="mb-4")

    # Filter options
    risk_options = []
    if 'risk_level' in SECURITY_VULNS_DF.columns and SECURITY_VULNS_DF['risk_level'].notna().any():
        risk_options = [{'label': r, 'value': r} for r in sorted(SECURITY_VULNS_DF['risk_level'].dropna().unique())]

    patch_options = [
        {'label': 'Sí', 'value': 'yes'},
        {'label': 'No', 'value': 'no'},
        {'label': 'Desconocido', 'value': 'unknown'} # Assuming None/NaN means unknown
    ]

    sort_options = [
        {'label': 'Fecha Publicación (Más Recientes)', 'value': 'date_desc'},
        {'label': 'Fecha Publicación (Más Antiguas)', 'value': 'date_asc'},
        {'label': 'Severidad (Más Alta)', 'value': 'severity_desc'},
        {'label': 'Severidad (Más Baja)', 'value': 'severity_asc'},
    ]

    filters_row = dbc.Row([
        dbc.Col(dbc.Input(id="security-search-input", placeholder="Buscar por Título/CVE ID..."), md=4, className="mb-2"),
        dbc.Col(dcc.Dropdown(id="security-risk-filter", options=risk_options, placeholder="Filtrar por Riesgo..."), md=2, className="mb-2"),
        dbc.Col(dcc.Dropdown(id="security-patch-filter", options=patch_options, placeholder="Filtrar por Parche..."), md=3, className="mb-2"),
        dbc.Col(dcc.Dropdown(id="security-sort-dropdown", options=sort_options, value='date_desc', placeholder="Ordenar Por...", clearable=False), md=3, className="mb-2"),
    ], className="mb-3")

    return html.Div([
        html.H3("Vulnerabilidades de Seguridad", className="mb-3"),
        summary_stats,
        filters_row,
        html.Div(id="security-table-container"),
        dbc.Pagination(id="security-pagination", max_value=1, active_page=1, className="mt-3 justify-content-center")
    ])

# --- Callbacks ---
def register_security_callbacks(app):
    @app.callback(
        Output("security-table-container", "children"),
        Output("security-pagination", "max_value"),
        Output("security-pagination", "active_page"),
        Input("security-search-input", "value"),
        Input("security-risk-filter", "value"),
        Input("security-patch-filter", "value"),
        Input("security-sort-dropdown", "value"),
        Input("security-pagination", "active_page")
    )
    def update_security_table(search_term, risk_level, patch_status, sort_by, current_page):
        if not SECURITY_DATA_LOADED or SECURITY_VULNS_DF.empty:
            return dbc.Alert("Security data not available.", color="warning"), 1, 1

        df_filtered = SECURITY_VULNS_DF.copy()

        if search_term:
            search_lower = search_term.lower()
            df_filtered = df_filtered[
                df_filtered['title'].astype(str).str.lower().contains(search_lower, na=False) |
                df_filtered['cve_id'].astype(str).str.lower().contains(search_lower, na=False) |
                df_filtered['affected_packages_str'].astype(str).str.lower().contains(search_lower, na=False)
            ]

        if risk_level:
            df_filtered = df_filtered[df_filtered['risk_level'] == risk_level]

        if patch_status:
            if patch_status == 'yes':
                df_filtered = df_filtered[df_filtered['patch_available'] == True]
            elif patch_status == 'no':
                df_filtered = df_filtered[df_filtered['patch_available'] == False]
            elif patch_status == 'unknown': # Assuming None/NaN means unknown
                 df_filtered = df_filtered[df_filtered['patch_available'].isna()]


        if sort_by == 'date_desc':
            df_filtered = df_filtered.sort_values(by='published_date', ascending=False, na_position='last')
        elif sort_by == 'date_asc':
            df_filtered = df_filtered.sort_values(by='published_date', ascending=True, na_position='last')
        elif sort_by == 'severity_desc':
            df_filtered = df_filtered.sort_values(by='severity_score_numeric', ascending=False, na_position='last')
        elif sort_by == 'severity_asc':
            df_filtered = df_filtered.sort_values(by='severity_score_numeric', ascending=True, na_position='last')

        if df_filtered.empty:
            return dbc.Alert("No vulnerabilities match your filters.", color="info"), 1, 1

        current_page = current_page if current_page else 1
        total_items = len(df_filtered)
        max_pages = (total_items + PAGE_SIZE_SECURITY - 1) // PAGE_SIZE_SECURITY

        start_idx = (current_page - 1) * PAGE_SIZE_SECURITY
        end_idx = start_idx + PAGE_SIZE_SECURITY
        df_paginated = df_filtered.iloc[start_idx:end_idx]

        table = create_security_table(df_paginated)
        actual_page = min(current_page, max_pages) if max_pages > 0 else 1
        return table, max_pages if max_pages > 0 else 1, actual_page

    @app.callback(
        Output("security-pagination", "active_page", allow_duplicate=True),
        Input("security-search-input", "value"),
        Input("security-risk-filter", "value"),
        Input("security-patch-filter", "value"),
        Input("security-sort-dropdown", "value"),
        prevent_initial_call=True
    )
    def reset_security_pagination(_, __, ___, ____):
        return 1

    # Callback to populate filter options dynamically (in case they change with data updates)
    # This is optional if options are static or pre-loaded sufficiently
    @app.callback(
        Output("security-risk-filter", "options"),
        # Output("security-patch-filter", "options"), # Patch options are static
        Input("security-risk-filter", "id") # Dummy input to trigger on load
    )
    def populate_security_filters(_):
        if SECURITY_DATA_LOADED and not SECURITY_VULNS_DF.empty:
            risk_options = []
            if 'risk_level' in SECURITY_VULNS_DF.columns and SECURITY_VULNS_DF['risk_level'].notna().any():
                 risk_options = [{'label': r, 'value': r} for r in sorted(SECURITY_VULNS_DF['risk_level'].dropna().unique())]
            return risk_options
        return []


if __name__ == '__main__':
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_security_tab(), fluid=True, className="py-4")
    register_security_callbacks(app_test) # Register callbacks
    print(f"Security Test: Data loaded - {SECURITY_DATA_LOADED}, DataFrame empty - {SECURITY_VULNS_DF.empty}")
    if SECURITY_DATA_LOADED and not SECURITY_VULNS_DF.empty:
        print(SECURITY_VULNS_DF.head(2))
        print(SECURITY_VULNS_DF[['cve_id', 'title', 'risk_level', 'patch_available', 'affected_packages_str']].head(2))
    app_test.run_server(debug=True, port=8062)
