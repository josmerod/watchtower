"""The Learning tab: the unified catalog and one subtab per provider.

Every subtab is rendered as a shell (its controls, a pager and an empty table container), and its table is painted by
its own controller when the subtab is first opened (T-177). The layout used to carry the first page of every table,
so opening the tab cost seven requests and about 1.4 MiB. A dispatcher on the subtab bar's ``active_tab`` marks the
open subtab as activated; it runs in the browser, so a subtab click costs the one request of its controller, and a
subtab opened again keeps the table it has.
"""

import json
import logging
import os
import re
import time

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, dcc, html

from src.web.dashboard.components.shared.table import TABLE_SCROLL_STYLE, paginate, pagination_controls, render_items_table
from src.web.dashboard.utils import file_exists, get_data_path, parse_date_universal

logger = logging.getLogger(__name__)

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
# Page size for the Coursera and Udemy tables
PAGE_SIZE = 15
# Rows per page of the tables that are paginated by the shared Prev/Next bar:
# the unified catalog (T-159) and the two cloud catalogs. GCP Skills Boost
# holds 715 rows, which used to arrive in one 862 KiB answer.
UNIFIED_PAGE_SIZE = 100
CLOUD_PAGE_SIZE = 50
# The search of a subtab runs on the server, over the whole catalog: its box
# waits for a pause in typing instead of sending a request per keystroke.
SEARCH_DEBOUNCE_MS = 400

# Microsoft Learn catalog (`ms_applied_skills.json`): the ETL copies the credential
# `type` into `category`. The tab offers each kind as its own subtab (T-144).
MS_CERT_CATEGORY = "cert"
MS_CREDENTIAL_KINDS = {
    "certs": {
        "label": "MS Certificaciones",
        "tab_id": "tab-ms-certs",
        "search_id": "ms-certs-search-input",
        "table_id": "ms-certs-table-container",
        "unified_provider": "MS Certificación",
        "placeholder": "Buscar por título o rol...",
    },
    "applied": {
        "label": "MS Applied Skills",
        "tab_id": "tab-ms-applied",
        "search_id": "ms-applied-search-input",
        "table_id": "ms-applied-table-container",
        "unified_provider": "MS Applied Skill",
        "placeholder": "Buscar por título, tema o rol...",
    },
}
_MS_TITLE_PREFIXES = ("Microsoft Certified: ", "Microsoft Applied Skills: ")
_MS_ROLE_ACRONYMS = {"ai": "AI", "devops": "DevOps", "ip": "IP"}

# The subtab bar. Its active_tab is read by one dispatcher that marks the open
# subtab as activated; only that subtab's controller listens for it.
COURSES_TABS_ID = "courses-main-tabs"
ALL_COURSES_TAB_ID = "tab-all-courses"

# Every subtab of the bar, in order: its tab id and the prefix of its controls
# (pager, stores). The dispatcher writes an ``<prefix>-activate`` store per line.
COURSES_SUBTABS: list[tuple[str, str]] = [
    (ALL_COURSES_TAB_ID, "courses-global"),
    ("tab-coursera", "coursera"),
    ("tab-udemy", "udemy"),
    (MS_CREDENTIAL_KINDS["certs"]["tab_id"], MS_CREDENTIAL_KINDS["certs"]["search_id"]),
    (MS_CREDENTIAL_KINDS["applied"]["tab_id"], MS_CREDENTIAL_KINDS["applied"]["search_id"]),
    ("tab-aws-skills", "aws-skills"),
    ("tab-gcp-skills", "gcp-skills"),
]


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


def _sort_by_first_detected(df: pd.DataFrame, with_time: bool = False) -> pd.DataFrame:
    """Sort a catalog by FIRST DETECTED, newest first, and add the ``detected_str`` the tables show.

    The ETLs stamp ``first_detected_at`` in UTC. The hour is moved to Madrid before the zone is dropped (T-185):
    a course found at 13:20 CET used to read 12:20, and one found after 23:00 CET got the day before.

    Args:
        df: Catalog with, optionally, a ``first_detected_at`` column.
        with_time: GCP Skills Boost shows the hour too; the other two show the day.

    Returns:
        The sorted frame with ``detected_str`` added ("N/A" when there is no stamp to show).
    """
    if "first_detected_at" not in df.columns:
        df["detected_str"] = "N/A"
        return df
    detected = pd.to_datetime(df["first_detected_at"])
    if detected.dt.tz is None:  # a stamp without a zone was written as UTC too
        detected = detected.dt.tz_localize("UTC")
    df["first_detected_at"] = detected.dt.tz_convert("Europe/Madrid").dt.tz_localize(None)
    df = df.sort_values(by="first_detected_at", ascending=False, na_position="last")
    df["detected_str"] = df["first_detected_at"].dt.strftime("%Y-%m-%d %H:%M" if with_time else "%Y-%m-%d")
    return df


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

    df = _sort_by_first_detected(df)

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

    df = _sort_by_first_detected(df)

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

    df = _sort_by_first_detected(df, with_time=True)

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


