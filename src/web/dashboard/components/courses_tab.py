import os
import json
import pandas as pd
from datetime import datetime, timezone
import dash
from dash import html, dcc, Input, Output, State, Patch
import dash_bootstrap_components as dbc

# Import shared utilities
from src.web.dashboard.utils import get_data_path, file_exists, dir_exists

from dash.exceptions import PreventUpdate

# --- Constants ---
COURSERA_DATA_PATH = get_data_path("classcentral", "coursera_courses.json")
UDEMY_DATA_PATH = get_data_path("udemy", "udemy_courses.json")
PLURALSIGHT_DATA_PATH = get_data_path("pluralsight_courses", "pluralsight_courses.json")

ALL_COURSES_DATA = {
    "coursera": pd.DataFrame(),
    "udemy": pd.DataFrame(),
    "pluralsight": pd.DataFrame(),
}
COURSES_DATA_LOADED = {"coursera": False, "udemy": False, "pluralsight": False}
# Page size for tables
PAGE_SIZE = 15


# --- Date Parsing Utility (can be adapted if formats differ) ---
def parse_course_date(date_str, source_format=None):
    if pd.isna(date_str) or not date_str:
        return None
    try:  # ISO format is common
        dt = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass
    if source_format:
        try:
            dt = datetime.strptime(str(date_str), source_format)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    # Add other common formats if needed
    common_formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%b %d, %Y", "%B %d, %Y"]
    for fmt in common_formats:
        try:
            dt = datetime.strptime(str(date_str), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    # Try epoch
    try:
        ts = float(date_str)
        if ts > 10000000000:
            ts /= 1000  # ms to s
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except ValueError:
        pass
    print(f"Warning (Courses): Could not parse date: {date_str}")
    return None


# --- Data Loading Functions ---
def load_coursera_data():
    global ALL_COURSES_DATA, COURSES_DATA_LOADED
    file_path = COURSERA_DATA_PATH

    if not file_exists(file_path):
        print(f"Warning (Coursera): File not found at {file_path}")
        ALL_COURSES_DATA["coursera"] = pd.DataFrame()
        COURSES_DATA_LOADED["coursera"] = True  # Mark as attempt to prevent reload loop
        return

    try:
        df = pd.read_json(file_path)
    except Exception as e:
        print(f"Error (Coursera): Failed to load or parse {file_path}. Error: {e}")
        ALL_COURSES_DATA["coursera"] = pd.DataFrame()
        COURSES_DATA_LOADED["coursera"] = True
        return

    if df.empty:
        print(f"Info (Coursera): {file_path} was empty.")
        ALL_COURSES_DATA["coursera"] = pd.DataFrame()
        COURSES_DATA_LOADED["coursera"] = True
        return

    # Standardize columns
    # title, url, description, institution, subject, language, duration, start_date, is_free, certificate_offered, scraped_at
    df.rename(
        columns={
            "name": "title",  # common alternative
            "link": "url",
            "partner": "institution",  # ClassCentral uses 'partner'
            "category": "subject",  # Or 'categories'
            "startDate": "start_date_str",
            "isFree": "is_free",
            "hasCertificate": "certificate_offered",
            "retrieved_at": "scraped_at_str",  # If this is the scrape date
            "last_updated": "scraped_at_str",  # Another common name for scrape date
        },
        inplace=True,
    )

    expected_cols = [
        "title",
        "url",
        "description",
        "institution",
        "subject",
        "language",
        "duration",
        "start_date_str",
        "is_free",
        "certificate_offered",
        "scraped_at_str",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df["start_date"] = df["start_date_str"].apply(lambda x: parse_course_date(x))
    df["scraped_at"] = df["scraped_at_str"].apply(
        lambda x: parse_course_date(x)
    )  # This is likely the "added" date

    # Sort by scraped_at (added date) or start_date if available
    sort_col = "scraped_at" if "scraped_at" in df.columns else "start_date"
    if sort_col in df.columns:
        df = df.sort_values(by=sort_col, ascending=False, na_position="last")

    ALL_COURSES_DATA["coursera"] = df
    COURSES_DATA_LOADED["coursera"] = True
    print(f"Info (Coursera): Loaded {len(df)} courses.")


def load_udemy_data():
    global ALL_COURSES_DATA, COURSES_DATA_LOADED
    file_path = UDEMY_DATA_PATH

    if not file_exists(file_path):
        print(f"Warning (Udemy): File not found at {file_path}")
        ALL_COURSES_DATA["udemy"] = pd.DataFrame()
        COURSES_DATA_LOADED["udemy"] = True
        return

    try:
        df = pd.read_json(file_path)
    except Exception as e:
        print(f"Error (Udemy): Failed to load or parse {file_path}. Error: {e}")
        ALL_COURSES_DATA["udemy"] = pd.DataFrame()
        COURSES_DATA_LOADED["udemy"] = True
        return

    if df.empty:
        print(f"Info (Udemy): {file_path} was empty.")
        ALL_COURSES_DATA["udemy"] = pd.DataFrame()
        COURSES_DATA_LOADED["udemy"] = True
        return

    # Standardize columns: title, url, scraped_at
    df.rename(
        columns={
            "course_title": "title",
            "course_url": "url",
            "created_at": "scraped_at_str",  # Assuming this is the scrape date
        },
        inplace=True,
    )

    expected_cols = [
        "title",
        "url",
        "scraped_at_str",
    ]  # Udemy data is simpler from this source
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df["scraped_at"] = df["scraped_at_str"].apply(lambda x: parse_course_date(x))

    if "scraped_at" in df.columns:
        df = df.sort_values(by="scraped_at", ascending=False, na_position="last")

    ALL_COURSES_DATA["udemy"] = df
    COURSES_DATA_LOADED["udemy"] = True
    print(f"Info (Udemy): Loaded {len(df)} courses.")


def load_pluralsight_data():
    global ALL_COURSES_DATA, COURSES_DATA_LOADED
    file_path = PLURALSIGHT_DATA_PATH

    if not file_exists(file_path):
        print(f"Warning (Pluralsight): File not found at {file_path}")
        ALL_COURSES_DATA["pluralsight"] = pd.DataFrame()
        COURSES_DATA_LOADED["pluralsight"] = True
        return

    try:
        df = pd.read_json(file_path)
    except Exception as e:
        print(f"Error (Pluralsight): Failed to load or parse {file_path}. Error: {e}")
        ALL_COURSES_DATA["pluralsight"] = pd.DataFrame()
        COURSES_DATA_LOADED["pluralsight"] = True
        return

    if df.empty:
        print(f"Info (Pluralsight): {file_path} was empty.")
        ALL_COURSES_DATA["pluralsight"] = pd.DataFrame()
        COURSES_DATA_LOADED["pluralsight"] = True
        return

    # Standardize columns for Pluralsight
    expected_cols = ["title", "url", "instructor", "duration", "level", "scraped_at"]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df["scraped_at_parsed"] = df["scraped_at"].apply(lambda x: parse_course_date(x))

    if "scraped_at_parsed" in df.columns:
        df = df.sort_values(by="scraped_at_parsed", ascending=False, na_position="last")

    ALL_COURSES_DATA["pluralsight"] = df
    COURSES_DATA_LOADED["pluralsight"] = True
    print(f"Info (Pluralsight): Loaded {len(df)} courses.")


def load_all_courses_data():
    load_coursera_data()
    load_udemy_data()
    load_pluralsight_data()
    print("Attempted to load all courses data.")


load_all_courses_data()


# --- Layout Rendering Functions ---
def format_coursera_display_date(dt_obj):
    if pd.isna(dt_obj) or dt_obj is None:
        return "N/A"
    return dt_obj.strftime("%Y-%m-%d")


def create_coursera_table(df_subset):
    if df_subset.empty:
        return dbc.Alert("No Coursera courses match your criteria.", color="info")

    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Title"),
                    html.Th("Institution"),
                    html.Th("Subject"),
                    html.Th("Language"),
                    html.Th("Duration"),
                    html.Th("Start Date"),
                    html.Th("Added"),
                    html.Th("Free"),
                    html.Th("Certificate"),
                ]
            )
        )
    ]

    table_body_rows = []
    for _, row in df_subset.iterrows():
        table_body_rows.append(
            html.Tr(
                [
                    html.Td(
                        html.A(
                            row.get("title", "N/A"),
                            href=row.get("url"),
                            target="_blank",
                        )
                    ),
                    html.Td(row.get("institution", "N/A")),
                    html.Td(row.get("subject", "N/A")),
                    html.Td(row.get("language", "N/A")),
                    html.Td(row.get("duration", "N/A")),
                    html.Td(format_coursera_display_date(row.get("start_date"))),
                    html.Td(format_coursera_display_date(row.get("scraped_at"))),
                    html.Td("Yes" if row.get("is_free") else "No"),
                    html.Td("Yes" if row.get("certificate_offered") else "No"),
                ]
            )
        )
    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(
        table_header + table_body,
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        size="sm",
        color="dark",
        className="table-responsive",
    )


