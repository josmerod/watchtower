import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import ALL, Input, Output, State, dcc, html

from src.web.dashboard.components.items_per_page_selector import (
    create_items_per_page_selector,
    load_initial_preference,
    register_items_per_page_callback,
)
from src.web.dashboard.utils import get_data_path

# Configure logging
logger = logging.getLogger(__name__)


def _canonical_channel(name: str) -> str:
    """Normalize a channel directory name for de-duplication.

    Channel directories can appear under variant names for the same channel
    (e.g. ``MatthewBerman`` vs ``matthew-berman`` vs ``MatthewBerman-videos``).
    This folds common variants so the dropdown and the "all" feed don't list
    the same channel twice.

    Args:
        name: Raw channel directory name.

    Returns:
        A canonical, comparable key (lowercased, trimmed of common suffixes
        and separators).
    """
    canonical = name.strip().lower()
    for suffix in ("-videos", "_videos", "-channel", "_channel", "-official", "_official"):
        if canonical.endswith(suffix):
            canonical = canonical[: -len(suffix)]
    return canonical.replace("_", "-").strip("-")


def _date_sort_key(video: dict):
    """Sort key: dated videos first (newest), undated last."""
    date_value = video.get("published_date")
    if date_value is None or pd.isna(date_value):
        return (0, datetime.min.replace(tzinfo=timezone.utc))
    return (1, date_value)