def create_udemy_table(df_subset):
    """Create a table component for one page of Udemy courses."""
    if df_subset.empty:
        return dbc.Alert("No Udemy courses match your criteria.", color="info")

    table_header = [html.Thead(html.Tr([html.Th("Title"), html.Th("Language"), html.Th("Category"), html.Th("Subcategory"), html.Th("Date Added")]))]
    table_body_rows = []
    for row in df_subset.to_dict("records"):
        date_str = "N/A"
        if pd.notna(row.get("scraped_at")):
            try:
                date_str = row["scraped_at"].strftime("%Y-%m-%d")
            except Exception:
                date_str = str(row["scraped_at"])[:10]
        table_body_rows.append(
            html.Tr(
                [
                    html.Td(html.A(row.get("title", "N/A"), href=row.get("url") or "#", target="_blank")),
                    html.Td(row.get("language", "N/A")),
                    html.Td(row.get("category", "N/A")),
                    html.Td(row.get("subcategory", "N/A")),
                    html.Td(date_str),
                ]
            )
        )
    return dbc.Table(
        table_header + [html.Tbody(table_body_rows)],
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        size="sm",
        color="dark",
        className="table-responsive",
    )


def _loading() -> html.Div:
    """What a subtab shows where its table goes until its controller paints it."""
    return html.Div("Cargando…", className="text-muted small")


def _activate_store(prefix: str) -> dcc.Store:
    """Set to 1 by the dispatcher when the subtab is first opened; its controller starts with it."""
    return dcc.Store(id=f"{prefix}-activate", data=0)


def _inactive(message: dbc.Alert, shell: list) -> html.Div:
    """A subtab that has no table to build says why, and keeps its shell hidden.

    The renderer refuses a callback while one of its inputs or outputs is not
    in the page, and the dispatcher writes every subtab's activation store. So
    a subtab always carries its controls, its table container, its pager and
    its stores, here hidden: opened, its controller paints an empty state into
    the hidden container.
    """
    return html.Div([message, html.Div(shell, hidden=True)], className="mt-3")


def _numbered_pager(prefix: str) -> html.Div:
    """The pager of the Coursera and Udemy subtabs: previous/next and a box that jumps to a page."""
    return html.Div(
        [
            html.Div(id=f"{prefix}-pagination-info", className="text-muted"),
            html.Div(
                [
                    dbc.Button("« Previous", id=f"{prefix}-prev-btn", size="sm", outline=True, color="primary", disabled=True),
                    dbc.Input(id=f"{prefix}-page-input", type="number", value=1, min=1, max=1, style={"width": "80px", "textAlign": "center"}, size="sm"),
                    html.Span("of", className="mx-2 text-muted"),
                    html.Span(id=f"{prefix}-total-pages", className="text-muted"),
                    dbc.Button("Next »", id=f"{prefix}-next-btn", size="sm", outline=True, color="primary", disabled=True),
                ],
                className="d-flex align-items-center gap-2",
            ),
        ],
        id=f"{prefix}-pagination-wrapper",
        className="d-flex justify-content-between align-items-center mt-3",
    )


def _coursera_options(df):
    subject_options = [{"label": i, "value": i} for i in df["subject"].dropna().unique().tolist() if i] if "subject" in df.columns else []
    language_options = [{"label": i, "value": i} for i in df["language"].dropna().unique().tolist() if i] if "language" in df.columns else []
    return subject_options, language_options


def _coursera_shell(df) -> list:
    """The controls, the empty table container, the pager and the stores of the Coursera subtab."""
    subject_options, language_options = _coursera_options(df)
    return [
        dbc.Row(
            [
                dbc.Col(dbc.Input(id="coursera-search-input", placeholder="Search by title/description...", debounce=SEARCH_DEBOUNCE_MS), md=4, className="mb-2"),
                dbc.Col(dcc.Dropdown(id="coursera-subject-dropdown", options=subject_options, placeholder="Filter by subject"), md=3, className="mb-2"),
                dbc.Col(dcc.Dropdown(id="coursera-language-dropdown", options=language_options, placeholder="Filter by language"), md=3, className="mb-2"),
                dbc.Col(dbc.Checkbox(id="coursera-free-checkbox", label="Only Free Courses"), md=2, className="mb-2 align-self-center"),
            ],
            className="mt-3 mb-3",
        ),
        html.Div(id="coursera-table-container", children=_loading()),
        _numbered_pager("coursera"),
        dcc.Store(id="coursera-page"),
        _activate_store("coursera"),
    ]


def render_coursera_courses_sub_tab(df):
    """The Coursera subtab: its filters and pager, and an empty table container its controller fills."""
    shell = _coursera_shell(df)
    if not COURSES_DATA_LOADED["coursera"]:
        return _inactive(dbc.Alert("Coursera courses data failed to load. Check logs.", color="danger"), shell)
    if df.empty:
        return _inactive(dbc.Alert("No Coursera courses data currently available (file might be empty or all data filtered out).", color="info"), shell)
    return html.Div(shell, className="mt-3")