def render_coursera_courses_sub_tab(df):
    if not COURSES_DATA_LOADED[
        "coursera"
    ]:  # Check if loading was even attempted and successful
        return dbc.Alert(
            "Coursera courses data failed to load. Check logs.",
            color="danger",
            className="mt-3",
        )
    if df.empty:  # Check if the dataframe itself is empty after successful load
        return dbc.Alert(
            "No Coursera courses data currently available (file might be empty or all data filtered out).",
            color="info",
            className="mt-3",
        )

    # Prepare filter options
    # For simplicity, using unique values directly. For very long lists, consider pre-filtering or search in dropdown.
    subject_options = (
        [
            {"label": i, "value": i}
            for i in df["subject"].dropna().unique().tolist()
            if i
        ]
        if "subject" in df.columns
        else []
    )
    language_options = (
        [
            {"label": i, "value": i}
            for i in df["language"].dropna().unique().tolist()
            if i
        ]
        if "language" in df.columns
        else []
    )

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Input(
                            id="coursera-search-input",
                            placeholder="Search by title/description...",
                        ),
                        md=4,
                        className="mb-2",
                    ),
                    dbc.Col(
                        dcc.Dropdown(
                            id="coursera-subject-dropdown",
                            options=subject_options,
                            placeholder="Filter by subject",
                        ),
                        md=3,
                        className="mb-2",
                    ),
                    dbc.Col(
                        dcc.Dropdown(
                            id="coursera-language-dropdown",
                            options=language_options,
                            placeholder="Filter by language",
                        ),
                        md=3,
                        className="mb-2",
                    ),
                    dbc.Col(
                        dbc.Checkbox(
                            id="coursera-free-checkbox", label="Only Free Courses"
                        ),
                        md=2,
                        className="mb-2 align-self-center",
                    ),
                ],
                className="mt-3 mb-3",
            ),
            html.Div(id="coursera-table-container"),
            # Custom pagination with better UX
            html.Div(
                id="coursera-pagination-wrapper",
                className="d-flex justify-content-between align-items-center mt-3",
                children=[
                    html.Div(id="coursera-pagination-info", className="text-muted"),
                    html.Div(
                        className="d-flex align-items-center gap-2",
                        children=[
                            dbc.Button(
                                "« Previous",
                                id="coursera-prev-btn",
                                size="sm",
                                outline=True,
                                color="primary",
                                disabled=True,
                            ),
                            dbc.Input(
                                id="coursera-page-input",
                                type="number",
                                value=1,
                                min=1,
                                max=1,
                                style={"width": "80px", "textAlign": "center"},
                                size="sm",
                            ),
                            html.Span("of", className="mx-2 text-muted"),
                            html.Span(
                                id="coursera-total-pages", className="text-muted"
                            ),
                            dbc.Button(
                                "Next »",
                                id="coursera-next-btn",
                                size="sm",
                                outline=True,
                                color="primary",
                                disabled=True,
                            ),
                        ],
                    ),
                ],
            ),
        ],
        className="mt-3",
    )


