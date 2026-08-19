"""4chan Generals Tab Component for Watchtower Dashboard"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, dash_table, dcc, html

# Import repository pattern (NEW)
from src.etl.fourchan.fourchan_generals_etl import DEFAULT_BOARDS
from src.repositories import BaseRepository
from src.web.dashboard.components.shared.table import render_items_table
from src.web.dashboard.utils import get_data_path

# Set up logging
logger = logging.getLogger(__name__)

DATA_FILE = Path(get_data_path("4chan_generals", "output", "latest.json"))


# NEW: Repository-based loading (SOLID Pattern)
class FourChanRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for 4chan generals data."""

    def __init__(self):
        """Initialize 4chan repository."""
        super().__init__(
            data_path=DATA_FILE,
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform JSON data into list of threads.

        Args:
            raw_data: Raw JSON data

        Returns:
            List of thread dictionaries
        """
        if isinstance(raw_data, list):
            return raw_data
        elif isinstance(raw_data, dict):
            return [raw_data]
        else:
            return []


# Create singleton instance
fourchan_repo = FourChanRepository()


# OLD: Direct file loading (commented out for migration - SAFE TO ROLLBACK)
# def load_4chan_data() -> list[dict[str, Any]]:
#     """Load 4chan generals data from JSON file"""
#     try:
#         if not DATA_FILE.exists():
#             logger.warning(f"4chan data file not found: {DATA_FILE}")
#             return []
#
#         with open(DATA_FILE, encoding="utf-8") as f:
#             data = json.load(f)
#
#         logger.info(f"Loaded {len(data)} 4chan general threads")
#         return data
#     except Exception as e:
#         logger.error(f"Error loading 4chan data: {e}")
#         return []


def load_4chan_data() -> list[dict[str, Any]]:
    """Load 4chan generals data using repository pattern (NEW).

    Returns:
        List of 4chan general threads

    This function now uses the repository pattern with built-in caching.
    """
    try:
        data = fourchan_repo.get()
        logger.info(f"Loaded {len(data)} 4chan general threads")
        return data
    except Exception as e:
        logger.error(f"Error loading 4chan data: {e}")
        return []


def get_board_description(board: str) -> str:
    """Get a description for a board (canonical list lives in the ETL module)."""
    return DEFAULT_BOARDS.get(board, f"Board /{board}/")


def _relative_date(unix_ts) -> str:
    """Format a unix timestamp as a short relative date ('3h', '2d', '45m')."""
    try:
        delta = datetime.now() - datetime.fromtimestamp(int(unix_ts))
        seconds = int(delta.total_seconds())
        if seconds < 0:
            return "now"
        if seconds < 3600:
            return f"{max(1, seconds // 60)}m"
        if seconds < 86400:
            return f"{seconds // 3600}h"
        return f"{seconds // 86400}d"
    except (ValueError, TypeError, OSError):
        return str(unix_ts)


def _activity_score(thread: dict[str, Any]) -> float:
    """Replies per hour since the thread's last activity (spec 06 FA4)."""
    try:
        replies = float(thread.get("replies") or 0)
        hours = max(1.0, (datetime.now() - datetime.fromtimestamp(int(thread.get("last_modified") or 0))).total_seconds() / 3600)
        return round(replies / hours, 2)
    except (ValueError, TypeError, OSError):
        return 0.0


def create_board_table(board: str, threads: list[dict[str, Any]]) -> html.Div:
    """Create a table for a specific board's threads"""
    try:
        if not threads:
            return dbc.Alert(
                f"No active General threads detected for /{board}/ ({get_board_description(board).split(' - ')[1] if ' - ' in get_board_description(board) else 'this board'}).",
                color="info",
                className="alert-info",
            )

        # Prepare data for dash_table
        df = pd.DataFrame(threads)

        # Activity score column (replies/hour, spec FA4)
        if "replies" in df.columns:
            df["Activity"] = df.apply(lambda row: _activity_score(row.to_dict()), axis=1)
            threads = df.to_dict("records")
            threads.sort(key=_activity_score, reverse=True)
            df = pd.DataFrame(threads)

        # Select and rename columns for display
        display_columns = ["subject", "replies", "images", "last_modified", "comment", "url", "Activity"]
        display_columns = [c for c in display_columns if c in df.columns]
        display_df = df[display_columns].copy()

        # Format the data
        display_df["url"] = display_df["url"].apply(lambda x: f"[View Thread]({x})")
        if "last_modified" in display_df.columns:
            display_df["Last Modified"] = display_df["last_modified"].apply(_relative_date)
        if "comment" in display_df.columns:
            # OP preview in the table + full text in the tooltip
            display_df["OP"] = display_df["comment"].apply(lambda c: f"{str(c)[:120]}…" if len(str(c)) > 120 else str(c))
        drop = [c for c in ("last_modified", "comment", "subject", "replies", "images") if c in display_df.columns]
        display_df = display_df.drop(columns=drop)

        display_df.columns = [
            {
                "url": "Thread URL",
                "OP": "OP (preview)",
                "Last Modified": "Last Modified",
                "Activity": "Activity (replies/h)",
            }.get(col, col)
            for col in display_df.columns
        ]
        # Stable column order
        order = ["Subject", "Replies", "Images", "Activity (replies/h)", "Last Modified", "OP (preview)", "Thread URL"]
        display_df = display_df[[c for c in order if c in display_df.columns]]

        # Create table with dark theme styling
        table = dash_table.DataTable(
            id=f"4chan-table-{board}",
            data=display_df.to_dict("records"),
            columns=[{"name": col, "id": col, "type": "numeric" if col in ("Replies", "Images") else "text", "presentation": "markdown" if col == "Thread URL" else "text"} for col in display_df.columns],
            style_cell={
                "textAlign": "left",
                "padding": "12px 16px",
                "fontSize": "14px",
                "fontFamily": "Poppins, sans-serif",
                "backgroundColor": "#2D2B55",
                "color": "#CDD6F4",
                "border": "1px solid #3C3970",
            },
            style_header={
                "backgroundColor": "#3C3970",
                "color": "#E2E8F0",
                "fontWeight": "600",
                "borderBottom": "2px solid #A37FFF",
                "textTransform": "uppercase",
                "fontSize": "0.85em",
                "letterSpacing": "0.5px",
            },
            style_data={
                "backgroundColor": "#2D2B55",
                "color": "#CDD6F4",
                "border": "1px solid #3C3970",
            },
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#252343"},
                {
                    "if": {"state": "selected"},
                    "backgroundColor": "#A37FFF",
                    "color": "#1E1E2E",
                },
                # Activity color coding (spec FA4)
                {"if": {"filter_query": "{Activity (replies/h)} >= 20", "column_id": "Activity (replies/h)"}, "backgroundColor": "#1B4332", "color": "#95D5B2", "fontWeight": "600"},
                {"if": {"filter_query": "{Activity (replies/h)} >= 5 && {Activity (replies/h)} < 20", "column_id": "Activity (replies/h)"}, "backgroundColor": "#4A4E2B", "color": "#D8E48B"},
            ],
            sort_action="native",
            sort_by=[{"column_id": "Activity (replies/h)", "direction": "desc"}] if "Activity (replies/h)" in display_df.columns else None,
            filter_action="native",
            page_action="native",
            page_current=0,
            page_size=10,
            tooltip_data=[{column: {"value": str(value), "type": "markdown"} for column, value in row.items()} for row in display_df.to_dict("records")],
            css=[
                {
                    "selector": ".dash-table-tooltip",
                    "rule": "background-color: #2D2B55; font-family: Poppins, sans-serif; color: #CDD6F4; border: 1px solid #3C3970",
                }
            ],
        )

        board_desc = get_board_description(board)
        return html.Div(
            [
                html.H5(f"/{board}/ – {len(threads)} General threads", className="mb-2"),
                html.P(
                    board_desc.split(" - ")[1] if " - " in board_desc else board_desc,
                    className="text-muted mb-3",
                    style={"fontSize": "0.9em"},
                ),
                table,
            ]
        )

    except Exception as e:
        logger.error(f"Error creating board table for {board}: {e}")
        return dbc.Alert(
            f"Error loading data for board /{board}/: {e!s}",
            color="danger",
            className="alert-danger",
        )


