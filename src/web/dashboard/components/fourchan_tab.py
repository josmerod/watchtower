"""4chan Generals Tab Component for Watchtower Dashboard"""
import json
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output
from pathlib import Path
from typing import List, Dict, Any
import logging
import pandas as pd

# Set up logging
logger = logging.getLogger(__name__)

DATA_FILE = Path("data/4chan_generals/output/latest.json")

def load_4chan_data() -> List[Dict[str, Any]]:
    """Load 4chan generals data from JSON file"""
    try:
        if not DATA_FILE.exists():
            logger.warning(f"4chan data file not found: {DATA_FILE}")
            return []
        
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded {len(data)} 4chan general threads")
        return data
    except Exception as e:
        logger.error(f"Error loading 4chan data: {e}")
        return []

def get_board_description(board: str) -> str:
    """Get a description for a board"""
    board_descriptions = {
        "g": "Technology - Programming, hardware, software, and tech discussions",
        "vg": "Video Games Generals - Ongoing game discussions and threads",
        "t": "Torrents - File sharing and technology discussions",
        "pol": "Politically Incorrect - Political discussions and current events",
        "biz": "Business & Finance - Economics, investing, and career advice",
        "sci": "Science & Math - Scientific discussions and research",
        "tv": "Television & Film - TV shows, movies, and entertainment",
        "fit": "Fitness - Health, exercise, and wellness discussions",
        "mu": "Music - All genres, artists, and music production",
        "v": "Video Games - General gaming discussions",
        "k": "Weapons - Firearms, military equipment, and tactics",
        "o": "Auto - Cars, motorcycles, and automotive discussions",
        "diy": "Do It Yourself - Home improvement and crafting projects",
        "his": "History & Humanities - Historical discussions and academia",
        "int": "International - Cultural exchange and world discussions",
    }
    return board_descriptions.get(board, f"Board /{board}/")

def create_board_table(board: str, threads: List[Dict[str, Any]]) -> html.Div:
    """Create a table for a specific board's threads"""
    try:
        if not threads:
            return dbc.Alert(
                f"No active General threads detected for /{board}/ ({get_board_description(board).split(' - ')[1] if ' - ' in get_board_description(board) else 'this board'}).",
                color="info",
                className="alert-info"
            )
        
        # Prepare data for dash_table
        df = pd.DataFrame(threads)
        
        # Select and rename columns for display
        display_columns = ['subject', 'replies', 'images', 'last_modified', 'url']
        display_df = df[display_columns].copy()
        
        # Format the data
        display_df['url'] = display_df['url'].apply(lambda x: f"[View Thread]({x})")
        display_df.columns = ['Subject', 'Replies', 'Images', 'Last Modified', 'Thread URL']
        
        # Create table with dark theme styling
        table = dash_table.DataTable(
            id=f'4chan-table-{board}',
            data=display_df.to_dict('records'),
            columns=[
                {'name': 'Subject', 'id': 'Subject', 'type': 'text'},
                {'name': 'Replies', 'id': 'Replies', 'type': 'numeric'},
                {'name': 'Images', 'id': 'Images', 'type': 'numeric'},
                {'name': 'Last Modified', 'id': 'Last Modified', 'type': 'numeric'},
                {'name': 'Thread URL', 'id': 'Thread URL', 'type': 'text', 'presentation': 'markdown'},
            ],
            style_cell={
                'textAlign': 'left',
                'padding': '12px 16px',
                'fontSize': '14px',
                'fontFamily': 'Poppins, sans-serif',
                'backgroundColor': '#2D2B55',
                'color': '#CDD6F4',
                'border': '1px solid #3C3970'
            },
            style_header={
                'backgroundColor': '#3C3970',
                'color': '#E2E8F0',
                'fontWeight': '600',
                'borderBottom': '2px solid #A37FFF',
                'textTransform': 'uppercase',
                'fontSize': '0.85em',
                'letterSpacing': '0.5px'
            },
            style_data={
                'backgroundColor': '#2D2B55',
                'color': '#CDD6F4',
                'border': '1px solid #3C3970'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#252343'
                },
                {
                    'if': {'state': 'selected'},
                    'backgroundColor': '#A37FFF',
                    'color': '#1E1E2E'
                }
            ],
            sort_action="native",
            filter_action="native",
            page_action="native",
            page_current=0,
            page_size=10,
            tooltip_data=[
                {
                    column: {'value': str(value), 'type': 'markdown'}
                    for column, value in row.items()
                } for row in display_df.to_dict('records')
            ],
            css=[{
                'selector': '.dash-table-tooltip',
                'rule': 'background-color: #2D2B55; font-family: Poppins, sans-serif; color: #CDD6F4; border: 1px solid #3C3970'
            }]
        )
        
        board_desc = get_board_description(board)
        return html.Div([
            html.H5(f"/{board}/ – {len(threads)} General threads", className="mb-2"),
            html.P(board_desc.split(' - ')[1] if ' - ' in board_desc else board_desc, 
                   className="text-muted mb-3", style={"fontSize": "0.9em"}),
            table
        ])
        
    except Exception as e:
        logger.error(f"Error creating board table for {board}: {e}")
        return dbc.Alert(
            f"Error loading data for board /{board}/: {str(e)}",
            color="danger",
            className="alert-danger"
        )