def render_udemy_courses_sub_tab(df):
    if not COURSES_DATA_LOADED["udemy"]:
        return dbc.Alert(
            "Udemy courses data failed to load. Check logs.",
            color="danger",
            className="mt-3",
        )
    if df.empty:
        return dbc.Alert(
            "No Udemy courses data currently available (file might be empty).",
            color="info",
            className="mt-3",
        )
    # Placeholder for actual layout
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Input(
                            id="udemy-search-input", placeholder="Search by title..."
                        ),
                        md=12,
                        className="mb-2",
                    ),
                ],
                className="mt-3 mb-3",
            ),
            html.Div(id="udemy-table-container"),
            # Custom pagination with better UX
            html.Div(
                id="udemy-pagination-wrapper",
                className="d-flex justify-content-between align-items-center mt-3",
                children=[
                    html.Div(id="udemy-pagination-info", className="text-muted"),
                    html.Div(
                        className="d-flex align-items-center gap-2",
                        children=[
                            dbc.Button(
                                "« Previous",
                                id="udemy-prev-btn",
                                size="sm",
                                outline=True,
                                color="primary",
                                disabled=True,
                            ),
                            dbc.Input(
                                id="udemy-page-input",
                                type="number",
                                value=1,
                                min=1,
                                max=1,
                                style={"width": "80px", "textAlign": "center"},
                                size="sm",
                            ),
                            html.Span("of", className="mx-2 text-muted"),
                            html.Span(id="udemy-total-pages", className="text-muted"),
                            dbc.Button(
                                "Next »",
                                id="udemy-next-btn",
                                size="sm",
                                outline=True,
                                color="primary",
                                disabled=True,
                            ),
                        ],
                    ),
                ],
            ),
        ],
        className="mt-3",
    )


