import os
import time

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, dcc, html

# Import shared utilities
from src.services.data_loader import load_data_from_file
from src.web.dashboard.components.shared.table import paginate, render_items_table
from src.web.dashboard.utils import file_exists, get_data_path, parse_date_universal

# --- Constants ---
# Two registered ETLs scrape Class Central's Coursera provider page and write
# different output dirs (data/classcentral and data/coursera). Try both so the
# tab shows data regardless of which one ran last.
COURSERA_DATA_PATHS = [
    get_data_path("classcentral", "coursera_courses.json"),
    get_data_path("coursera", "coursera_courses.json"),
]
COURSERA_DATA_PATH = COURSERA_DATA_PATHS[0]
UDEMY_DATA_PATH = get_data_path("udemy", "udemy_courses.json")
MS_APPLIED_SKILLS_DATA_PATH = get_data_path("courses", "ms_applied_skills.json")
AWS_SKILL_BUILDER_DATA_PATH = get_data_path("courses", "aws_skill_builder.json")
GCP_SKILLS_BOOST_DATA_PATH = get_data_path("courses", "gcp_skills_boost.json")
FREECODECAMP_DATA_PATH = get_data_path("news", "freecodecamp_latest.json")
HF_LEARN_DATA_PATH = get_data_path("courses", "hf_learn.json")
DEEPLEARNING_AI_DATA_PATH = get_data_path("courses", "deeplearning_ai_latest.json")

ALL_COURSES_DATA = {
    "coursera": pd.DataFrame(),
    "udemy": pd.DataFrame(),
    "ms_skills": pd.DataFrame(),
    "aws_skills": pd.DataFrame(),
    "gcp_skills": pd.DataFrame(),
}
COURSES_DATA_LOADED = {
    "coursera": False,
    "udemy": False,
    "ms_skills": False,
    "aws_skills": False,
    "gcp_skills": False,
}
# Page size for tables
PAGE_SIZE = 15