class VideoManager:
    """Manages video data loading and filtering."""

    DATA_TTL_SECONDS = 300  # Re-read the JSON files at most every 5 minutes

    def __init__(self):
        """Initialize the VideoManager."""
        self.video_data = {}
        self.loaded = False
        self._loaded_at = 0.0

    def _is_fresh(self) -> bool:
        """Whether the in-memory data is within the TTL window."""
        import time

        return self.loaded and (time.time() - self._loaded_at) < self.DATA_TTL_SECONDS

    def ensure_loaded(self, force_refresh: bool = False):
        """Load video data unless it is already loaded and fresh."""
        if force_refresh or not self._is_fresh():
            self.load_data()

    def load_data(self):
        """Load video data from YouTube directories."""
        import time

        logger.info("Loading video data...")
        self.video_data = {}

        youtube_path = Path(get_data_path("youtube"))
        if not youtube_path.exists():
            logger.warning(f"YouTube directory not found: {youtube_path}")
            self.loaded = True
            self._loaded_at = time.time()
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
                    # Parse dates properly; rows without a parseable date are
                    # KEPT (sorted last) instead of silently dropped.
                    df["published_date"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
                    df = df.sort_values("published_date", ascending=False, na_position="last")

                    self.video_data[channel_dir.name] = df
                    logger.info(f"Loaded {len(df)} videos for {channel_dir.name}")

            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")

        logger.info(f"Total channels loaded: {len(self.video_data)}")
        logger.info(f"Available channels: {list(self.video_data.keys())}")
        self.loaded = True
        self._loaded_at = time.time()

    def get_channels(self):
        """Get a de-duplicated list of available channels.

        Channel directories can appear under variant names for the same
        channel (e.g. ``MatthewBerman`` and ``MatthewBerman-videos``); this
        folds them so each channel appears once in the dropdown.
        """
        self.ensure_loaded()
        seen: dict[str, str] = {}
        for raw in self.video_data:
            key = _canonical_channel(raw)
            if key not in seen:
                seen[key] = raw
        return list(seen.values())

    def get_videos(self, channel=None, search_term=None, days_filter=None, limit=None):
        """Get filtered videos (``limit=None`` returns everything, for pagination)."""
        self.ensure_loaded()

        all_videos = []

        # Get videos from specified channel(s)
        if channel is None or channel == "all":
            # All channels
            for ch_name, df in self.video_data.items():
                for video in df.to_dict("records"):
                    video_dict = video.copy()
                    video_dict["channel"] = ch_name
                    all_videos.append(video_dict)
        else:
            # Single channel
            if channel in self.video_data:
                df = self.video_data[channel]
                for video in df.to_dict("records"):
                    video_dict = video.copy()
                    video_dict["channel"] = channel
                    all_videos.append(video_dict)

        logger.debug(f"Retrieved {len(all_videos)} videos for channel '{channel}'")

        # De-duplicate by URL: the same video can appear under two channel
        # directories when a channel was fetched under variant names.
        seen_urls: set[str] = set()
        deduped: list[dict] = []
        for video in all_videos:
            url = video.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            deduped.append(video)
        if len(deduped) != len(all_videos):
            logger.info(f"De-duplicated {len(all_videos) - len(deduped)} duplicate video(s) by URL")
        all_videos = deduped

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

        # Sort by date (newest first; undated videos last)
        all_videos.sort(key=_date_sort_key, reverse=True)

        # Apply limit
        return all_videos[:limit] if limit else all_videos


# Global video manager instance
video_manager = VideoManager()


def _format_duration(length) -> str | None:
    """Normalize a duration (seconds or 'HH:MM:SS'/'MM:SS') to 'H:MM:SS'/'M:SS'."""
    if length in (None, "", 0, "0"):
        return None
    try:
        if isinstance(length, str) and ":" in length:
            parts = [int(p) for p in length.split(":")]
            seconds = sum(part * 60**i for i, part in enumerate(reversed(parts)))
        else:
            seconds = int(float(length))
        if seconds <= 0:
            return None
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
    except (ValueError, TypeError):
        return None


def _format_views(views) -> str | None:
    """Format a view count compactly ('12K', '1.2M')."""
    try:
        count = int(float(views))
    except (ValueError, TypeError):
        return None
    if count <= 0:
        return None
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M views"
    if count >= 1_000:
        return f"{count / 1_000:.0f}K views"
    return f"{count} views"


def create_video_card(video):
    """Create a video card component."""
    thumbnail_url = video.get("thumbnail", "")
    duration = _format_duration(video.get("length"))
    views = _format_views(video.get("views"))

    # Thumbnail
    if thumbnail_url:
        thumbnail = html.Div(
            [
                html.Img(
                    src=thumbnail_url,
                    style={
                        "width": "100%",
                        "height": "180px",
                        "objectFit": "cover",
                        "borderRadius": "8px 8px 0 0",
                    },
                    className="card-img-top",
                ),
                html.Span(
                    duration,
                    style={
                        "position": "absolute",
                        "bottom": "8px",
                        "right": "8px",
                        "backgroundColor": "rgba(0,0,0,.75)",
                        "color": "#fff",
                        "fontSize": "0.72rem",
                        "padding": "1px 6px",
                        "borderRadius": "4px",
                    },
                )
                if duration
                else None,
            ],
            style={"position": "relative"},
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

    channel_line = video.get("channel", "Unknown")
    if views:
        channel_line = f"{channel_line} · {views}"

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
                                channel_line,
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
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.Div(
                                html.I(className="fas fa-video-slash text-muted", style={"fontSize": "3rem"}),
                                className="text-center mb-3",
                            ),
                            html.H5("No video data found", className="text-center mb-2"),
                            html.P(
                                [
                                    "Run the YouTube ETL to populate the Videos tab. ",
                                    html.Br(),
                                    html.Code("uv run python -m src.etl.youtube_shorts.youtube_shorts_etl", className="small"),
                                ],
                                className="text-muted text-center mb-0",
                            ),
                        ]
                    ),
                    className="border-0 shadow-sm",
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
                    dbc.Col(
                        [
                            html.Label("Sort:", className="form-label small"),
                            dcc.Dropdown(
                                id="videos-sort-by",
                                options=[
                                    {"label": "Fecha ⬇", "value": "date_desc"},
                                    {"label": "Fecha ⬆", "value": "date_asc"},
                                    {"label": "Más vistos", "value": "most_viewed"},
                                ],
                                value="date_desc",
                                clearable=False,
                                className="mb-3",
                            ),
                        ],
                        width=12,
                        md=2,
                    ),
                    create_items_per_page_selector("videos", default_value=48),
                    dbc.Col(
                        [
                            html.Label("Preset:", className="form-label small"),
                            dcc.Dropdown(id="videos-preset-selector", options=[], placeholder="Presets guardados…", clearable=True, className="mb-3"),
                        ],
                        width=12,
                        md=2,
                    ),
                    dbc.Col(
                        [
                            html.Label("Save preset:", className="form-label small"),
                            dbc.Button(
                                "💾",
                                id="videos-preset-save",
                                color="secondary",
                                outline=True,
                                size="sm",
                                title="Guarda los filtros actuales como preset (persiste en este navegador)",
                                className="mb-3",
                            ),
                        ],
                        width=12,
                        md=1,
                    ),
                    dbc.Col(
                        [
                            html.Label("Refresh:", className="form-label small"),
                            dbc.Button(
                                "🔄",
                                id="videos-refresh-button",
                                color="secondary",
                                outline=True,
                                title="Re-read the ETL output files (bypasses the 5-minute cache)",
                                n_clicks=0,
                                className="mb-3",
                            ),
                        ],
                        width=12,
                        md=1,
                    ),
                ],
                className="mb-3",
            ),
            # Current page for pagination (server-side slice)
            dcc.Store(id="videos-page", data=1),
            # Saved filter presets, persisted across sessions (spec 15 M3)
            dcc.Store(id="videos-presets", storage_type="local", data={}),
            # Videos container - paginated, updates via the combined callback
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
    """Register video callbacks for filtering and pagination."""

    @app.callback(
        Output("videos-container", "children"),
        Output("videos-pagination", "children"),
        Output("videos-page", "data"),
        Input("video-channel-dropdown-new", "value"),
        Input("video-search-input-new", "value"),
        Input("video-date-filter-new", "value"),
        Input("videos-sort-by", "value"),
        Input("videos-items-per-page-select", "value"),
        Input("videos-refresh-button", "n_clicks"),
        Input({"type": "videos-page-btn", "dir": ALL}, "n_clicks"),
        State("videos-page", "data"),
        prevent_initial_call=False,
    )
    def update_videos_combined(
        selected_channel,
        search_term,
        date_filter,
        sort_by,
        items_per_page,
        refresh_clicks,
        page_btn_clicks,
        current_page,
    ):
        """Update videos with filters + real pagination (prev/next)."""
        try:
            import dash as _dash

            ctx = _dash.callback_context
            triggered = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""
            # Pattern-matching triggers arrive as JSON dicts
            if triggered.startswith("{"):
                try:
                    payload = json.loads(triggered)
                except ValueError:
                    payload = {}
                triggered_id = payload.get("type", "")
                direction = payload.get("dir")
            else:
                triggered_id = triggered
                direction = None

            if triggered_id == "videos-refresh-button":
                video_manager.ensure_loaded(force_refresh=True)

            if selected_channel is None:
                selected_channel = "all"
            if items_per_page is None:
                items_per_page = 48
            current_page = current_page or 1

            # Any filter change resets to page 1; prev/next move within range
            if triggered_id == "videos-page-btn" and direction == "prev":
                page = max(1, current_page - 1)
            elif triggered_id == "videos-page-btn" and direction == "next":
                page = current_page + 1
            else:
                page = 1

            # Full filtered dataset (no cap) so pagination reaches history
            videos = video_manager.get_videos(channel=selected_channel, search_term=search_term, days_filter=date_filter, limit=None)

            if not videos:
                return [dbc.Alert("No videos found matching your criteria.", color="info")], None, 1

            # Sort order (spec 04 F2): date desc (default, undated last), date asc, views
            def _view_count(v: dict) -> int:
                raw = v.get("view_count") or v.get("views") or 0
                try:
                    return int(str(raw).replace(",", "").replace(".", "")) if raw else 0
                except (TypeError, ValueError):
                    return 0

            if sort_by == "date_asc":
                videos.sort(key=_date_sort_key, reverse=False)
            elif sort_by == "most_viewed":
                videos.sort(key=lambda v: (_view_count(v), _date_sort_key(v)), reverse=True)
            else:
                videos.sort(key=_date_sort_key, reverse=True)

            total_pages = max(1, -(-len(videos) // items_per_page))
            page = min(page, total_pages)
            page_videos = videos[(page - 1) * items_per_page : page * items_per_page]

            video_cards = [create_video_card(video) for video in page_videos]

            channel_display = "all channels" if selected_channel == "all" else f"'{selected_channel}'"
            filters_text = []
            if search_term:
                filters_text.append(f"matching '{search_term}'")
            if date_filter and date_filter != "all":
                filters_text.append(f"from last {date_filter} days")
            filter_suffix = f" ({', '.join(filters_text)})" if filters_text else ""

            pagination = None
            if total_pages > 1:
                # Pattern-matching ids: the callback uses Input({"type": ...}, ALL)
                # because these buttons only exist once pagination renders — a
                # literal id in the Input would dead-lock the whole callback
                # until the buttons appear.
                pagination = html.Div(
                    [
                        dbc.Button("« Prev", id={"type": "videos-page-btn", "dir": "prev"}, color="secondary", outline=True, size="sm", disabled=(page <= 1), className="me-2"),
                        html.Span(f"Page {page} of {total_pages} · {len(videos)} videos", className="align-self-center text-muted small me-2"),
                        dbc.Button("Next »", id={"type": "videos-page-btn", "dir": "next"}, color="secondary", outline=True, size="sm", disabled=(page >= total_pages)),
                    ],
                    className="d-flex justify-content-center",
                )

            content = [
                dbc.Alert(
                    f"📺 Showing {len(page_videos)} of {len(videos)} videos from {channel_display}{filter_suffix}",
                    color="success",
                    className="mb-3",
                ),
                html.Div(video_cards, className="row"),
            ]

            return content, pagination, page

        except Exception as e:
            logger.error(f"Error updating videos: {e}")
            return [dbc.Alert(f"Error loading videos: {e}", color="danger")], None, 1

    # Register client-side callback for items-per-page preference saving
    register_items_per_page_callback("videos")

    # Populate preset options from the localStorage store (also on page load)
    app.clientside_callback(
        """
        function(ts, presets) {
            if (!presets) return window.dash_clientside.no_update;
            return Object.keys(presets).map(function(name) {
                return {label: name, value: name};
            });
        }
        """,
        Output("videos-preset-selector", "options", allow_duplicate=True),
        Input("videos-presets", "modified_timestamp"),
        State("videos-presets", "data"),
        prevent_initial_call=True,
    )

    # Filter presets (spec 15 M3): save current filters, apply — persisted
    # in localStorage via the videos-presets Store.
    @app.callback(
        [Output("videos-presets", "data"), Output("videos-preset-selector", "options"), Output("videos-preset-selector", "value")],
        Input("videos-preset-save", "n_clicks"),
        [
            State("videos-presets", "data"),
            State("video-channel-dropdown-new", "value"),
            State("video-date-filter-new", "value"),
            State("videos-sort-by", "value"),
            State("videos-items-per-page-select", "value"),
        ],
        prevent_initial_call=True,
    )
    def save_videos_preset(save_clicks, presets, channel, date_filter, sort_by, per_page):
        """Persist the current filter combo as a named preset."""
        try:
            presets = presets or {}
            name = f"{channel or 'all'} · {date_filter or 'all'}d · {sort_by or 'date_desc'}"
            presets[name] = {
                "channel": channel or "all",
                "date": date_filter or "all",
                "sort": sort_by or "date_desc",
                "per_page": per_page or 48,
            }
            options = [{"label": n, "value": n} for n in presets]
            return presets, options, name
        except Exception as e:
            logger.error(f"Error saving videos preset: {e}")
            return dash.no_update, dash.no_update, dash.no_update

    @app.callback(
        [Output("video-channel-dropdown-new", "value"), Output("video-date-filter-new", "value"), Output("videos-sort-by", "value")],
        Input("videos-preset-selector", "value"),
        State("videos-presets", "data"),
        prevent_initial_call=True,
    )
    def apply_videos_preset(selected_preset, presets):
        """Apply the selected preset's filter values (fires the main controller)."""
        try:
            if not selected_preset or not presets:
                return dash.no_update, dash.no_update, dash.no_update
            preset = presets.get(selected_preset)
            if not preset:
                return dash.no_update, dash.no_update, dash.no_update
            return preset.get("channel", "all"), preset.get("date", "all"), preset.get("sort", "date_desc")
        except Exception as e:
            logger.error(f"Error applying videos preset: {e}")
            return dash.no_update, dash.no_update, dash.no_update


# Load data when module is imported
video_manager.load_data()