# --- Main Layout ---
def render_courses_tab():
    # Initial check if any data was loaded to provide a general message
    # More specific messages are handled by individual sub-tab render functions
    if (
        not COURSES_DATA_LOADED["coursera"]
        and not COURSES_DATA_LOADED["udemy"]
        and not COURSES_DATA_LOADED["pluralsight"]
    ):
        return dbc.Alert(
            "All course data failed to load. Please check data sources and ETLs.",
            color="danger",
            className="mt-3",
        )

    # If one source loaded but not the other, the specific tab will show its own message.
    # This top-level check is for when *neither* loaded.

    return html.Div(
        [
            html.H3("Cursos Online", className="mb-3"),
            dbc.Tabs(
                id="courses-main-tabs",
                active_tab="tab-coursera",
                children=[  # Default to Coursera
                    dbc.Tab(
                        label="Coursera",
                        tab_id="tab-coursera",
                        children=render_coursera_courses_sub_tab(
                            ALL_COURSES_DATA["coursera"]
                        ),
                    ),
                    dbc.Tab(
                        label="Udemy",
                        tab_id="tab-udemy",
                        children=render_udemy_courses_sub_tab(
                            ALL_COURSES_DATA["udemy"]
                        ),
                    ),
                    dbc.Tab(
                        label="Pluralsight",
                        tab_id="tab-pluralsight",
                        children=render_pluralsight_courses_sub_tab(
                            ALL_COURSES_DATA["pluralsight"]
                        ),
                    ),
                ],
            ),
        ]
    )