def _udemy_shell(df) -> list:
    """The controls, the empty table container, the pager and the stores of the Udemy subtab."""
    language_options = [{"label": i, "value": i} for i in sorted(df["language"].unique().tolist()) if i] if "language" in df.columns else []
    category_options = [{"label": i, "value": i} for i in sorted(df["category"].unique().tolist()) if i] if "category" in df.columns else []
    return [
        dbc.Row(
            [
                dbc.Col(dbc.Input(id="udemy-search-input", placeholder="Search by title...", debounce=SEARCH_DEBOUNCE_MS), md=4, className="mb-2"),
                dbc.Col(dcc.Dropdown(id="udemy-language-dropdown", options=language_options, placeholder="Filter by language"), md=3, className="mb-2"),
                dbc.Col(dcc.Dropdown(id="udemy-category-dropdown", options=category_options, placeholder="Filter by category"), md=3, className="mb-2"),
            ],
            className="mt-3 mb-3",
        ),
        html.Div(id="udemy-table-container", children=_loading()),
        _numbered_pager("udemy"),
        dcc.Store(id="udemy-page"),
        _activate_store("udemy"),
    ]


def render_udemy_courses_sub_tab(df):
    """The Udemy subtab: its filters and pager, and an empty table container its controller fills."""
    shell = _udemy_shell(df)
    if not COURSES_DATA_LOADED["udemy"]:
        return _inactive(dbc.Alert("Udemy courses data failed to load. Check logs.", color="danger"), shell)
    if df.empty:
        return _inactive(dbc.Alert("No Udemy courses data currently available (file might be empty).", color="info"), shell)
    return html.Div(shell, className="mt-3")


