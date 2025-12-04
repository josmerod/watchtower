import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, dcc, html

from src.web.dashboard.components.items_per_page_selector import (
    create_items_per_page_selector,
    load_initial_preference,
    register_items_per_page_callback,
)
from src.web.dashboard.utils import get_data_path

# Configure logging
logger = logging.getLogger(__name__)


class VideoManager:
    """Manages video data loading and filtering."""

    def __init__(self):
        """Initialize the VideoManager."""
        self.video_data = {}
        self.loaded = False

    def load_data(self):
        """Load video data from YouTube directories."""
        logger.info("Loading video data...")
        self.video_data = {}

        youtube_path = Path(get_data_path("youtube"))
        if not youtube_path.exists():
            logger.warning(f"YouTube directory not found: {youtube_path}")
            self.loaded = True
            return

        # Get all channel directories
        for channel_dir in youtube_path.iterdir():
            if not channel_dir.is_dir():
                continue

            json_file = channel_dir / "youtube_videos.json"
            if not json_file.exists():
                continue

            try:
                with open(json_file, encoding="utf-8") as f:
                    videos = json.load(f)

                if not videos:
                    continue

                # Convert to proper format
                processed_videos = []
                for video in videos:
                    processed_video = {
                        "title": video.get("title", "No Title"),
                        "url": video.get("url", ""),
                        "thumbnail": video.get("thumbnail", ""),
                        "channel": video.get("channel", channel_dir.name),
                        "published_at": video.get("published_at", ""),
                        "description": video.get("description", ""),
                        "views": video.get("views", 0),
                        "length": video.get("length", 0),
                    }
                    processed_videos.append(processed_video)

                if processed_videos:
                    df = pd.DataFrame(processed_videos)
                    # Parse dates properly
                    df["published_date"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
                    df = df.dropna(subset=["published_date"])
                    df = df.sort_values("published_date", ascending=False)

                    self.video_data[channel_dir.name] = df
                    logger.info(f"Loaded {len(df)} videos for {channel_dir.name}")

            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")

        logger.info(f"Total channels loaded: {len(self.video_data)}")
        logger.info(f"Available channels: {list(self.video_data.keys())}")
        self.loaded = True

    def get_channels(self):
        """Get list of available channels."""
        if not self.loaded:
            self.load_data()
        return list(self.video_data.keys())

    def get_videos(self, channel=None, search_term=None, days_filter=None, limit=200):
        """Get filtered videos."""
        if not self.loaded:
            self.load_data()

        all_videos = []

        # Get videos from specified channel(s)
        if channel is None or channel == "all":
            # All channels
            for ch_name, df in self.video_data.items():
                for _, video in df.iterrows():
                    video_dict = video.to_dict()
                    video_dict["channel"] = ch_name
                    all_videos.append(video_dict)
        else:
            # Single channel
            if channel in self.video_data:
                df = self.video_data[channel]
                for _, video in df.iterrows():
                    video_dict = video.to_dict()
                    video_dict["channel"] = channel
                    all_videos.append(video_dict)

        logger.debug(f"Retrieved {len(all_videos)} videos for channel '{channel}'")

        # Apply search filter
        if search_term and search_term.strip():
            search_lower = search_term.lower().strip()
            filtered_videos = []
            for video in all_videos:
                title = video.get("title", "").lower()
                description = video.get("description", "").lower()
                ch = video.get("channel", "").lower()
                if search_lower in title or search_lower in description or search_lower in ch:
                    filtered_videos.append(video)
            all_videos = filtered_videos
            logger.debug(f"After search filter: {len(all_videos)} videos")

        # Apply date filter
        if days_filter and days_filter != "all":
            try:
                days = int(days_filter)
                cutoff_date = datetime.now(timezone.utc) - pd.Timedelta(days=days)
                filtered_videos = []
                for video in all_videos:
                    pub_date = video.get("published_date")
                    if pd.notna(pub_date) and pub_date >= cutoff_date:
                        filtered_videos.append(video)
                all_videos = filtered_videos
                logger.debug(f"After date filter: {len(all_videos)} videos")
            except ValueError:
                pass

        # Sort by date (newest first)
        all_videos.sort(
            key=lambda x: x.get("published_date", datetime.min.replace(tzinfo=timezone.utc)),
            reverse=True,
        )

        # Apply limit
        return all_videos[:limit]


# Global video manager instance
video_manager = VideoManager()


def create_video_card(video):
    """Create a video card component."""
    thumbnail_url = video.get("thumbnail", "")

    # Thumbnail
    if thumbnail_url:
        thumbnail = html.Img(
            src=thumbnail_url,
            style={
                "width": "100%",
                "height": "180px",
                "objectFit": "cover",
                "borderRadius": "8px 8px 0 0",
            },
            className="card-img-top",
        )
    else:
        thumbnail = html.Div(
            [
                html.I(
                    className="fas fa-video",
                    style={"fontSize": "2rem", "color": "#A37FFF"},
                ),
                html.Br(),
                html.Span("Video", style={"color": "#A37FFF"}),
            ],
            style={
                "height": "180px",
                "display": "flex",
                "flexDirection": "column",
                "alignItems": "center",
                "justifyContent": "center",
                "backgroundColor": "#3C3970",
                "borderRadius": "8px 8px 0 0",
            },
        )

    return dbc.Col(
        [
            dbc.Card(
                [
                    thumbnail,
                    dbc.CardBody(
                        [
                            html.H6(
                                html.A(
                                    video.get("title", "No Title"),
                                    href=video.get("url", "#"),
                                    target="_blank",
                                    style={
                                        "color": "#A37FFF",
                                        "textDecoration": "none",
                                    },
                                ),
                                className="card-title",
                                style={
                                    "fontSize": "0.9rem",
                                    "overflow": "hidden",
                                    "textOverflow": "ellipsis",
                                    "display": "-webkit-box",
                                    "-webkitLineClamp": "2",
                                    "-webkitBoxOrient": "vertical",
                                    "height": "2.5em",
                                    "marginBottom": "0.5rem",
                                },
                            ),
                            html.P(
                                video.get("channel", "Unknown"),
                                className="card-text text-muted",
                                style={"fontSize": "0.8rem", "marginBottom": "0.25rem"},
                            ),
                            html.P(
                                (video.get("published_at", "")[:10] if video.get("published_at") else "Unknown date"),
                                className="card-text text-muted",
                                style={"fontSize": "0.8rem", "marginBottom": "0"},
                            ),
                        ]
                    ),
                ],
                className="h-100",
            )
        ],
        xs=12,
        sm=6,
        md=4,
        lg=3,
        xl=3,
        className="mb-3",
    )


def get_initial_video_display(limit=48):
    """Get initial video display with all channels."""
    try:
        # Get videos to display from all channels with specified limit
        videos = video_manager.get_videos(channel="all", limit=limit)
        if not videos:
            return [dbc.Alert("No videos found", color="warning")]

        # Create video cards with error handling
        video_cards = []
        for video in videos:
            try:
                card = create_video_card(video)
                video_cards.append(card)
            except Exception as e:
                # Add fallback card if video card creation fails
                fallback_card = dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H6("Video Load Error", className="card-title"),
                                        html.P(
                                            f"Failed to load: {video.get('title', 'Unknown')}",
                                            className="card-text",
                                        ),
                                        html.Small(f"Error: {e}", className="text-danger"),
                                    ]
                                )
                            ],
                            className="h-100",
                        )
                    ],
                    xs=12,
                    sm=6,
                    md=4,
                    lg=3,
                    xl=3,
                    className="mb-3",
                )
                video_cards.append(fallback_card)

        # Return content with header
        content = [
            dbc.Alert(
                f"📺 Showing {len(video_cards)} videos from all channels",
                color="success",
                className="mb-3",
            ),
            html.Div(video_cards, className="row"),
        ]

        return content

    except Exception as e:
        return [dbc.Alert(f"Error loading videos: {e}", color="danger")]