# --- Callbacks ---
def register_courses_callbacks(app):
    @app.callback(
        Output("coursera-table-container", "children"),
        Output("coursera-pagination-info", "children"),
        Output("coursera-total-pages", "children"),
        Output("coursera-page-input", "max"),
        Output("coursera-page-input", "value"),
        Output("coursera-prev-btn", "disabled"),
        Output("coursera-next-btn", "disabled"),
        Input("coursera-search-input", "value"),
        Input("coursera-subject-dropdown", "value"),
        Input("coursera-language-dropdown", "value"),
        Input(
            "coursera-free-checkbox", "value"
        ),  # This is a list if checked, e.g. [True] or empty []
        Input("coursera-page-input", "value"),
        Input("coursera-prev-btn", "n_clicks"),
        Input("coursera-next-btn", "n_clicks"),
        prevent_initial_call=False,
    )
    def update_coursera_table(
        search_term,
        subject,
        language,
        free_only_checked,
        current_page,
        prev_clicks,
        next_clicks,
    ):
        try:
            if not COURSES_DATA_LOADED["coursera"]:
                return (
                    dbc.Alert("Loading Coursera data...", color="info"),
                    "",
                    "1",
                    1,
                    1,
                    True,
                    True,
                )

            df_filtered = ALL_COURSES_DATA["coursera"].copy()
            if df_filtered.empty:
                return (
                    dbc.Alert("No Coursera data available.", color="warning"),
                    "",
                    "1",
                    1,
                    1,
                    True,
                    True,
                )

            if search_term:
                search_lower = search_term.lower()
                # Assuming description might be NaN, fill with empty string for search
                df_filtered = df_filtered[
                    df_filtered["title"].str.lower().contains(search_lower, na=False)
                    | df_filtered["description"]
                    .fillna("")
                    .str.lower()
                    .contains(search_lower, na=False)
                ]
            if subject:
                df_filtered = df_filtered[df_filtered["subject"] == subject]
            if language:
                df_filtered = df_filtered[df_filtered["language"] == language]
            if (
                free_only_checked
            ):  # Checkbox value is a list, [True] if checked, else None or empty list
                # is_free column should be boolean True/False after loading.
                # If it can be None/NaN, handle that: df_filtered['is_free'].fillna(False) == True
                df_filtered = df_filtered[df_filtered["is_free"] == True]

            if df_filtered.empty:
                return (
                    dbc.Alert("No Coursera courses match your filters.", color="info"),
                    "",
                    "1",
                    1,
                    1,
                    True,
                    True,
                )

            total_items = len(df_filtered)
            max_pages = max(1, (total_items + PAGE_SIZE - 1) // PAGE_SIZE)

            # Handle pagination button clicks
            ctx = dash.callback_context
            if ctx.triggered:
                prop_id = ctx.triggered[0]["prop_id"]
                if "prev-btn" in prop_id:
                    current_page = max(1, (current_page or 1) - 1)
                elif "next-btn" in prop_id:
                    current_page = min(max_pages, (current_page or 1) + 1)

            current_page = max(1, min(current_page or 1, max_pages))

            start_idx = (current_page - 1) * PAGE_SIZE
            end_idx = start_idx + PAGE_SIZE
            df_paginated = df_filtered.iloc[start_idx:end_idx]

            table = create_coursera_table(df_paginated)

            # Create pagination info
            pagination_info = f"Showing {start_idx + 1}-{min(end_idx, total_items)} of {total_items} courses"

            # Button states
            prev_disabled = current_page <= 1
            next_disabled = current_page >= max_pages

            return (
                table,
                pagination_info,
                str(max_pages),
                max_pages,
                current_page,
                prev_disabled,
                next_disabled,
            )

        except Exception as e:
            print(f"Error in coursera table update: {e}")
            return (
                dbc.Alert(f"Error loading Coursera data: {str(e)}", color="danger"),
                "",
                "1",
                1,
                1,
                True,
                True,
            )

    # Reset to page 1 when filters change
    @app.callback(
        Output("coursera-page-input", "value", allow_duplicate=True),
        Input("coursera-search-input", "value"),
        Input("coursera-subject-dropdown", "value"),
        Input("coursera-language-dropdown", "value"),
        Input("coursera-free-checkbox", "value"),
        prevent_initial_call=True,
    )
    def reset_coursera_pagination(_, __, ___, ____):
        return 1  # Reset to page 1

    # Udemy Callbacks (similar structure)
    @app.callback(
        Output("udemy-table-container", "children"),
        Output("udemy-pagination-info", "children"),
        Output("udemy-total-pages", "children"),
        Output("udemy-page-input", "max"),
        Output("udemy-page-input", "value"),
        Output("udemy-prev-btn", "disabled"),
        Output("udemy-next-btn", "disabled"),
        Input("udemy-search-input", "value"),
        Input("udemy-page-input", "value"),
        Input("udemy-prev-btn", "n_clicks"),
        Input("udemy-next-btn", "n_clicks"),
        prevent_initial_call=False,
    )
    def update_udemy_table(search_term, current_page, prev_clicks, next_clicks):
        try:
            if not COURSES_DATA_LOADED["udemy"]:
                return (
                    dbc.Alert("Loading Udemy data...", color="info"),
                    "",
                    "1",
                    1,
                    1,
                    True,
                    True,
                )

            df_filtered = ALL_COURSES_DATA["udemy"].copy()
            if df_filtered.empty:
                return (
                    dbc.Alert("No Udemy data available.", color="warning"),
                    "",
                    "1",
                    1,
                    1,
                    True,
                    True,
                )

            if search_term:
                search_lower = search_term.lower()
                df_filtered = df_filtered[
                    df_filtered["title"].str.lower().contains(search_lower, na=False)
                ]

            if df_filtered.empty:
                return (
                    dbc.Alert("No Udemy courses match your filters.", color="info"),
                    "",
                    "1",
                    1,
                    1,
                    True,
                    True,
                )

            total_items = len(df_filtered)
            max_pages = max(1, (total_items + PAGE_SIZE - 1) // PAGE_SIZE)

            # Handle pagination button clicks
            ctx = dash.callback_context
            if ctx.triggered:
                prop_id = ctx.triggered[0]["prop_id"]
                if "prev-btn" in prop_id:
                    current_page = max(1, (current_page or 1) - 1)
                elif "next-btn" in prop_id:
                    current_page = min(max_pages, (current_page or 1) + 1)

            current_page = max(1, min(current_page or 1, max_pages))

            start_idx = (current_page - 1) * PAGE_SIZE
            end_idx = start_idx + PAGE_SIZE
            df_paginated = df_filtered.iloc[start_idx:end_idx]

            # Need a create_udemy_table helper
            table_header = [
                html.Thead(html.Tr([html.Th("Title"), html.Th("Added Date")]))
            ]
            table_body_rows = []
            for _, row in df_paginated.iterrows():
                table_body_rows.append(
                    html.Tr(
                        [
                            html.Td(
                                html.A(
                                    row.get("title", "N/A"),
                                    href=row.get("url"),
                                    target="_blank",
                                )
                            ),
                            html.Td(
                                format_coursera_display_date(row.get("scraped_at"))
                            ),  # Reusing date formatter
                        ]
                    )
                )
            table_body = [html.Tbody(table_body_rows)]
            table = dbc.Table(
                table_header + table_body,
                bordered=True,
                hover=True,
                responsive=True,
                striped=True,
                size="sm",
                color="dark",
                className="table-responsive",
            )

            # Create pagination info
            pagination_info = f"Showing {start_idx + 1}-{min(end_idx, total_items)} of {total_items} courses"

            # Button states
            prev_disabled = current_page <= 1
            next_disabled = current_page >= max_pages

            return (
                table,
                pagination_info,
                str(max_pages),
                max_pages,
                current_page,
                prev_disabled,
                next_disabled,
            )

        except Exception as e:
            print(f"Error in udemy table update: {e}")
            return (
                dbc.Alert(f"Error loading Udemy data: {str(e)}", color="danger"),
                "",
                "1",
                1,
                1,
                True,
                True,
            )

    @app.callback(
        Output("udemy-page-input", "value", allow_duplicate=True),
        Input("udemy-search-input", "value"),
        prevent_initial_call=True,
    )
    def reset_udemy_pagination(_):
        return 1

    # Pluralsight Callbacks (similar structure to Udemy)
    @app.callback(
        Output("pluralsight-table-container", "children"),
        Output("pluralsight-pagination-info", "children"),
        Output("pluralsight-total-pages", "children"),
        Output("pluralsight-page-input", "max"),
        Output("pluralsight-page-input", "value"),
        Output("pluralsight-prev-btn", "disabled"),
        Output("pluralsight-next-btn", "disabled"),
        Input("pluralsight-search-input", "value"),
        Input("pluralsight-instructor-input", "value"),
        Input("pluralsight-page-input", "value"),
        Input("pluralsight-prev-btn", "n_clicks"),
        Input("pluralsight-next-btn", "n_clicks"),
        prevent_initial_call=False,
    )
    def update_pluralsight_table(
        search_term, instructor_filter, current_page, prev_clicks, next_clicks
    ):
        try:
            if not COURSES_DATA_LOADED["pluralsight"]:
                return (
                    dbc.Alert("Loading Pluralsight data...", color="info"),
                    "",
                    "1",
                    1,
                    1,
                    True,
                    True,
                )

            df_filtered = ALL_COURSES_DATA["pluralsight"].copy()
            if df_filtered.empty:
                return (
                    dbc.Alert("No Pluralsight data available.", color="warning"),
                    "",
                    "1",
                    1,
                    1,
                    True,
                    True,
                )

            if search_term:
                search_lower = search_term.lower()
                df_filtered = df_filtered[
                    df_filtered["title"].str.lower().contains(search_lower, na=False)
                ]

            if instructor_filter:
                instructor_lower = instructor_filter.lower()
                df_filtered = df_filtered[
                    df_filtered["instructor"]
                    .str.lower()
                    .contains(instructor_lower, na=False)
                ]

            if df_filtered.empty:
                return (
                    dbc.Alert(
                        "No Pluralsight courses match your filters.", color="info"
                    ),
                    "",
                    "1",
                    1,
                    1,
                    True,
                    True,
                )

            total_items = len(df_filtered)
            max_pages = max(1, (total_items + PAGE_SIZE - 1) // PAGE_SIZE)

            # Handle pagination button clicks
            ctx = dash.callback_context
            if ctx.triggered:
                prop_id = ctx.triggered[0]["prop_id"]
                if "prev-btn" in prop_id:
                    current_page = max(1, (current_page or 1) - 1)
                elif "next-btn" in prop_id:
                    current_page = min(max_pages, (current_page or 1) + 1)

            current_page = max(1, min(current_page or 1, max_pages))

            start_idx = (current_page - 1) * PAGE_SIZE
            end_idx = start_idx + PAGE_SIZE
            df_paginated = df_filtered.iloc[start_idx:end_idx]

            # Create Pluralsight table
            table_header = [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Title"),
                            html.Th("Instructor"),
                            html.Th("Level"),
                            html.Th("Added Date"),
                        ]
                    )
                )
            ]
            table_body_rows = []
            for _, row in df_paginated.iterrows():
                table_body_rows.append(
                    html.Tr(
                        [
                            html.Td(
                                html.A(
                                    row.get("title", "N/A"),
                                    href=row.get("url"),
                                    target="_blank",
                                )
                            ),
                            html.Td(
                                str(row.get("instructor", "N/A"))
                                if row.get("instructor") != "false"
                                else "N/A"
                            ),
                            html.Td(row.get("level", "N/A")),
                            html.Td(
                                format_coursera_display_date(
                                    row.get("scraped_at_parsed")
                                )
                            ),  # Reusing date formatter
                        ]
                    )
                )
            table_body = [html.Tbody(table_body_rows)]
            table = dbc.Table(
                table_header + table_body,
                bordered=True,
                hover=True,
                responsive=True,
                striped=True,
                size="sm",
                color="dark",
                className="table-responsive",
            )

            # Create pagination info
            pagination_info = f"Showing {start_idx + 1}-{min(end_idx, total_items)} of {total_items} courses"

            # Button states
            prev_disabled = current_page <= 1
            next_disabled = current_page >= max_pages

            return (
                table,
                pagination_info,
                str(max_pages),
                max_pages,
                current_page,
                prev_disabled,
                next_disabled,
            )

        except Exception as e:
            print(f"Error in pluralsight table update: {e}")
            return (
                dbc.Alert(f"Error loading Pluralsight data: {str(e)}", color="danger"),
                "",
                "1",
                1,
                1,
                True,
                True,
            )

    @app.callback(
        Output("pluralsight-page-input", "value", allow_duplicate=True),
        Input("pluralsight-search-input", "value"),
        Input("pluralsight-instructor-input", "value"),
        prevent_initial_call=True,
    )
    def reset_pluralsight_pagination(_, __):
        return 1