# --- Data Loading Functions ---
def load_coursera_data():
    global ALL_COURSES_DATA, COURSES_DATA_LOADED
    file_path = next((p for p in COURSERA_DATA_PATHS if file_exists(p)), None)

    if file_path is None:
        print(f"Warning (Coursera): No data file found at any of: {COURSERA_DATA_PATHS}")
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

    df["start_date"] = df["start_date_str"].apply(lambda x: parse_date_universal(x, "Courses"))
    df["scraped_at"] = df["scraped_at_str"].apply(lambda x: parse_date_universal(x, "Courses"))  # This is likely the "added" date

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
        print(f"Warning (Udemy): File not found at {os.path.abspath(file_path)}")
        ALL_COURSES_DATA["udemy"] = pd.DataFrame()
        COURSES_DATA_LOADED["udemy"] = True
        return

    print(f"DEBUG (Udemy): Attempting to load from {file_path}")

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

    # Standardize columns: title, url, scraped_at, language, category, subcategory
    # Note: New ETL produces 'title', 'url', 'scraped_at', 'language', 'category', 'subcategory' directly.
    # We rename potential legacy columns just in case, but prioritize new ones.
    df.rename(
        columns={
            "course_title": "title",
            "course_url": "url",
            "created_at": "scraped_at_str",
        },
        inplace=True,
    )

    expected_cols = [
        "title",
        "url",
        "scraped_at",
        "language",
        "category",
        "subcategory",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    # Ensure scraped_at is datetime compatible (it should be ISO string from ETL)
    # If scraped_at is already correct, parse_date_universal handles it.
    df["scraped_at"] = df["scraped_at"].apply(lambda x: parse_date_universal(x, "Courses"))

    if "scraped_at" in df.columns:
        df = df.sort_values(by="scraped_at", ascending=False, na_position="last")

    # Fill N/A for display
    df["language"] = df["language"].fillna("Unknown")
    df["category"] = df["category"].fillna("Other")
    df["subcategory"] = df["subcategory"].fillna("Other")

    ALL_COURSES_DATA["udemy"] = df
    COURSES_DATA_LOADED["udemy"] = True
    print(f"Info (Udemy): Loaded {len(df)} courses.")


def load_ms_applied_skills_data():
    global ALL_COURSES_DATA, COURSES_DATA_LOADED
    file_path = MS_APPLIED_SKILLS_DATA_PATH
    if not file_exists(file_path):
        print(f"Warning (MS Skills): File not found at {file_path}")
        ALL_COURSES_DATA["ms_skills"] = pd.DataFrame()
        COURSES_DATA_LOADED["ms_skills"] = True
        return
    try:
        df = pd.read_json(file_path)
    except Exception as e:
        print(f"Error (MS Skills): Failed to load or parse {file_path}. Error: {e}")
        ALL_COURSES_DATA["ms_skills"] = pd.DataFrame()
        COURSES_DATA_LOADED["ms_skills"] = True
        return
    if df.empty:
        ALL_COURSES_DATA["ms_skills"] = pd.DataFrame()
        COURSES_DATA_LOADED["ms_skills"] = True
        return

    if "first_detected_at" in df.columns:
        df["first_detected_at"] = pd.to_datetime(df["first_detected_at"]).dt.tz_convert(None)
        df = df.sort_values(by="first_detected_at", ascending=False, na_position="last")
        df["detected_str"] = df["first_detected_at"].dt.strftime("%Y-%m-%d")
    else:
        df["detected_str"] = "N/A"

    df = df.fillna("N/A")
    ALL_COURSES_DATA["ms_skills"] = df
    COURSES_DATA_LOADED["ms_skills"] = True
    print(f"Info (MS Skills): Loaded {len(df)} items.")


def load_aws_skill_builder_data():
    global ALL_COURSES_DATA, COURSES_DATA_LOADED
    file_path = AWS_SKILL_BUILDER_DATA_PATH
    if not file_exists(file_path):
        print(f"Warning (AWS Skills): File not found at {file_path}")
        ALL_COURSES_DATA["aws_skills"] = pd.DataFrame()
        COURSES_DATA_LOADED["aws_skills"] = True
        return
    try:
        df = pd.read_json(file_path)
    except Exception as e:
        print(f"Error (AWS Skills): Failed to load or parse {file_path}. Error: {e}")
        ALL_COURSES_DATA["aws_skills"] = pd.DataFrame()
        COURSES_DATA_LOADED["aws_skills"] = True
        return
    if df.empty:
        ALL_COURSES_DATA["aws_skills"] = pd.DataFrame()
        COURSES_DATA_LOADED["aws_skills"] = True
        return

    if "first_detected_at" in df.columns:
        df["first_detected_at"] = pd.to_datetime(df["first_detected_at"]).dt.tz_convert(None)
        df = df.sort_values(by="first_detected_at", ascending=False, na_position="last")
        df["detected_str"] = df["first_detected_at"].dt.strftime("%Y-%m-%d")
    else:
        df["detected_str"] = "N/A"

    df = df.fillna("N/A")
    ALL_COURSES_DATA["aws_skills"] = df
    COURSES_DATA_LOADED["aws_skills"] = True
    print(f"Info (AWS Skills): Loaded {len(df)} items.")


def load_gcp_skills_boost_data():
    global ALL_COURSES_DATA, COURSES_DATA_LOADED
    file_path = GCP_SKILLS_BOOST_DATA_PATH
    if not file_exists(file_path):
        print(f"Warning (GCP Skills): File not found at {file_path}")
        ALL_COURSES_DATA["gcp_skills"] = pd.DataFrame()
        COURSES_DATA_LOADED["gcp_skills"] = True
        return
    try:
        df = pd.read_json(file_path)
    except Exception as e:
        print(f"Error (GCP Skills): Failed to load or parse {file_path}. Error: {e}")
        ALL_COURSES_DATA["gcp_skills"] = pd.DataFrame()
        COURSES_DATA_LOADED["gcp_skills"] = True
        return
    if df.empty:
        ALL_COURSES_DATA["gcp_skills"] = pd.DataFrame()
        COURSES_DATA_LOADED["gcp_skills"] = True
        return

    if "first_detected_at" in df.columns:
        df["first_detected_at"] = pd.to_datetime(df["first_detected_at"]).dt.tz_convert(None)
        df = df.sort_values(by="first_detected_at", ascending=False, na_position="last")
        df["detected_str"] = df["first_detected_at"].dt.strftime("%Y-%m-%d %H:%M")
    else:
        df["detected_str"] = "N/A"

    df = df.fillna("N/A")
    ALL_COURSES_DATA["gcp_skills"] = df
    COURSES_DATA_LOADED["gcp_skills"] = True
    print(f"Info (GCP Skills): Loaded {len(df)} items.")


def load_all_courses_data():
    global _COURSES_LOADED_AT
    # Allow a fresh reload when the previous one is older than the TTL
    for key in COURSES_DATA_LOADED:
        COURSES_DATA_LOADED[key] = False
    load_coursera_data()
    load_udemy_data()
    load_ms_applied_skills_data()
    load_aws_skill_builder_data()
    load_gcp_skills_boost_data()
    _COURSES_LOADED_AT = time.time()
    print("Attempted to load all courses data.")


_COURSES_LOADED_AT = 0.0
COURSES_DATA_TTL_SECONDS = 900  # Re-read the ETL files at most every 15 minutes


def ensure_courses_data(force_refresh: bool = False):
    """Reload course data when the in-memory copy is older than the TTL.

    The tab is lazily re-rendered on every visit (TAB_RENDERERS), so this
    makes new ETL output visible on the next tab switch without a restart.
    """
    if force_refresh or (time.time() - _COURSES_LOADED_AT) > COURSES_DATA_TTL_SECONDS:
        load_all_courses_data()


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
                ]
            )
        )
    ]

    table_body_rows = []
    for row in df_subset.to_dict("records"):
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