def render_videos_tab():
    """Render the videos tab."""
    # Load available channels
    channels = video_manager.get_channels()

    if not channels:
        return html.Div(
            [
                html.H3("Videos", className="mb-3"),
                dbc.Alert(
                    "No video data found. Please check if the YouTube ETL has run.",
                    color="info",
                ),
            ]
        )

    # Create channel options
    channel_options = [{"label": "All Channels", "value": "all"}]

    # Organize channels (categories first)
    categories = [ch for ch in sorted(channels) if ch.startswith(("aa-", "zz-"))]
    others = [ch for ch in sorted(channels) if ch not in categories]
    ordered_channels = categories + others

    channel_options.extend([{"label": ch, "value": ch} for ch in ordered_channels])

    return html.Div(
        [
            html.H3("Videos", className="mb-3"),
            # Filter Controls
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Channel:", className="form-label small"),
                            dcc.Dropdown(
                                id="video-channel-dropdown-new",
                                options=channel_options,
                                value="all",
                                placeholder="Select a channel",
                                clearable=False,
                                className="mb-3",
                            ),
                        ],
                        width=12,
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Search:", className="form-label small"),
                            dbc.Input(
                                id="video-search-input-new",
                                placeholder="Search videos...",
                                type="text",
                                className="mb-3",
                            ),
                        ],
                        width=12,
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Date Filter:", className="form-label small"),
                            dcc.Dropdown(
                                id="video-date-filter-new",
                                options=[
                                    {"label": "All Time", "value": "all"},
                                    {"label": "Last 7 Days", "value": "7"},
                                    {"label": "Last 30 Days", "value": "30"},
                                    {"label": "Last 90 Days", "value": "90"},
                                ],
                                value="all",
                                clearable=False,
                                className="mb-3",
                            ),
                        ],
                        width=12,
                        md=3,
                    ),
                    create_items_per_page_selector("videos", default_value=48),
                ],
                className="mb-3",
            ),
            # Videos container - loads 48 videos initially, updates via dropdown callback
            html.Div(
                id="videos-container",
                className="row",
                children=get_initial_video_display(),
            ),
            # Pagination info
            html.Div(id="videos-pagination", className="d-flex justify-content-center mt-3"),
            # Script to initialize items-per-page selector from localStorage
            html.Script(load_initial_preference("videos")),
        ]
    )


