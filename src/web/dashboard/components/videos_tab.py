import os
import json
import pandas as pd
from datetime import datetime, timezone
import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc

# Import dashboard utilities - using absolute path
def get_data_path(*path_parts):
    """Get path to data directory"""
    # Get project root - this file is in src/web/dashboard/components/
    # Go up: components -> dashboard -> web -> src, then we need one more level to get to project root
    current_file = os.path.abspath(__file__)
    src_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
    project_root = os.path.dirname(src_dir)  # Go up one more level from src to project root
    data_path = os.path.join(project_root, "data", *path_parts)
    return data_path

def file_exists(filepath):
    """Check if file exists"""
    return os.path.isfile(filepath)

def dir_exists(dirpath):
    """Check if directory exists"""
    return os.path.isdir(dirpath)

# Global variables
VIDEO_DATA = {}
LOADED = False

def load_video_data():
    """Load video data from all YouTube channel directories"""
    global VIDEO_DATA, LOADED
    
    VIDEO_DATA = {}
    
    youtube_path = get_data_path("youtube")
    if not dir_exists(youtube_path):
        print(f"YouTube data directory not found: {youtube_path}")
        LOADED = True
        return
    
    channels = [d for d in os.listdir(youtube_path) if os.path.isdir(os.path.join(youtube_path, d))]
    
    for channel in channels:
        channel_path = os.path.join(youtube_path, channel)
        json_file = os.path.join(channel_path, "youtube_videos.json")
        
        if file_exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    videos = json.load(f)
                
                # Convert to DataFrame with consistent column names
                video_list = []
                for video in videos:
                    video_list.append({
                        'title': video.get('title', 'No Title'),
                        'url': video.get('url', ''),
                        'thumbnail': video.get('thumbnail', ''),
                        'channel': video.get('channel', channel),
                        'published_at': video.get('published_at', ''),
                        'description': video.get('description', ''),
                        'views': video.get('views', 0),
                        'length': video.get('length', 0)
                    })
                
                if video_list:
                    df = pd.DataFrame(video_list)
                    # Parse dates
                    df['published_date'] = pd.to_datetime(df['published_at'], errors='coerce', utc=True)
                    df = df.dropna(subset=['published_date'])
                    df = df.sort_values('published_date', ascending=False)
                    
                    VIDEO_DATA[channel] = df
                    
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
    
    print(f"Loaded video data for {len(VIDEO_DATA)} channels: {list(VIDEO_DATA.keys())}")
    LOADED = True

def create_video_card(video):
    """Create a simple video card"""
    thumbnail_url = video.get('thumbnail', '')
    
    # Create thumbnail element
    if thumbnail_url:
        thumbnail = html.Img(
            src=thumbnail_url,
            style={
                'width': '100%',
                'height': '180px',
                'objectFit': 'cover',
                'borderRadius': '8px 8px 0 0'
            },
            className="card-img-top"
        )
    else:
        # Placeholder
        thumbnail = html.Div([
            html.I(className="fas fa-video", style={'fontSize': '2rem', 'color': '#A37FFF'}),
            html.Br(),
            html.Span("Video", style={'color': '#A37FFF'})
        ], style={
            'height': '180px',
            'display': 'flex',
            'flexDirection': 'column',
            'alignItems': 'center',
            'justifyContent': 'center',
            'backgroundColor': '#3C3970',
            'borderRadius': '8px 8px 0 0'
        })
    
    return dbc.Col([
        dbc.Card([
            thumbnail,
            dbc.CardBody([
                html.H6(
                    html.A(
                        video.get('title', 'No Title'),
                        href=video.get('url', '#'),
                        target="_blank",
                        style={'color': '#A37FFF', 'textDecoration': 'none'}
                    ),
                    className="card-title",
                    style={
                        'fontSize': '0.9rem',
                        'overflow': 'hidden',
                        'textOverflow': 'ellipsis',
                        'display': '-webkit-box',
                        '-webkitLineClamp': '2',
                        '-webkitBoxOrient': 'vertical',
                        'height': '2.5em',
                        'marginBottom': '0.5rem'
                    }
                ),
                html.P(
                    video.get('channel', 'Unknown'),
                    className="card-text text-muted",
                    style={'fontSize': '0.8rem', 'marginBottom': '0.25rem'}
                ),
                html.P(
                    video.get('published_at', '')[:10] if video.get('published_at') else 'Unknown date',
                    className="card-text text-muted",
                    style={'fontSize': '0.8rem', 'marginBottom': '0'}
                )
            ])
        ], className="h-100")
    ], xs=12, sm=6, md=4, lg=3, xl=3, className="mb-3")