def get_initial_coursera_table():
    """Pre-render initial Coursera table data for layout."""
    if not COURSES_DATA_LOADED["coursera"] or ALL_COURSES_DATA["coursera"].empty:
        return dbc.Alert("Loading Coursera data...", color="info")

    df = ALL_COURSES_DATA["coursera"]
    df_paginated = df.head(PAGE_SIZE)
    return create_coursera_table(df_paginated)


def render_coursera_courses_sub_tab(df):
    print(f"DEBUG: render_coursera_courses_sub_tab called. DF Empty={df.empty}, Loaded={COURSES_DATA_LOADED['coursera']}")
    if not COURSES_DATA_LOADED["coursera"]:  # Check if loading was even attempted and successful
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
    subject_options = [{"label": i, "value": i} for i in df["subject"].dropna().unique().tolist() if i] if "subject" in df.columns else []
    language_options = [{"label": i, "value": i} for i in df["language"].dropna().unique().tolist() if i] if "language" in df.columns else []

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
                        dbc.Checkbox(id="coursera-free-checkbox", label="Only Free Courses"),
                        md=2,
                        className="mb-2 align-self-center",
                    ),
                ],
                className="mt-3 mb-3",
            ),
            html.Div(id="coursera-table-container", children=get_initial_coursera_table()),
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
                            html.Span(id="coursera-total-pages", className="text-muted"),
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
            dcc.Store(id="coursera-initial-load", data="trigger"),
        ],
        className="mt-3",
    )


def create_udemy_table(df_subset):
    """Create a table component for Udemy courses."""
    if df_subset.empty:
        return dbc.Alert("No Udemy courses match your criteria.", color="info")

    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Title", style={"width": "50%"}),
                    html.Th("Language"),
                    html.Th("Category"),
                    html.Th("Subcategory"),
                ]
            )
        )
    ]

    table_body_rows = []
    for row in df_subset.to_dict("records"):
        table_body_rows.append(
            html.Tr(
                [
                    html.Td(
                        html.A(
                            row.get("title", "N/A"),
                            href=row.get("url", "#"),
                            target="_blank",
                        )
                    ),
                    html.Td(row.get("language", "N/A")),
                    html.Td(row.get("category", "N/A")),
                    html.Td(row.get("subcategory", "N/A")),
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


def get_initial_udemy_table():
    """Pre-render initial Udemy table data for layout."""
    if not COURSES_DATA_LOADED["udemy"] or ALL_COURSES_DATA["udemy"].empty:
        return dbc.Alert("Loading Udemy data...", color="info")

    df = ALL_COURSES_DATA["udemy"]
    df_paginated = df.head(PAGE_SIZE)
    return create_udemy_table(df_paginated)


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

    # Prepare filter options
    language_options = [{"label": i, "value": i} for i in sorted(df["language"].unique().tolist()) if i] if "language" in df.columns else []
    category_options = [{"label": i, "value": i} for i in sorted(df["category"].unique().tolist()) if i] if "category" in df.columns else []

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Input(id="udemy-search-input", placeholder="Search by title..."),
                        md=4,
                        className="mb-2",
                    ),
                    dbc.Col(
                        dcc.Dropdown(
                            id="udemy-language-dropdown",
                            options=language_options,
                            placeholder="Filter by language",
                        ),
                        md=3,
                        className="mb-2",
                    ),
                    dbc.Col(
                        dcc.Dropdown(
                            id="udemy-category-dropdown",
                            options=category_options,
                            placeholder="Filter by category",
                        ),
                        md=3,
                        className="mb-2",
                    ),
                ],
                className="mt-3 mb-3",
            ),
            html.Div(id="udemy-table-container", children=get_initial_udemy_table()),
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


