import os
import json
import pandas as pd
from datetime import datetime, timedelta, timezone
import dash
from dash import html, dcc, Input, Output, State, Patch
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

# Import shared utilities
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_data_path, file_exists, dir_exists

# --- Data Loading ---
ALL_VIDEOS_DATA = {} # Will store DataFrames by channel name
VIDEO_DATA_LOADED = False

BASE_VIDEOS_PATH = get_data_path("youtube")

def parse_video_date(date_str):
    """Parses video date strings into datetime objects."""
    if not date_str:
        return None
    try:
        # YouTube typical format: "2023-10-26T14:30:00Z"
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        # Add other formats if necessary for different data sources, though YouTube is usually consistent
        print(f"Warning: Could not parse video date string: {date_str}")
        return None

def load_single_channel_videos(channel_path, channel_name):
    """Loads, processes, and returns a DataFrame for a single channel's videos."""
    json_files_to_try = ["youtube_videos.json", "videos.json"]
    loaded_videos = []

    for json_file in json_files_to_try:
        file_path = os.path.join(channel_path, json_file)
        if file_exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    videos_raw = json.load(f)
                    if isinstance(videos_raw, list):
                        for video_data in videos_raw:
                            # Handle the actual data structure from the JSON
                            title = video_data.get('title', 'No Title')
                            url = video_data.get('url', '')
                            
                            # Use the thumbnail field directly
                            thumbnail_url = video_data.get('thumbnail', '')
                            
                            # Use published_at directly
                            published_at_str = video_data.get('published_at', '')
                            
                            # Get channel from the data or use the folder name
                            channel_display = video_data.get('channel', channel_name)

                            loaded_videos.append({
                                'title': title,
                                'url': url,
                                'thumbnail_url': thumbnail_url,
                                'published_date_str': published_at_str,
                                'published_date': parse_video_date(published_at_str),
                                'channel_name': channel_display,
                                'description': video_data.get('description', ''),
                                'views': video_data.get('views', 0),
                                'length': video_data.get('length', 0),
                            })
                        break # Found and processed a JSON file
            except json.JSONDecodeError:
                print(f"Error decoding JSON from {file_path} for channel {channel_name}")
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")

    if not loaded_videos:
        return pd.DataFrame()

    df = pd.DataFrame(loaded_videos)
    df = df[df['published_date'].notna()] # Remove rows where date parsing failed
    df = df.sort_values(by='published_date', ascending=False)
    return df

def load_videos_data():
    """Loads video data from all channel subdirectories."""
    global ALL_VIDEOS_DATA, VIDEO_DATA_LOADED

    actual_videos_path = BASE_VIDEOS_PATH
    # print(f"Debug: Attempting to load videos from: {actual_videos_path}")

    if not dir_exists(actual_videos_path):
        print(f"Warning: Videos base directory not found: {actual_videos_path}")
        ALL_VIDEOS_DATA = {}
        VIDEO_DATA_LOADED = True # Mark as loaded to prevent constant reload attempts
        return

    channel_dirs = [d for d in os.listdir(actual_videos_path) if os.path.isdir(os.path.join(actual_videos_path, d))]

    if not channel_dirs:
        print(f"Warning: No channel subdirectories found in {actual_videos_path}")
        ALL_VIDEOS_DATA = {}
        VIDEO_DATA_LOADED = True
        return

    for channel_name in channel_dirs:
        channel_path = os.path.join(actual_videos_path, channel_name)
        channel_df = load_single_channel_videos(channel_path, channel_name)
        if not channel_df.empty:
            ALL_VIDEOS_DATA[channel_name] = channel_df
            # print(f"Debug: Loaded {len(channel_df)} videos for channel {channel_name}")
        # else:
            # print(f"Debug: No videos loaded for channel {channel_name}")

    VIDEO_DATA_LOADED = True
    if not ALL_VIDEOS_DATA:
        print("Warning: Video data loading complete, but no videos were found or processed successfully.")
    else:
        print(f"Video data loaded successfully for channels: {list(ALL_VIDEOS_DATA.keys())}")


# Load data when module is imported.
# Consider moving this to a function called by app.py or an explicit "load" button if startup time is an issue.
load_videos_data()