def render_pluralsight_courses_sub_tab(df):
    if not COURSES_DATA_LOADED["pluralsight"]:
        return dbc.Alert(
            "Pluralsight courses data failed to load. Check logs.",
            color="danger",
            className="mt-3",
        )
    if df.empty:
        return dbc.Alert(
            "No Pluralsight courses data currently available (file might be empty).",
            color="info",
            className="mt-3",
        )

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Input(
                            id="pluralsight-search-input",
                            placeholder="Search by title...",
                        ),
                        md=8,
                        className="mb-2",
                    ),
                    dbc.Col(
                        dbc.Input(
                            id="pluralsight-instructor-input",
                            placeholder="Filter by instructor...",
                        ),
                        md=4,
                        className="mb-2",
                    ),
                ],
                className="mt-3 mb-3",
            ),
            html.Div(id="pluralsight-table-container"),
            # Custom pagination with better UX
            html.Div(
                id="pluralsight-pagination-wrapper",
                className="d-flex justify-content-between align-items-center mt-3",
                children=[
                    html.Div(id="pluralsight-pagination-info", className="text-muted"),
                    html.Div(
                        className="d-flex align-items-center gap-2",
                        children=[
                            dbc.Button(
                                "« Previous",
                                id="pluralsight-prev-btn",
                                size="sm",
                                outline=True,
                                color="primary",
                                disabled=True,
                            ),
                            dbc.Input(
                                id="pluralsight-page-input",
                                type="number",
                                value=1,
                                min=1,
                                max=1,
                                style={"width": "80px", "textAlign": "center"},
                                size="sm",
                            ),
                            html.Span("of", className="mx-2 text-muted"),
                            html.Span(
                                id="pluralsight-total-pages", className="text-muted"
                            ),
                            dbc.Button(
                                "Next »",
                                id="pluralsight-next-btn",
                                size="sm",
                                outline=True,
                                color="primary",
                                disabled=True,
                            ),
                        ],
                    ),
                ],
            ),
        ],
        className="mt-3",
    )


if __name__ == "__main__":
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_courses_tab(), fluid=True, className="py-4")
    register_courses_callbacks(app_test)  # Register callbacks
    print(
        f"Coursera data loaded: {COURSES_DATA_LOADED['coursera']}, Count: {len(ALL_COURSES_DATA['coursera'])}"
    )
    print(
        f"Udemy data loaded: {COURSES_DATA_LOADED['udemy']}, Count: {len(ALL_COURSES_DATA['udemy'])}"
    )
    app_test.run_server(debug=True, port=8059)