def render_ms_skills_courses_sub_tab(df):
    if not COURSES_DATA_LOADED["ms_skills"]:
        return dbc.Alert("MS Credentials data failed to load. Check logs.", color="danger", className="mt-3")
    if df.empty:
        return dbc.Alert("No MS Credentials data currently available.", color="info", className="mt-3")
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Input(id="ms-skills-search-input", placeholder="Search by title/subject/role..."),
                        md=12,
                        className="mb-2",
                    )
                ],
                className="mt-3 mb-3",
            ),
            html.Div(id="ms-skills-table-container"),
        ]
    )


def render_aws_skills_courses_sub_tab(df):
    if not COURSES_DATA_LOADED["aws_skills"]:
        return dbc.Alert("AWS Skill Builder data failed to load. Check logs.", color="danger", className="mt-3")
    if df.empty:
        return dbc.Alert("No AWS Skill Builder data currently available.", color="info", className="mt-3")
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Input(id="aws-skills-search-input", placeholder="Search by title..."),
                        md=12,
                        className="mb-2",
                    )
                ],
                className="mt-3 mb-3",
            ),
            html.Div(id="aws-skills-table-container"),
        ]
    )


def render_gcp_skills_courses_sub_tab(df):
    if not COURSES_DATA_LOADED["gcp_skills"]:
        return dbc.Alert("GCP Skills Boost data failed to load. Check logs.", color="danger", className="mt-3")
    if df.empty:
        return dbc.Alert("No GCP Skills Boost data currently available.", color="info", className="mt-3")
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Input(id="gcp-skills-search-input", placeholder="Search by title or description..."),
                        md=12,
                        className="mb-2",
                    )
                ],
                className="mt-3 mb-3",
            ),
            html.Div(id="gcp-skills-table-container"),
        ]
    )


def render_articles_sub_tab(data_path, source_label):
    """Render a list of articles/courses as cards (freeCodeCamp, HF Learn…)."""
    import json

    if not file_exists(data_path):
        return dbc.Alert(f"No {source_label} data available. Run the ETL to populate.", color="info", className="mt-3")

    try:
        with open(data_path, encoding="utf-8") as f:
            articles = json.load(f)
    except (OSError, ValueError):
        return dbc.Alert(f"Failed to load {source_label} data.", color="danger", className="mt-3")

    if not articles:
        return html.P(f"No {source_label} items found.", className="text-muted mt-3")

    cards = []
    for article in articles[:50]:
        title = article.get("title", "Untitled")
        link = article.get("link") or article.get("url") or "#"
        summary = article.get("summary") or article.get("description") or ""
        published = article.get("published") or article.get("published_at") or ""
        source_tag = article.get("source", "")
        cards.append(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H6(
                            html.A(title, href=link, target="_blank", className="text-decoration-none"),
                            className="mb-1",
                        ),
                        html.Small(f"{source_tag} · {published}" if published else source_tag, className="text-muted") if (source_tag or published) else None,
                        html.P(summary[:200] + "…" if len(summary) > 200 else summary, className="small text-muted mt-1 mb-0") if summary else None,
                    ]
                ),
                className="mb-2 shadow-sm",
            )
        )

    return html.Div(
        [
            html.P(f"{len(articles)} {source_label} items available.", className="text-muted small mb-3"),
            *cards,
        ]
    )


def render_freecodecamp_sub_tab():
    """Render freeCodeCamp articles as a learning resource list."""
    return render_articles_sub_tab(FREECODECAMP_DATA_PATH, "freeCodeCamp")