def register_video_callbacks(app):
    """Register video callbacks for filtering functionality."""

    @app.callback(
        Output("videos-container", "children"),
        Input("video-channel-dropdown-new", "value"),
        Input("videos-items-per-page-select", "value"),
        prevent_initial_call=True,
    )
    def update_videos_on_channel_change(selected_channel, items_per_page):
        """Update videos when channel selection or items-per-page changes."""
        try:
            if selected_channel is None:
                selected_channel = "all"

            if items_per_page is None:
                items_per_page = 48  # Default fallback

            # Get videos for selected channel with items-per-page limit
            videos = video_manager.get_videos(channel=selected_channel, limit=items_per_page)

            if not videos:
                return [dbc.Alert(f"No videos found for '{selected_channel}'", color="info")]

            # Create video cards
            video_cards = [create_video_card(video) for video in videos]

            # Format channel name for display
            channel_display = "all channels" if selected_channel == "all" else f"'{selected_channel}'"

            content = [
                dbc.Alert(
                    f"📺 Showing {len(video_cards)} videos from {channel_display}",
                    color="success",
                    className="mb-3",
                ),
                html.Div(video_cards, className="row"),
            ]

            return content

        except Exception as e:
            return [dbc.Alert(f"Error loading videos: {e}", color="danger")]

    # Register client-side callback for items-per-page preference saving
    register_items_per_page_callback("videos")


# Load data when module is imported
video_manager.load_data()