def split_ms_credentials(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split the Microsoft Learn catalog into (certifications, applied skills).

    A credential that carries no kind is not dropped: it stays with the applied
    skills, which is the ETL's own fallback for it.
    """
    if df.empty or "category" not in df.columns:
        return df.iloc[0:0], df
    is_cert = df["category"].astype(str).str.lower() == MS_CERT_CATEGORY
    return df[is_cert], df[~is_cert]


def _search_ms_credentials(df: pd.DataFrame, search_term) -> pd.DataFrame:
    """Keep the rows whose full title, subject or roles contain `search_term` (case-insensitive)."""
    if not search_term:
        return df

    def column(name: str) -> pd.Series:
        if name not in df.columns:
            return pd.Series("", index=df.index)
        return df[name].astype(str).str.lower()

    needle = str(search_term).lower()
    title, subject, roles = column("title"), column("subject"), column("roles")
    return df[title.str.contains(needle, na=False) | subject.str.contains(needle, na=False) | roles.str.contains(needle, na=False)]


def _ms_role_label(role_id: str) -> str:
    """Turn a catalog role id into a label ("ai-edge-engineer" -> "AI Edge Engineer")."""
    return " ".join(_MS_ROLE_ACRONYMS.get(word, word.capitalize()) for word in str(role_id).split("-"))


def retired_mask(df: pd.DataFrame) -> pd.Series:
    """Which credentials of a Microsoft Learn catalog are retired.

    The ETL marks every record with ``retired``. A file written before it did has
    no such column, and there nothing is retired.
    """
    if df.empty or "retired" not in df.columns:
        return pd.Series(False, index=df.index)
    # The loader fills what is missing with "N/A": only a true flag counts.
    return df["retired"].map(lambda value: value is True or str(value).strip().lower() in ("true", "1"))


def _credentials_in_view(df: pd.DataFrame, show_retired: bool) -> pd.DataFrame:
    """The credentials a Microsoft subtab lists: the current ones, then the retired ones when asked for."""
    retired = retired_mask(df)
    return pd.concat([df[~retired], df[retired]]) if show_retired else df[~retired]


def _retirement_cell(row: dict) -> str:
    """What the Retirada column says: the date when the catalog gave one."""
    date = str(row.get("retirement_date") or "")
    return date if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) else "Sí"


def _ms_credentials_table(df: pd.DataFrame, kind: str, with_retired: bool = False) -> dbc.Table:
    """Render one kind of Microsoft credential.

    Certifications carry no subject, so that column is only shown for applied
    skills; the kind prefix of a title is dropped because it repeats the subtab
    label on every row. With ``with_retired`` the retired credentials of ``df``
    (listed last) are marked, with the date they were retired on.
    """
    columns = ["Title", "Subject", "Level", "Roles", "First Detected"] if kind == "applied" else ["Title", "Level", "Roles", "First Detected"]
    if with_retired:
        columns.append("Retirada")
    header = [html.Thead(html.Tr([html.Th(name) for name in columns]))]
    retired_rows = retired_mask(df) if with_retired else [False] * len(df)
    rows = []
    for row, retired in zip(df.to_dict("records"), retired_rows, strict=True):
        roles = row.get("roles")
        title = str(row.get("title", "N/A"))
        for prefix in _MS_TITLE_PREFIXES:
            if title.startswith(prefix):
                title = title[len(prefix) :]
                break
        cells = [
            html.Td(html.A(title, href=row.get("url") or "#", target="_blank")),
            *([html.Td(row.get("subject", "N/A"))] if kind == "applied" else []),
            html.Td(row.get("level", "N/A")),
            # A row without roles holds "N/A" after fillna().
            html.Td(", ".join(_ms_role_label(role) for role in roles) if isinstance(roles, list) else "N/A"),
            html.Td(row.get("detected_str", "N/A")),
        ]
        if with_retired:
            cells.append(html.Td(_retirement_cell(row)))
        rows.append(html.Tr(cells, className="text-muted" if with_retired and retired else None))
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


def _ms_credentials_shell(kind: str, df: pd.DataFrame) -> list:
    """The search box, the retired toggle, the empty table container and the store of one Microsoft subtab."""
    spec = MS_CREDENTIAL_KINDS[kind]
    prefix = spec["search_id"]
    # Retired credentials are hidden until they are asked for. The toggle is
    # always in the page, only hidden when there is nothing to show: a callback
    # does not run while one of its inputs is missing from the page.
    retired = int(retired_mask(df).sum())
    toggle = dbc.Checkbox(id=f"{prefix}-retired", label=f"Mostrar retiradas ({retired})", value=False)
    return [
        dbc.Row(
            [
                dbc.Col(dbc.Input(id=spec["search_id"], placeholder=spec["placeholder"], debounce=SEARCH_DEBOUNCE_MS), width=True, className="mb-2"),
                dbc.Col(html.Div(toggle, style={} if retired else {"display": "none"}), width="auto", className="pt-2"),
            ],
            className="mt-3 mb-3",
        ),
        html.Div(id=spec["table_id"], children=_loading()),
        _activate_store(prefix),
    ]


def render_ms_credentials_sub_tab(kind: str, df: pd.DataFrame):
    """One Microsoft subtab: its search box, the retired toggle and an empty table container its controller fills."""
    spec = MS_CREDENTIAL_KINDS[kind]
    shell = _ms_credentials_shell(kind, df)
    if not COURSES_DATA_LOADED["ms_skills"]:
        return _inactive(dbc.Alert(f"{spec['label']} data failed to load. Check logs.", color="danger"), shell)
    if df.empty:
        return _inactive(dbc.Alert(f"No {spec['label']} data currently available.", color="info"), shell)
    return html.Div(shell)


def render_ms_credentials_tabs() -> list[dbc.Tab]:
    """Return the two Microsoft Learn subtabs: certifications and applied skills."""
    certs, applied = split_ms_credentials(ALL_COURSES_DATA["ms_skills"])
    return [
        dbc.Tab(
            label=MS_CREDENTIAL_KINDS["certs"]["label"],
            tab_id=MS_CREDENTIAL_KINDS["certs"]["tab_id"],
            children=render_ms_credentials_sub_tab("certs", certs),
        ),
        dbc.Tab(
            label=MS_CREDENTIAL_KINDS["applied"]["label"],
            tab_id=MS_CREDENTIAL_KINDS["applied"]["tab_id"],
            children=render_ms_credentials_sub_tab("applied", applied),
        ),
    ]


LANGUAGE_LABELS = {"es": "Español", "en": "English", "en+es": "English + Spanish"}


def language_options(df):
    """Dropdown options for the languages a catalog carries, in the order of LANGUAGE_LABELS."""
    if "language" not in df.columns:
        return []
    present = set(df["language"].dropna().unique())
    return [{"label": label, "value": code} for code, label in LANGUAGE_LABELS.items() if code in present]


def filter_by_language(df, language):
    """Keep the rows of a catalog in `language`; nothing is filtered when no language is chosen."""
    if not language or "language" not in df.columns:
        return df
    return df[df["language"] == language]


def _language_dropdown(dropdown_id, df):
    return dcc.Dropdown(id=dropdown_id, options=language_options(df), placeholder="Filter by language", clearable=True)


def _aws_skills_table(df):
    """The AWS Skill Builder table for the rows left in `df`."""
    header = [html.Thead(html.Tr([html.Th("Title"), html.Th("Info"), html.Th("First Detected")]))]
    rows = [
        html.Tr([html.Td(html.A(row.get("title", "N/A"), href=row.get("url"), target="_blank")), html.Td(row.get("description", "N/A")), html.Td(row.get("detected_str", "N/A"))])
        for row in df.to_dict("records")
    ]
    return dbc.Table(header + [html.Tbody(rows)], bordered=True, hover=True, responsive=True, striped=True, size="sm", color="dark", className="table-responsive")


def _gcp_skills_table(df):
    """The GCP Skills Boost table for the rows left in `df`."""
    header = [html.Thead(html.Tr([html.Th("Title"), html.Th("Type"), html.Th("Description"), html.Th("Duration"), html.Th("Level"), html.Th("First Detected")]))]
    rows = [
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
        for row in df.to_dict("records")
    ]
    return dbc.Table(header + [html.Tbody(rows)], bordered=True, hover=True, responsive=True, striped=True, size="sm", color="dark", className="table-responsive")


def _cloud_sub_tab(prefix: str, search_placeholder: str, dropdown_id: str, df, loaded: bool = True, label: str = "") -> html.Div:
    """A cloud catalog subtab (AWS Skill Builder, GCP Skills Boost): search, language filter, pager and an empty table container.

    Without data to list, the same shell stays under a message that says why,
    hidden: the renderer refuses the subtab's controller while one of its ids
    is missing from the page.
    """
    shell = [
        dbc.Row(
            [
                dbc.Col(dbc.Input(id=f"{prefix}-search-input", placeholder=search_placeholder, debounce=SEARCH_DEBOUNCE_MS), md=8, className="mb-2"),
                dbc.Col(_language_dropdown(dropdown_id, df), md=4, className="mb-2"),
            ],
            className="mt-3 mb-3",
        ),
        pagination_controls(prefix, page=0, total_pages=0, showing=0, total=0, id_prefix=prefix, info_id=f"{prefix}-page-info", label="Cargando…"),
        html.Div(id=f"{prefix}-table-container", children=_loading(), style=TABLE_SCROLL_STYLE),
        dcc.Store(id=f"{prefix}-page"),
        _activate_store(prefix),
    ]
    if not loaded:
        return _inactive(dbc.Alert(f"{label} data failed to load. Check logs.", color="danger"), shell)
    if df.empty:
        return _inactive(dbc.Alert(f"No {label} data currently available.", color="info"), shell)
    return html.Div(shell)


def render_aws_skills_courses_sub_tab(df):
    return _cloud_sub_tab("aws-skills", "Search by title...", "aws-skills-language-dropdown", df, COURSES_DATA_LOADED["aws_skills"], "AWS Skill Builder")


def render_gcp_skills_courses_sub_tab(df):
    return _cloud_sub_tab("gcp-skills", "Search by title or description...", "gcp-skills-language-dropdown", df, COURSES_DATA_LOADED["gcp_skills"], "GCP Skills Boost")


def _cloud_view(frame: pd.DataFrame, search_term, language, page: int, table, empty_message: str, search_description: bool = False) -> dict:
    """One page of a cloud catalog after its search box and language filter: the rows and what its pager says."""
    df = frame
    if search_term:
        needle = str(search_term).lower()
        title = df["title"].astype(str).str.lower().str.contains(needle, na=False)
        description = df["description"].astype(str).str.lower().str.contains(needle, na=False) if search_description and "description" in df.columns else pd.Series(False, index=df.index)
        df = df[title | description]
    df = filter_by_language(df, language)
    return _frame_view(df, page, table, CLOUD_PAGE_SIZE, empty_message)


def _frame_view(frame: pd.DataFrame | list[dict], page: int, table, page_size: int, empty_message: str) -> dict:
    """One page of a filtered catalog: its table and what its pager says about it.

    ``frame`` is a DataFrame (the cloud catalogs) or a list of dicts (the unified catalog). The rows are cut by
    position, so each keeps its type for its table builder.
    """
    positions, total_pages, page = paginate(list(range(len(frame))), int(page or 1), page_size)
    if not len(frame):
        return {"content": dbc.Alert(empty_message, color="info"), "page": 1, "first": 0, "last": 0, "showing": 0, "total": 0, "total_pages": 0}
    view = frame.iloc[positions] if isinstance(frame, pd.DataFrame) else [frame[i] for i in positions]
    first = (page - 1) * page_size + 1
    return {"content": table(view), "page": page, "first": first, "last": first + len(positions) - 1, "showing": len(positions), "total": len(frame), "total_pages": total_pages}


def _page_info(built: dict, spanish: bool = False) -> str:
    """The line of the shared pager: which rows are shown of how many, and which page of how many."""
    if not built["total"]:
        return "Sin cursos." if spanish else "No courses."
    if spanish:
        return f"{built['first']}–{built['last']} de {built['total']} · Página {built['page']} de {built['total_pages']}"
    return f"Showing {built['first']}–{built['last']} of {built['total']} · Page {built['page']} of {built['total_pages']}"


# --- Unified catalog ---
def _normalize_course(record: dict, provider: str) -> dict:
    """Normalize one course record across providers for the unified catalog."""
    title = record.get("title") or record.get("name") or record.get("course_title") or ""
    url = record.get("url") or record.get("link") or ""
    free_flag = record.get("is_free") or record.get("free") or (str(record.get("price", "")).lower() in ("free", "0", "0.0"))
    date_value = record.get("published") or record.get("date") or record.get("last_updated") or ""
    return {"title": str(title), "url": url, "provider": provider, "is_free": bool(free_flag), "date": str(date_value)}


def unified_catalog() -> list[dict]:
    """Every current course of every provider, provider by provider, shaped for the unified table.

    A retired Microsoft credential is not a course to take, so it stays out, as
    it does out of its own subtab until the user asks for the retired ones.
    """
    unified: list[dict] = []

    def _collect(data, provider: str):
        if data is None:
            return
        records = data.to_dict("records") if hasattr(data, "to_dict") else (data if isinstance(data, list) else [])
        unified.extend(_normalize_course(r, provider) for r in records if isinstance(r, dict))

    _collect(ALL_COURSES_DATA.get("coursera"), "Coursera")
    _collect(ALL_COURSES_DATA.get("udemy"), "Udemy")
    ms_certs, ms_applied = split_ms_credentials(ALL_COURSES_DATA.get("ms_skills", pd.DataFrame()))
    _collect(_credentials_in_view(ms_certs, False), MS_CREDENTIAL_KINDS["certs"]["unified_provider"])
    _collect(_credentials_in_view(ms_applied, False), MS_CREDENTIAL_KINDS["applied"]["unified_provider"])
    _collect(ALL_COURSES_DATA.get("aws_skills"), "AWS")
    _collect(ALL_COURSES_DATA.get("gcp_skills"), "Google Cloud")

    return [c for c in unified if c["title"]]


def _filter_unified(courses: list[dict], search_term, free_only: bool) -> list[dict]:
    """Keep the unified rows whose title or provider contains the term, and the free ones when only those are asked for."""
    term = (search_term or "").strip().lower()
    if free_only:
        courses = [c for c in courses if c.get("is_free")]
    if term:
        courses = [c for c in courses if term in c.get("title", "").lower() or term in c.get("provider", "").lower()]
    return courses


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
    return render_items_table(courses, columns, empty_message="Sin resultados.", wrap_scroll=False)


def _unified_view(search_term, free_only: bool, page: int) -> dict:
    """One page of the unified catalog after its search box and free-only box.

    The search runs over the whole catalog on the server. The rows used to be
    shipped to the browser in a store, cut to the first 2000 of about 4900, and
    the table to its first 100 (T-159).
    """
    courses = _filter_unified(unified_catalog(), search_term, free_only)
    term = (search_term or "").strip()
    header = dbc.Alert(f"🔎 {len(courses)} cursos" + (f" para '{term}'" if term else "") + (" · solo gratis" if free_only else ""), color="success", className="mb-2")
    built = _frame_view(courses, page, _unified_courses_table, UNIFIED_PAGE_SIZE, "Sin resultados.")
    return {**built, "content": html.Div([header, built["content"]])}


def render_all_courses_sub_tab() -> html.Div:
    """The unified catalog (spec 05 F1): search, free-only box, pager and an empty results container."""
    total = len(unified_catalog())
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(dbc.Input(id="courses-global-search", placeholder=f"🔎 Buscar en {total} cursos de todos los proveedores…", type="text", debounce=SEARCH_DEBOUNCE_MS), width=True),
                    dbc.Col(dbc.Checkbox(id="courses-free-only", label="Solo gratis"), width="auto", className="pt-2"),
                ],
                className="mb-3",
            ),
            pagination_controls("courses", page=0, total_pages=0, showing=0, total=0, id_prefix="courses-global", info_id="courses-global-page-info", label="Cargando…"),
            html.Div(_loading(), id="courses-global-results", style={"maxHeight": "860px", "overflowY": "auto", "paddingRight": "15px"}),
            dcc.Store(id="courses-global-page"),
            _activate_store("courses-global"),
        ]
    )


# --- Main Layout ---
def render_courses_tab():
    # Refresh data if the in-memory copy is stale (lazy tab re-render)
    ensure_courses_data()

    # When nothing loaded, each subtab says so on its own; this message is for
    # when there is not a single table to build.
    if not any(COURSES_DATA_LOADED.values()):
        return dbc.Alert(
            "All course data failed to load. Please check data sources and ETLs.",
            color="danger",
            className="mt-3",
        )

    return html.Div(
        [
            html.H3("Cursos Online", className="mb-3"),
            dbc.Tabs(
                id=COURSES_TABS_ID,
                active_tab=ALL_COURSES_TAB_ID,
                children=[
                    dbc.Tab(label="🔎 Todos", tab_id=ALL_COURSES_TAB_ID, children=render_all_courses_sub_tab()),
                    dbc.Tab(label="Coursera", tab_id="tab-coursera", children=render_coursera_courses_sub_tab(ALL_COURSES_DATA["coursera"])),
                    dbc.Tab(label="Udemy", tab_id="tab-udemy", children=render_udemy_courses_sub_tab(ALL_COURSES_DATA["udemy"])),
                    *render_ms_credentials_tabs(),
                    dbc.Tab(label="AWS Skill Builder", tab_id="tab-aws-skills", children=render_aws_skills_courses_sub_tab(ALL_COURSES_DATA["aws_skills"])),
                    dbc.Tab(label="GCP Skills Boost", tab_id="tab-gcp-skills", children=render_gcp_skills_courses_sub_tab(ALL_COURSES_DATA["gcp_skills"])),
                ],
            ),
        ]
    )


# --- Callbacks ---
def _page_plan(triggered_id, activated, current_page, prefix: str, filters: tuple[str, ...], typed_page=None) -> int | None:
    """The page a subtab's controller builds next, or None when it has nothing to do.

    A subtab's table is built lazily, when the dispatcher first marks it as
    activated: until then its page store is empty and the controller stays
    idle. Afterwards only its own controls act. Opening another subtab does not
    reach this controller, and coming back leaves the table as it was.

    Args:
        triggered_id: The ``id`` of the control that set the controller going.
        activated: 1 once the subtab has been opened.
        current_page: The page the subtab is on (its page store), empty before the first build.
        prefix: Id prefix of the subtab's pager (``<prefix>-prev``, ``<prefix>-next``, ``<prefix>-page-input``).
        filters: Ids of the controls that restart from the first page.
        typed_page: What a subtab with a page box shows, when that box is the trigger.
    """
    if not current_page:
        return 1 if activated else None
    page = int(current_page)
    if triggered_id in (f"{prefix}-prev", f"{prefix}-prev-btn"):
        return page - 1
    if triggered_id in (f"{prefix}-next", f"{prefix}-next-btn"):
        return page + 1
    if triggered_id == f"{prefix}-page-input":
        try:
            return int(typed_page)
        except (TypeError, ValueError):
            return None
    if triggered_id in filters:
        return 1  # a new search or filter restarts from the first page
    return None


def _filter_coursera(df: pd.DataFrame, search_term, subject, language, free_only) -> pd.DataFrame:
    """The Coursera rows that pass the subtab's search box, its two dropdowns and its free-only box."""
    if search_term:
        needle = str(search_term).lower()
        title = df["title"].astype(str).str.lower().str.contains(needle, na=False)
        description = df["description"].fillna("").astype(str).str.lower().str.contains(needle, na=False) if "description" in df.columns else pd.Series(False, index=df.index)
        df = df[title | description]
    if subject:
        df = df[df["subject"] == subject]
    if language:
        df = df[df["language"] == language]
    if free_only:
        free = df["is_free"].fillna(False).astype(bool) if "is_free" in df.columns else pd.Series(False, index=df.index)
        df = df[free]
    return df


def _filter_udemy(df: pd.DataFrame, search_term, language, category) -> pd.DataFrame:
    """The Udemy rows that pass the subtab's search box and its two dropdowns."""
    if search_term:
        df = df[df["title"].astype(str).str.lower().str.contains(str(search_term).lower(), na=False)]
    if language:
        df = df[df["language"] == language]
    if category:
        df = df[df["category"] == category]
    return df


def _coursera_view(search_term, subject, language, free_only, page: int) -> dict:
    return _frame_view(_filter_coursera(ALL_COURSES_DATA["coursera"], search_term, subject, language, free_only), page, create_coursera_table, PAGE_SIZE, "No Coursera courses match your filters.")


def _udemy_view(search_term, language, category, page: int) -> dict:
    return _frame_view(_filter_udemy(ALL_COURSES_DATA["udemy"], search_term, language, category), page, create_udemy_table, PAGE_SIZE, "No Udemy courses match your filters.")


def _unified_page(search_term, free_only: bool, page: int) -> dict:
    return _unified_view(search_term, free_only, page)


def _aws_page(search_term, language, page: int) -> dict:
    return _cloud_view(ALL_COURSES_DATA["aws_skills"], search_term, language, page, _aws_skills_table, "No AWS Skill Builder course matches.")


def _gcp_page(search_term, language, page: int) -> dict:
    return _cloud_view(ALL_COURSES_DATA["gcp_skills"], search_term, language, page, _gcp_skills_table, "No GCP Skills Boost course matches.", search_description=True)


def _register_pager_controller(app, prefix: str, results_id: str, filters: list[tuple[str, str]], build, label: str, spanish: bool = False) -> None:
    """One controller for a subtab with the shared Prev/Next bar: the unified catalog, AWS Skill Builder and GCP Skills Boost."""
    idle = (dash.no_update,) * 5

    @app.callback(
        [
            Output(results_id, "children"),
            Output(f"{prefix}-page", "data"),
            Output(f"{prefix}-page-info", "children"),
            Output(f"{prefix}-prev", "disabled"),
            Output(f"{prefix}-next", "disabled"),
        ],
        [Input(filter_id, prop) for filter_id, prop in filters] + [Input(f"{prefix}-prev", "n_clicks"), Input(f"{prefix}-next", "n_clicks"), Input(f"{prefix}-activate", "data")],
        State(f"{prefix}-page", "data"),
        # Idle on insertion: the table is built when the dispatcher writes the
        # activate store, not when the subtab bar appears.
        prevent_initial_call=True,
    )
    def update_table(*args, prefix=prefix, filters=tuple(filter_id for filter_id, _ in filters), build=build, label=label, spanish=spanish, idle=idle):
        *values, _prev, _next, activated, current_page = args
        try:
            page = _page_plan(dash.ctx.triggered_id, activated, current_page, prefix, filters)
            if page is None:
                return idle
            built = build(*values, page)
            return built["content"], built["page"], _page_info(built, spanish), built["page"] <= 1, built["page"] >= built["total_pages"]
        except Exception as e:
            logger.error(f"Error in the {prefix} table: {e}")
            return dbc.Alert(f"Error loading {label} data: {e!s}", color="danger"), 1, "", True, True


def _register_numbered_pager_controller(app, prefix: str, filters: list[tuple[str, str]], build, label: str) -> None:
    """One controller for the Coursera or the Udemy subtab, whose pager also has a box that jumps to a page."""
    idle = (dash.no_update,) * 8
    inputs = [Input(filter_id, prop) for filter_id, prop in filters]
    inputs += [Input(f"{prefix}-page-input", "value"), Input(f"{prefix}-prev-btn", "n_clicks"), Input(f"{prefix}-next-btn", "n_clicks"), Input(f"{prefix}-activate", "data")]

    @app.callback(
        [
            Output(f"{prefix}-table-container", "children"),
            Output(f"{prefix}-page", "data"),
            Output(f"{prefix}-pagination-info", "children"),
            Output(f"{prefix}-total-pages", "children"),
            Output(f"{prefix}-page-input", "max"),
            Output(f"{prefix}-page-input", "value"),
            Output(f"{prefix}-prev-btn", "disabled"),
            Output(f"{prefix}-next-btn", "disabled"),
        ],
        inputs,
        State(f"{prefix}-page", "data"),
        prevent_initial_call=True,
    )
    def update_table(*args, prefix=prefix, filters=tuple(filter_id for filter_id, _ in filters), build=build, label=label, idle=idle):
        *values, typed_page, _prev, _next, activated, current_page = args
        try:
            page = _page_plan(dash.ctx.triggered_id, activated, current_page, prefix, filters, typed_page)
            if page is None:
                return idle
            built = build(*values, page)
            showing = f"Showing {built['first']}-{built['last']} of {built['total']} courses" if built["total"] else ""
            # The box is rewritten only when it shows another page than the one
            # built: rewriting the page just typed would run this controller twice.
            shown = dash.no_update if str(typed_page) == str(built["page"]) else built["page"]
            return built["content"], built["page"], showing, str(built["total_pages"]), built["total_pages"], shown, built["page"] <= 1, built["page"] >= built["total_pages"]
        except Exception as e:
            logger.error(f"Error in the {prefix} table: {e}")
            return dbc.Alert(f"Error loading {label} data: {e!s}", color="danger"), 1, "", "1", 1, dash.no_update, True, True


def _register_ms_credentials_callback(app, kind: str):
    """One callback per Microsoft table container (Single Callback Pattern): the open subtab's controller."""
    spec = MS_CREDENTIAL_KINDS[kind]
    prefix = spec["search_id"]

    # ``dbc.Checkbox`` has no ``checked`` prop: the box's state is ``value``.
    @app.callback(
        Output(spec["table_id"], "children"),
        [Input(spec["search_id"], "value"), Input(f"{prefix}-retired", "value"), Input(f"{prefix}-activate", "data")],
        prevent_initial_call=True,
    )
    def update_ms_credentials_table(search_term, show_retired, activated, kind=kind, spec=spec):
        if not activated:
            return dash.no_update
        try:
            certs, applied = split_ms_credentials(ALL_COURSES_DATA["ms_skills"])
            df = certs if kind == "certs" else applied
            if df.empty:
                return dbc.Alert("No data available.", color="warning")
            df = _credentials_in_view(df, bool(show_retired))
            if df.empty:
                return dbc.Alert(f"Sin credenciales vigentes ({int(retired_mask(certs if kind == 'certs' else applied).sum())} retiradas).", color="info")
            df = _search_ms_credentials(df, search_term)
            if df.empty:
                return dbc.Alert("Sin resultados.", color="info")
            return _ms_credentials_table(df, kind, with_retired=bool(show_retired))
        except Exception as e:
            logger.error(f"Error in the {prefix} table: {e}")
            return dbc.Alert(f"Error loading {spec['label']} data: {e!s}", color="danger")


def register_courses_callbacks(app):
    """Register one controller per subtab and the dispatcher that activates the open subtab.

    Every subtab renders its controls and pager, hidden when it has no data, so the literal component ids used here as
    inputs are in the layout before any table exists; the renderer does not run a callback whose input or output is not
    in the page.
    """
    _register_pager_controller(app, "courses-global", "courses-global-results", [("courses-global-search", "value"), ("courses-free-only", "value")], _unified_page, label="the unified catalog", spanish=True)
    _register_numbered_pager_controller(
        app,
        "coursera",
        [("coursera-search-input", "value"), ("coursera-subject-dropdown", "value"), ("coursera-language-dropdown", "value"), ("coursera-free-checkbox", "value")],
        _coursera_view,
        label="Coursera",
    )
    _register_numbered_pager_controller(app, "udemy", [("udemy-search-input", "value"), ("udemy-language-dropdown", "value"), ("udemy-category-dropdown", "value")], _udemy_view, label="Udemy")
    for _kind in MS_CREDENTIAL_KINDS:
        _register_ms_credentials_callback(app, _kind)
    _register_pager_controller(app, "aws-skills", "aws-skills-table-container", [("aws-skills-search-input", "value"), ("aws-skills-language-dropdown", "value")], _aws_page, label="AWS Skill Builder")
    _register_pager_controller(app, "gcp-skills", "gcp-skills-table-container", [("gcp-skills-search-input", "value"), ("gcp-skills-language-dropdown", "value")], _gcp_page, label="GCP Skills Boost")

    # One dispatcher listens to the subtab bar and marks the open subtab as
    # activated; only that subtab's controller runs. It runs in the browser, so
    # it costs no request: 1 marks the store the first time the subtab opens.
    # A store that is marked already gets no_update: a subtab that is opened
    # again keeps the table it has, and its controller does not run a second
    # time for the same rows.
    app.clientside_callback(
        f"""
        function(activeTab) {{
            var tabIds = {json.dumps([tab_id for tab_id, _ in COURSES_SUBTABS])};
            var marked = Array.prototype.slice.call(arguments, 1);
            return tabIds.map(function(tabId, i) {{
                return tabId === activeTab && !marked[i] ? 1 : window.dash_clientside.no_update;
            }});
        }}
        """,
        [Output(f"{prefix}-activate", "data") for _, prefix in COURSES_SUBTABS],
        Input(COURSES_TABS_ID, "active_tab"),
        [State(f"{prefix}-activate", "data") for _, prefix in COURSES_SUBTABS],
        # Runs on insertion too, to activate the subtab that is open when the
        # tab first renders.
        prevent_initial_call=False,
    )


if __name__ == "__main__":
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_courses_tab(), fluid=True, className="py-4")
    register_courses_callbacks(app_test)  # Register callbacks
    print(f"Coursera data loaded: {COURSES_DATA_LOADED['coursera']}, Count: {len(ALL_COURSES_DATA['coursera'])}")
    print(f"Udemy data loaded: {COURSES_DATA_LOADED['udemy']}, Count: {len(ALL_COURSES_DATA['udemy'])}")
    app_test.run(debug=True, port=8059)