def render_fourchan_tab() -> html.Div:
    """Render the 4chan generals tab"""
    try:
        data = load_4chan_data()
        
        if not data:
            return html.Div([
                dbc.Alert(
                    [
                        html.H4("No 4chan Data Available", className="alert-heading"),
                        html.P("No 4chan generals data found. Please run the FourChanGeneralsETL to generate the latest snapshot."),
                        html.Hr(),
                        html.P(f"Expected data location: {DATA_FILE}", className="mb-0")
                    ],
                    color="warning",
                    className="alert-warning"
                )
            ], className="p-4")
        
        # Group threads by board
        boards = {item["board"] for item in data}
        grouped = {b: [] for b in boards}
        for item in data:
            grouped[item["board"]].append(item)
        
        # Sort boards by activity (number of threads), then alphabetically
        boards = sorted(boards, key=lambda b: (-len(grouped[b]), b))
        
        # Create tabs for each board
        board_tabs = []
        board_content = []
        
        for idx, board in enumerate(boards):
            tab_id = f"4chan-board-{board}"
            
            # Create tab with thread count
            thread_count = len(grouped[board])
            board_tabs.append(
                dbc.Tab(
                    label=f"/{board}/ ({thread_count})",
                    tab_id=tab_id,
                    active_tab_style={"textTransform": "none"}
                )
            )
            
            # Create content for this board
            board_content.append(
                dcc.Tab(
                    id=tab_id,
                    value=tab_id,
                    children=[
                        html.Div([
                            create_board_table(board, grouped[board])
                        ], className="p-3")
                    ]
                )
            )
        
        return html.Div([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H2("📑 4chan – Active *General* Threads", className="mb-3"),
                    html.P([
                        f"Displaying {len(data)} active general threads across {len(boards)} boards. ",
                        "Boards are sorted by activity level (most active first)."
                    ], className="text-muted")
                ])
            ], className="mb-4"),
            
            # Tabs for different boards
            dcc.Tabs(
                id="4chan-boards-tabs",
                value=f"4chan-board-{boards[0]}" if boards else "",
                children=board_content,
                style={'marginBottom': '20px'}
            )
            
        ], className="p-4")
        
    except Exception as e:
        logger.error(f"Error rendering 4chan tab: {e}")
        return html.Div([
            dbc.Alert(
                f"Error loading 4chan generals tab: {str(e)}",
                color="danger",
                className="alert-danger"
            )
        ], className="p-4")

def register_fourchan_callbacks(app):
    """Register callbacks for 4chan tab"""
    # No special callbacks needed for this tab currently
    pass 