# --- Layout Rendering ---
def render_videos_tab():
    if not VIDEO_DATA_LOADED:
        # This state might occur if load_videos_data() hasn't finished or failed critically (though it sets VIDEO_DATA_LOADED=True on exit)
        return html.Div([
            html.H3("Videos", className="mb-3"),
            dbc.Alert("Video data is currently loading or no data sources could be processed. Please try refreshing shortly.", color="warning", id="video-data-alert")
        ])

    if not ALL_VIDEOS_DATA:
         return html.Div([
            html.H3("Videos", className="mb-3"),
            dbc.Alert("No video data found. Please check the data source and ensure ETLs have run.", color="info", id="no-video-data-alert")
        ])

    channel_options = [{'label': ch_name, 'value': ch_name} for ch_name in ALL_VIDEOS_DATA.keys()]

    return html.Div([
        html.H3("Videos", className="mb-3"),
        dbc.Row([
            dbc.Col(dcc.Dropdown(id="video-category-dropdown", options=channel_options, placeholder="Select Channel"), width=12, md=4, className="mb-2"),
            dbc.Col(dbc.Input(id="video-search-input", placeholder="Search videos by title/description..."), width=12, md=4, className="mb-2"),
            dbc.Col(dcc.Dropdown(
                id="video-date-filter",
                options=[
                    {'label': 'All Time', 'value': 'all'},
                    {'label': 'Last 7 Days', 'value': '7days'},
                    {'label': 'Last 30 Days', 'value': '30days'},
                    {'label': 'Last 90 Days', 'value': '90days'},
                ],
                value='all', # Default value
                clearable=False
            ), width=12, md=4, className="mb-2"),
        ]),
        html.Div(id="video-cards-container", className="mt-3 row"), # Added "row" class for Bootstrap grid
        dbc.Pagination(id="video-pagination", max_value=1, active_page=1, fully_expanded=False, className="mt-3 justify-content-center"),
        dcc.Store(id='video-current-page-store', data=1), # To manage current page state reliably
        dcc.Store(id='video-page-size-store', data=12) # Default page size (e.g., 4 cards per row, 3 rows)
    ])

# --- Callbacks ---
def format_video_published_date(dt_object):
    """Formats datetime object to string 'YYYY-MM-DD HH:MM' or 'Date N/A'."""
    if pd.isna(dt_object) or dt_object is None:
        return "Date N/A"
    try:
        return dt_object.strftime('%Y-%m-%d %H:%M')
    except AttributeError: # Not a datetime object
        return "Invalid Date"

def create_video_card(video_row):
    """Creates a dbc.Card for a single video item (Pandas Series)."""

    # Basic card styling - can be enhanced via CSS
    card_style = {
        "transition": "transform .2s ease-in-out, box-shadow .2s ease-in-out",
    }
    # Hover effect can be defined in CSS for .video-card:hover if preferred
    # card_hover_style = {
    #     "transform": "scale(1.03)",
    #     "boxShadow": "0 4px 20px 0 rgba(0,0,0,0.12)"
    # }

    return dbc.Col(
        dbc.Card(
            [
                dbc.CardImg(src=video_row.get('thumbnail_url', '/assets/placeholder_thumbnail.svg'), top=True, alt=video_row.get('title', 'Video thumbnail'), style={"maxHeight": "180px", "objectFit": "cover"}), # Changed to .svg
                dbc.CardBody(
                    [
                        html.H5(
                            html.A(video_row.get('title', 'No Title'), href=video_row.get('url', '#'), target="_blank", rel="noopener noreferrer", className="stretched-link"),
                            className="card-title", style={"fontSize": "0.95rem", "overflow": "hidden", "textOverflow": "ellipsis", "display": "-webkit-box", "-webkitLineClamp": 2, "-webkitBoxOrient": "vertical", "height": "2.8em"}
                        ), # Height approx 2 lines
                        html.P(
                            video_row.get('channel_name', 'N/A'),
                            className="card-text text-muted",
                            style={"fontSize": "0.8rem"}
                        ),
                        html.P(
                            format_video_published_date(video_row.get('published_date')),
                            className="card-text text-muted",
                            style={"fontSize": "0.8rem"}
                        ),
                    ]
                ),
            ],
            className="mb-4 h-100 video-card", # h-100 for equal height cards if in same row
            style=card_style
        ),
        xs=12, sm=6, md=4, lg=3, xl=3 # Responsive grid: 1 on extra small, 2 on small, 3 on medium, 4 on large/xl
    )