def render_hf_learn_sub_tab():
    """Render the Hugging Face Learn catalog."""
    return render_articles_sub_tab(HF_LEARN_DATA_PATH, "Hugging Face Learn")


def render_deeplearning_ai_sub_tab():
    """Render the DeepLearning.AI course catalog."""
    return render_articles_sub_tab(DEEPLEARNING_AI_DATA_PATH, "DeepLearning.AI")


# --- Main Layout ---
def _normalize_course(record: dict, provider: str) -> dict:
    """Normalize one course record across providers for the unified catalog."""
    title = record.get("title") or record.get("name") or record.get("course_title") or ""
    url = record.get("url") or record.get("link") or ""
    free_flag = record.get("is_free") or record.get("free") or (str(record.get("price", "")).lower() in ("free", "0", "0.0"))
    date_value = record.get("published") or record.get("date") or record.get("last_updated") or ""
    return {"title": str(title), "url": url, "provider": provider, "is_free": bool(free_flag), "date": str(date_value)}


def render_all_courses_sub_tab() -> html.Div:
    """Unified multi-provider catalog (spec 05 F1): search + provider badges."""
    ensure_courses_data()
    unified: list[dict] = []

    def _collect(key: str, provider: str):
        data = ALL_COURSES_DATA.get(key)
        if data is None:
            return
        records = data.to_dict("records") if hasattr(data, "to_dict") else (data if isinstance(data, list) else [])
        unified.extend(_normalize_course(r, provider) for r in records if isinstance(r, dict))

    _collect("coursera", "Coursera")
    _collect("udemy", "Udemy")
    _collect("ms_skills", "Microsoft")
    _collect("aws_skills", "AWS")
    _collect("gcp_skills", "Google Cloud")

    # HF Learn articles live in their own file
    try:
        hf_records = load_data_from_file(HF_LEARN_DATA_PATH) or []
        if isinstance(hf_records, list):
            unified.extend(_normalize_course(r, "HF Learn") for r in hf_records if isinstance(r, dict))
    except Exception:
        pass

    # DeepLearning.AI courses live in their own file
    try:
        dlai_records = load_data_from_file(DEEPLEARNING_AI_DATA_PATH) or []
        if isinstance(dlai_records, list):
            unified.extend(_normalize_course(r, "DeepLearning.AI") for r in dlai_records if isinstance(r, dict))
    except Exception:
        pass

    unified = [c for c in unified if c["title"]]
    store_data = unified[:2000]

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Input(id="courses-global-search", placeholder=f"🔎 Buscar en {len(unified)} cursos de todos los proveedores…", type="text", debounce=True),
                        width=True,
                    ),
                    dbc.Col(dbc.Checkbox(id="courses-free-only", label="Solo gratis"), width="auto", className="pt-2"),
                ],
                className="mb-3",
            ),
            html.Div(_unified_courses_table(unified), id="courses-global-results"),
            dcc.Store(id="courses-global-store", data=store_data),
        ]
    )


def _unified_courses_table(courses: list[dict]):
    """Render the unified catalog table (search filter applied upstream)."""
    if not courses:
        return dbc.Alert("Sin resultados.", color="info")
    columns = [
        {
            "header": "Title",
            "cell": lambda c: html.A(c["title"], href=c["url"] or "#", target="_blank", className="text-decoration-none") if c["url"] else c["title"],
        },
        {"header": "Provider", "cell": lambda c: dbc.Badge(c["provider"], color="secondary")},
        {"header": "Free", "cell": lambda c: "✅" if c["is_free"] else "—"},
        {"header": "Date", "cell": lambda c: c["date"][:10] if c["date"] else ""},
    ]
    return render_items_table(courses[:100], columns, empty_message="Sin resultados.", wrap_scroll=False)