def create_initial_video_cards():
    """Create initial video cards to show immediately"""
    if not LOADED or not VIDEO_DATA:
        return [html.P("Loading videos...", className="text-center text-muted")]
    
    # Get all videos from all channels
    all_videos = []
    for channel, df in VIDEO_DATA.items():
        for _, video in df.iterrows():
            all_videos.append(video.to_dict())
    
    if not all_videos:
        return [html.P("No videos found", className="text-center text-muted")]
    
    # Sort by date and take first 20
    all_videos.sort(key=lambda x: x.get('published_date', datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    displayed_videos = all_videos[:20]
    
    print(f"[INITIAL] Creating {len(displayed_videos)} initial video cards")
    
    # Create cards
    video_cards = [create_video_card(video) for video in displayed_videos]
    return video_cards

def render_videos_tab():
    """Render the videos tab layout"""
    # Load data when rendering
    if not LOADED:
        load_video_data()
    
    if not VIDEO_DATA:
        return html.Div([
            html.H3("Videos", className="mb-3"),
            dbc.Alert("No video data found. Please check if the YouTube ETL has run.", color="info")
        ])
    
    # Create channel options
    channel_options = [{'label': 'All Channels', 'value': 'all'}]
    channel_options.extend([{'label': ch, 'value': ch} for ch in sorted(VIDEO_DATA.keys())])
    
    return html.Div([
        html.H3("Videos", className="mb-3"),
        
        # Controls
        dbc.Row([
            dbc.Col([
                dcc.Dropdown(
                    id="video-channel-dropdown",
                    options=channel_options,
                    value="all",
                    placeholder="Select a channel",
                    className="mb-2"
                )
            ], width=12, md=4),
            dbc.Col([
                dbc.Input(
                    id="video-search-input",
                    placeholder="Search videos...",
                    type="text",
                    className="mb-2"
                )
            ], width=12, md=4),
            dbc.Col([
                dcc.Dropdown(
                    id="video-date-filter",
                    options=[
                        {'label': 'All Time', 'value': 'all'},
                        {'label': 'Last 7 Days', 'value': '7'},
                        {'label': 'Last 30 Days', 'value': '30'},
                        {'label': 'Last 90 Days', 'value': '90'}
                    ],
                    value="all",
                    clearable=False,
                    className="mb-2"
                )
            ], width=12, md=4)
        ]),
        
        # Video grid - will be populated by callback
        html.Div(id="videos-container", className="row"),
        
        # Pagination
        html.Div(id="videos-pagination", className="d-flex justify-content-center mt-3")
    ])

def register_video_callbacks(app):
    """Register video-related callbacks"""
    
    @app.callback(
        [Output("videos-container", "children"),
         Output("videos-pagination", "children")],
        [Input("video-channel-dropdown", "value"),
         Input("video-search-input", "value"),
         Input("video-date-filter", "value")],
        prevent_initial_call=False
    )
    def update_videos(selected_channel, search_term, date_filter):
        print(f"[CALLBACK] Video callback triggered: channel={selected_channel}, search='{search_term}', date={date_filter}")
        print(f"[CALLBACK] Input types: channel={type(selected_channel)}, search={type(search_term)}, date={type(date_filter)}")
        
        # Handle None values (initial callback)
        if selected_channel is None:
            selected_channel = "all"
            print(f"[CALLBACK] Set channel to 'all' from None")
        
        if not LOADED or not VIDEO_DATA:
            print("[CALLBACK] No video data available")
            return [dbc.Alert("No video data available", color="warning")], []
        
        # Get videos based on channel selection
        all_videos = []
        if selected_channel == "all" or not selected_channel:
            # Combine all channels
            for channel, df in VIDEO_DATA.items():
                for _, video in df.iterrows():
                    video_dict = video.to_dict()
                    video_dict['channel'] = channel  # Ensure channel is set
                    all_videos.append(video_dict)
        else:
            # Single channel
            if selected_channel in VIDEO_DATA:
                for _, video in VIDEO_DATA[selected_channel].iterrows():
                    video_dict = video.to_dict()
                    video_dict['channel'] = selected_channel
                    all_videos.append(video_dict)
        
        print(f"[CALLBACK] Found {len(all_videos)} videos before filtering")
        
        # Apply search filter
        if search_term and search_term.strip():
            search_lower = search_term.lower().strip()
            filtered_videos = []
            for v in all_videos:
                title = v.get('title', '').lower()
                description = v.get('description', '').lower()
                channel = v.get('channel', '').lower()
                if (search_lower in title or 
                    search_lower in description or 
                    search_lower in channel):
                    filtered_videos.append(v)
            all_videos = filtered_videos
            print(f"[CALLBACK] After search filter: {len(all_videos)} videos")
        
        # Apply date filter
        if date_filter and date_filter != "all":
            try:
                days = int(date_filter)
                cutoff_date = datetime.now(timezone.utc) - pd.Timedelta(days=days)
                filtered_videos = []
                for video in all_videos:
                    pub_date = video.get('published_date')
                    if pd.notna(pub_date) and pub_date >= cutoff_date:
                        filtered_videos.append(video)
                all_videos = filtered_videos
                print(f"[CALLBACK] After date filter: {len(all_videos)} videos")
            except Exception as e:
                print(f"[CALLBACK] Date filter error: {e}")
        
        # Sort by date (newest first)
        all_videos.sort(key=lambda x: x.get('published_date', datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        
        # Limit to first 24 videos
        displayed_videos = all_videos[:24]
        print(f"[CALLBACK] Displaying {len(displayed_videos)} videos")
        
        # Create cards
        if not displayed_videos:
            return [dbc.Alert("No videos match your filters", color="info")], []
        
        video_cards = [create_video_card(video) for video in displayed_videos]
        
        # Simple pagination info
        pagination_info = html.P(
            f"Showing {len(displayed_videos)} of {len(all_videos)} videos",
            className="text-muted text-center"
        )
        
        print(f"[CALLBACK] Created {len(video_cards)} video cards")
        
        return video_cards, pagination_info

# Load data when module is imported
load_video_data()

if __name__ == "__main__":
    # Test the component
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = dbc.Container([
        render_videos_tab()
    ], fluid=True)
    
    register_video_callbacks(app)
    
    print(f"Test app starting with {len(VIDEO_DATA)} channels loaded")
    app.run(debug=True, port=8054)