def register_video_callbacks(app):
    @app.callback(
        Output("video-cards-container", "children"),
        Output("video-pagination", "max_value"),
        Output("video-pagination", "active_page"),
        # Output("video-current-page-store", "data"), # Manage current page via pagination's active_page
        Input("video-category-dropdown", "value"),
        Input("video-search-input", "value"),
        Input("video-date-filter", "value"),
        Input("video-pagination", "active_page"),
        Input("video-page-size-store", "data") # Using dcc.Store for page size
    )
    def update_video_display(selected_channel, search_term, date_filter_value, current_page, page_size):
        if not VIDEO_DATA_LOADED or not ALL_VIDEOS_DATA:
            return dbc.Alert("Video data not available.", color="warning"), 1, 1

        # Determine which DataFrame to use
        if selected_channel and selected_channel in ALL_VIDEOS_DATA:
            df_filtered = ALL_VIDEOS_DATA[selected_channel].copy()
        elif not selected_channel: # All channels - combine them
            if not ALL_VIDEOS_DATA: return [], 1, 1
            df_filtered = pd.concat(ALL_VIDEOS_DATA.values(), ignore_index=True)
            df_filtered.sort_values(by='published_date', ascending=False, inplace=True) # Sort again after concat
        else: # Should not happen if dropdown is populated correctly
            return dbc.Alert(f"Selected channel '{selected_channel}' not found.", color="danger"), 1, 1

        # Apply date filter
        if date_filter_value and date_filter_value != 'all':
            days = 0
            if date_filter_value == '7days': days = 7
            elif date_filter_value == '30days': days = 30
            elif date_filter_value == '90days': days = 90

            if days > 0:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                # Ensure 'published_date' is timezone-aware for comparison
                df_filtered = df_filtered[df_filtered['published_date'] >= cutoff_date]

        # Apply search term filter (title and description)
        if search_term:
            search_term_lower = search_term.lower()
            df_filtered = df_filtered[
                df_filtered['title'].str.lower().contains(search_term_lower, na=False) |
                df_filtered['description'].str.lower().contains(search_term_lower, na=False) # Assuming 'description' column exists
            ]

        if df_filtered.empty:
            return dbc.Alert("No videos match your current filters.", color="info"), 1, 1

        # Pagination
        current_page = current_page if current_page else 1 # Default to page 1 if None
        total_videos = len(df_filtered)
        max_pages = (total_videos + page_size - 1) // page_size # Ceiling division

        start_idx = (current_page - 1) * page_size
        end_idx = start_idx + page_size
        df_paginated = df_filtered.iloc[start_idx:end_idx]

        video_cards = [create_video_card(row) for _, row in df_paginated.iterrows()]

        # Ensure current_page is not out of bounds after filtering
        actual_page = min(current_page, max_pages) if max_pages > 0 else 1

        return video_cards, max_pages if max_pages > 0 else 1, actual_page

    # If you want to manage current page via dcc.Store as well (e.g., for resets)
    # This might be redundant if dbc.Pagination handles active_page state well enough on its own.
    # @app.callback(
    #     Output("video-current-page-store", "data"),
    #     Input("video-pagination", "active_page"),
    #     prevent_initial_call=True
    # )
    # def sync_page_to_store(active_page_from_pagination):
    #     return active_page_from_pagination

    # Callback to reset pagination when filters change
    @app.callback(
        Output("video-pagination", "active_page", allow_duplicate=True), # Output active_page
        Input("video-category-dropdown", "value"),
        Input("video-search-input", "value"),
        Input("video-date-filter", "value"),
        prevent_initial_call=True # Very important
    )
    def reset_pagination_on_filter_change(_, __, ___):
        return 1 # Reset to page 1

if __name__ == '__main__':
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_videos_tab(), fluid=True, className="py-4")
    register_video_callbacks(app_test) # Register callbacks for the test app

    print("Running standalone test for videos_tab.py...")
    if not VIDEO_DATA_LOADED: # This check is done after load_videos_data() has run
        print("WARNING: Video data was not loaded at import. Check paths and data files in data/youtube/.")
    elif not ALL_VIDEOS_DATA:
        print("INFO: Video data loading complete, but no channels or videos were found/processed from data/youtube/.")
    else:
        print(f"INFO: Video data loaded for channels: {list(ALL_VIDEOS_DATA.keys())}. Test app running.")

    app_test.run_server(debug=True, port=8053)