def render_fourchan_tab() -> html.Div:
    """Render the 4chan generals tab"""
    try:
        data = load_4chan_data()

        if not data:
            return html.Div(
                [
                    dbc.Alert(
                        [
                            html.H4("No 4chan Data Available", className="alert-heading"),
                            html.P("No 4chan generals data found. Please run the FourChanGeneralsETL to generate the latest snapshot."),
                            html.Hr(),
                            html.P(f"Expected data location: {DATA_FILE}", className="mb-0"),
                        ],
                        color="warning",
                        className="alert-warning",
                    )
                ],
                className="p-4",
            )

        # Group threads by board
        boards = {item["board"] for item in data}
        grouped = {b: [] for b in boards}
        for item in data:
            grouped[item["board"]].append(item)

        # Sort boards by activity (number of threads), then alphabetically
        boards = sorted(boards, key=lambda b: (-len(grouped[b]), b))

        # Create tabs for each board
        board_content = []

        for _idx, board in enumerate(boards):
            tab_id = f"4chan-board-{board}"

            # Create tab with thread count
            thread_count = len(grouped[board])

            # Create content for this board
            board_content.append(
                dcc.Tab(
                    label=f"/{board}/ ({thread_count})",
                    value=tab_id,
                    children=[html.Div([create_board_table(board, grouped[board])], className="p-3")],
                )
            )

        return html.Div(
            [
                # Header
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H2(
                                    "📑 4chan – Active *General* Threads",
                                    className="mb-3",
                                ),
                                html.P(
                                    [
                                        f"Displaying {len(data)} active general threads across {len(boards)} boards. ",
                                        "Boards are sorted by activity level (most active first).",
                                    ],
                                    className="text-muted",
                                ),
                            ]
                        )
                    ],
                    className="mb-4",
                ),
                # Cross-board global search (spec FA1)
                dcc.Input(
                    id="4chan-global-search",
                    type="text",
                    placeholder="🔎 Buscar en todos los boards (subject + OP)… ej. /dpt/, rust, homelab",
                    debounce=True,
                    className="form-control mb-2",
                ),
                html.Div(id="4chan-global-results", className="mb-3"),
                # Tabs for different boards
                dcc.Tabs(
                    id="4chan-boards-tabs",
                    value=f"4chan-board-{boards[0]}" if boards else "",
                    children=board_content,
                    style={"marginBottom": "20px"},
                    colors={
                        "border": "#374151",
                        "primary": "#9CA3AF",
                        "background": "#1F2937",
                    },
                ),
            ],
            className="p-4",
        )

    except Exception as e:
        logger.error(f"Error rendering 4chan tab: {e}")
        return html.Div(
            [
                dbc.Alert(
                    f"Error loading 4chan generals tab: {e!s}",
                    color="danger",
                    className="alert-danger",
                )
            ],
            className="p-4",
        )