def render_courses_tab():
    # Refresh data if the in-memory copy is stale (lazy tab re-render)
    ensure_courses_data()
    print(f"DEBUG: render_courses_tab called. Loaded status: {COURSES_DATA_LOADED}")
    # Initial check if any data was loaded to provide a general message
    # More specific messages are handled by individual sub-tab render functions
    if not any(COURSES_DATA_LOADED.values()):
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
                active_tab="tab-all-courses",
                children=[  # Unified catalog first (spec 05 F1)
                    dbc.Tab(
                        label="🔎 Todos",
                        tab_id="tab-all-courses",
                        children=render_all_courses_sub_tab(),
                    ),
                    dbc.Tab(
                        label="Coursera",
                        tab_id="tab-coursera",
                        children=render_coursera_courses_sub_tab(ALL_COURSES_DATA["coursera"]),
                    ),
                    dbc.Tab(
                        label="Udemy",
                        tab_id="tab-udemy",
                        children=render_udemy_courses_sub_tab(ALL_COURSES_DATA["udemy"]),
                    ),
                    dbc.Tab(
                        label="MS Credentials",
                        tab_id="tab-ms-skills",
                        children=render_ms_skills_courses_sub_tab(ALL_COURSES_DATA["ms_skills"]),
                    ),
                    dbc.Tab(
                        label="AWS Skill Builder",
                        tab_id="tab-aws-skills",
                        children=render_aws_skills_courses_sub_tab(ALL_COURSES_DATA["aws_skills"]),
                    ),
                    dbc.Tab(
                        label="GCP Skills Boost",
                        tab_id="tab-gcp-skills",
                        children=render_gcp_skills_courses_sub_tab(ALL_COURSES_DATA["gcp_skills"]),
                    ),
                    dbc.Tab(
                        label="📚 freeCodeCamp",
                        tab_id="tab-freecodecamp",
                        children=render_freecodecamp_sub_tab(),
                    ),
                    dbc.Tab(
                        label="🤗 HF Learn",
                        tab_id="tab-hf-learn",
                        children=render_hf_learn_sub_tab(),
                    ),
                    dbc.Tab(
                        label="🧠 DeepLearning.AI",
                        tab_id="tab-deeplearning-ai",
                        children=render_deeplearning_ai_sub_tab(),
                    ),
                ],
            ),
        ]
    )