def register_fourchan_callbacks(app):
    """Register callbacks for 4chan tab."""

    # Cross-board global search (spec FA1)
    @app.callback(
        Output("4chan-global-results", "children"),
        Input("4chan-global-search", "value"),
        prevent_initial_call=True,
    )
    def fourchan_global_search(search_term):
        """Search subject + OP text across every board at once."""
        try:
            term = (search_term or "").strip().lower()
            if not term:
                return html.Div()

            data = load_4chan_data()
            matches = [t for t in data if term in str(t.get("subject") or "").lower() or term in str(t.get("comment") or "").lower()]
            if not matches:
                return dbc.Alert(f"Sin resultados para '{search_term}' en ningún board.", color="info")

            matches.sort(key=_activity_score, reverse=True)
            columns = [
                {"header": "Board", "cell": lambda t: dbc.Badge(f"/{t.get('board', '?')}/", color="secondary")},
                {
                    "header": "Subject",
                    "cell": lambda t: html.A(
                        str(t.get("subject") or "(sin subject)")[:100],
                        href=t.get("url"),
                        target="_blank",
                        className="text-decoration-none",
                    ),
                },
                {"header": "Activity/h", "cell": lambda t: _activity_score(t)},
                {"header": "Replies", "cell": lambda t: t.get("replies", 0)},
                {"header": "Last Modified", "cell": lambda t: _relative_date(t.get("last_modified"))},
            ]
            board_count = len({t.get("board") for t in matches})
            return html.Div(
                [
                    dbc.Alert(f"🔎 {len(matches)} threads en {board_count} boards para '{search_term}'", color="success", className="mb-2"),
                    render_items_table(matches[:50], columns, empty_message="Sin resultados.", wrap_scroll=False),
                ]
            )
        except Exception as e:
            logger.error(f"Error in 4chan global search: {e}")
            return dbc.Alert(f"Error en la búsqueda: {e}", color="danger")