# --- Callbacks ---
def register_courses_callbacks(app):
    print("DEBUG: register_courses_callbacks called")

    # Unified catalog search (spec 05 F1)
    @app.callback(
        Output("courses-global-results", "children"),
        [Input("courses-global-search", "value"), Input("courses-free-only", "checked")],
        State("courses-global-store", "data"),
        prevent_initial_call=True,
    )
    def search_unified_catalog(search_term, free_only, store_data):
        """Filter the combined catalog by term and free flag."""
        try:
            courses = store_data or []
            term = (search_term or "").strip().lower()
            if free_only:
                courses = [c for c in courses if c.get("is_free")]
            if term:
                courses = [c for c in courses if term in c.get("title", "").lower() or term in c.get("provider", "").lower()]
            header = dbc.Alert(f"🔎 {len(courses)} cursos" + (f" para '{search_term}'" if term else "") + (" · solo gratis" if free_only else ""), color="success", className="mb-2")
            return html.Div([header, _unified_courses_table(courses)])
        except Exception as e:
            return dbc.Alert(f"Error buscando cursos: {e}", color="danger")

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
        Input("coursera-free-checkbox", "value"),  # This is a list if checked, e.g. [True] or empty []
        Input("coursera-page-input", "value"),
        Input("coursera-prev-btn", "n_clicks"),
        Input("coursera-next-btn", "n_clicks"),
        Input("coursera-initial-load", "data"),
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
        dummy_trigger,
    ):
        print(f"DEBUG: update_coursera_table called. Trigger={dummy_trigger}, Search={search_term}, Subject={subject}, DataLoaded={COURSES_DATA_LOADED['coursera']}")
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
                df_filtered = df_filtered[df_filtered["title"].str.lower().contains(search_lower, na=False) | df_filtered["description"].fillna("").str.lower().contains(search_lower, na=False)]
            if subject:
                df_filtered = df_filtered[df_filtered["subject"] == subject]
            if language:
                df_filtered = df_filtered[df_filtered["language"] == language]
            if free_only_checked:  # Checkbox value is a list, [True] if checked, else None or empty list
                # is_free column should be boolean True/False after loading.
                # If it can be None/NaN, handle that: df_filtered['is_free'].fillna(False) == True
                df_filtered = df_filtered[df_filtered["is_free"]]

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

            # Handle pagination button clicks
            ctx = dash.callback_context
            if ctx.triggered:
                prop_id = ctx.triggered[0]["prop_id"]
                if "prev-btn" in prop_id:
                    current_page = (current_page or 1) - 1
                elif "next-btn" in prop_id:
                    current_page = (current_page or 1) + 1

            # Shared paginate() slices one page and clamps it into range
            # (DataFrames support the same len()/[a:b] protocol as lists).
            df_paginated, max_pages, current_page = paginate(df_filtered, current_page or 1, PAGE_SIZE)
            start_idx = (current_page - 1) * PAGE_SIZE
            end_idx = start_idx + PAGE_SIZE

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
                dbc.Alert(f"Error loading Coursera data: {e!s}", color="danger"),
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
        Input("udemy-language-dropdown", "value"),
        Input("udemy-category-dropdown", "value"),
        Input("udemy-page-input", "value"),
        Input("udemy-prev-btn", "n_clicks"),
        Input("udemy-next-btn", "n_clicks"),
        prevent_initial_call=False,
    )
    def update_udemy_table(search_term, language_filter, category_filter, current_page, prev_clicks, next_clicks):
        print(f"DEBUG: update_udemy_table called. Search={search_term}, Lang={language_filter}, DataLoaded={COURSES_DATA_LOADED['udemy']}")
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
                df_filtered = df_filtered[df_filtered["title"].str.lower().contains(search_lower, na=False)]

            if language_filter:
                df_filtered = df_filtered[df_filtered["language"] == language_filter]

            if category_filter:
                df_filtered = df_filtered[df_filtered["category"] == category_filter]

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

            # Handle pagination button clicks
            ctx = dash.callback_context
            if ctx.triggered:
                prop_id = ctx.triggered[0]["prop_id"]
                if "prev-btn" in prop_id:
                    current_page = (current_page or 1) - 1
                elif "next-btn" in prop_id:
                    current_page = (current_page or 1) + 1

            # Shared paginate() slices one page and clamps it into range
            # (DataFrames support the same len()/[a:b] protocol as lists).
            df_paginated, max_pages, current_page = paginate(df_filtered, current_page or 1, PAGE_SIZE)
            start_idx = (current_page - 1) * PAGE_SIZE
            end_idx = start_idx + PAGE_SIZE

            # Need a create_udemy_table helper
            table_header = [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Title"),
                            html.Th("Language"),
                            html.Th("Category"),
                            html.Th("Subcategory"),
                            html.Th("Date Added"),
                        ]
                    )
                )
            ]
            table_body_rows = []
            for row in df_paginated.to_dict("records"):
                # Format Date
                date_str = "N/A"
                if pd.notna(row.get("scraped_at")):
                    try:
                        date_str = row["scraped_at"].strftime("%Y-%m-%d")
                    except Exception:
                        date_str = str(row["scraped_at"])[:10]

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
                            html.Td(row.get("language", "N/A")),
                            html.Td(row.get("category", "N/A")),
                            html.Td(row.get("subcategory", "N/A")),
                            html.Td(date_str),
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
                dbc.Alert(f"Error loading Udemy data: {e!s}", color="danger"),
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

    @app.callback(
        Output("ms-skills-table-container", "children"),
        Input("ms-skills-search-input", "value"),
        prevent_initial_call=False,
    )
    def update_ms_skills_table(search_term):
        try:
            if not COURSES_DATA_LOADED["ms_skills"]:
                return dbc.Alert("Loading MS Credentials data...", color="info")
            df = ALL_COURSES_DATA["ms_skills"].copy()
            if df.empty:
                return dbc.Alert("No data available.", color="warning")
            if search_term:
                s = str(search_term).lower()
                df = df[df["title"].str.lower().str.contains(s, na=False) | df["subject"].str.lower().str.contains(s, na=False) | df["roles"].astype(str).str.lower().str.contains(s, na=False)]

            header = [html.Thead(html.Tr([html.Th("Title"), html.Th("Subject"), html.Th("Level"), html.Th("Roles"), html.Th("First Detected")]))]
            rows = []
            for row in df.to_dict("records"):
                roles_str = ", ".join(row.get("roles", [])) if isinstance(row.get("roles"), list) else "N/A"
                rows.append(
                    html.Tr(
                        [
                            html.Td(html.A(row.get("title", "N/A"), href=row.get("url"), target="_blank")),
                            html.Td(row.get("subject", "N/A")),
                            html.Td(row.get("level", "N/A")),
                            html.Td(roles_str),
                            html.Td(row.get("detected_str", "N/A")),
                        ]
                    )
                )
            return dbc.Table(
                header + [html.Tbody(rows)],
                bordered=True,
                hover=True,
                responsive=True,
                striped=True,
                size="sm",
                color="dark",
                className="table-responsive",
            )
        except Exception as e:
            return dbc.Alert(f"Error loading MS Applied Skills data: {e!s}", color="danger")

    @app.callback(
        Output("aws-skills-table-container", "children"),
        Input("aws-skills-search-input", "value"),
        prevent_initial_call=False,
    )
    def update_aws_skills_table(search_term):
        try:
            if not COURSES_DATA_LOADED["aws_skills"]:
                return dbc.Alert("Loading AWS Skill Builder data...", color="info")
            df = ALL_COURSES_DATA["aws_skills"].copy()
            if df.empty:
                return dbc.Alert("No data available.", color="warning")
            if search_term:
                s = str(search_term).lower()
                df = df[df["title"].str.lower().str.contains(s, na=False)]

            header = [html.Thead(html.Tr([html.Th("Title"), html.Th("Info"), html.Th("First Detected")]))]
            rows = []
            for row in df.to_dict("records"):
                rows.append(
                    html.Tr(
                        [
                            html.Td(html.A(row.get("title", "N/A"), href=row.get("url"), target="_blank")),
                            html.Td(row.get("description", "N/A")),
                            html.Td(row.get("detected_str", "N/A")),
                        ]
                    )
                )
            return dbc.Table(
                header + [html.Tbody(rows)],
                bordered=True,
                hover=True,
                responsive=True,
                striped=True,
                size="sm",
                color="dark",
                className="table-responsive",
            )
        except Exception as e:
            return dbc.Alert(f"Error loading AWS Skill Builder data: {e!s}", color="danger")

    @app.callback(
        Output("gcp-skills-table-container", "children"),
        Input("gcp-skills-search-input", "value"),
        prevent_initial_call=False,
    )
    def update_gcp_skills_table(search_term):
        try:
            if not COURSES_DATA_LOADED["gcp_skills"]:
                return dbc.Alert("Loading GCP Skills Boost data...", color="info")
            df = ALL_COURSES_DATA["gcp_skills"].copy()
            if df.empty:
                return dbc.Alert("No data available.", color="warning")
            if search_term:
                s = str(search_term).lower()
                df = df[df["title"].str.lower().str.contains(s, na=False) | df["description"].str.lower().str.contains(s, na=False)]

            header = [html.Thead(html.Tr([html.Th("Title"), html.Th("Type"), html.Th("Description"), html.Th("Duration"), html.Th("Level"), html.Th("First Detected")]))]
            rows = []
            for row in df.to_dict("records"):
                rows.append(
                    html.Tr(
                        [
                            html.Td(html.A(row.get("title", "N/A"), href=row.get("url", "#"), target="_blank")),
                            html.Td(row.get("course_type", "N/A")),
                            html.Td(row.get("description", "N/A")),
                            html.Td(row.get("duration", "N/A")),
                            html.Td(row.get("level", "N/A")),
                            html.Td(row.get("detected_str", "N/A")),
                        ]
                    )
                )
            return dbc.Table(
                header + [html.Tbody(rows)],
                bordered=True,
                hover=True,
                responsive=True,
                striped=True,
                size="sm",
                color="dark",
                className="table-responsive",
            )
        except Exception as e:
            return dbc.Alert(f"Error loading GCP Skills Boost data: {e!s}", color="danger")


if __name__ == "__main__":
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_courses_tab(), fluid=True, className="py-4")
    register_courses_callbacks(app_test)  # Register callbacks
    print(f"Coursera data loaded: {COURSES_DATA_LOADED['coursera']}, Count: {len(ALL_COURSES_DATA['coursera'])}")
    print(f"Udemy data loaded: {COURSES_DATA_LOADED['udemy']}, Count: {len(ALL_COURSES_DATA['udemy'])}")
    app_test.run_server(debug=True, port=8059)
