import hashlib
import json
import logging
import re
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
from src.web.dashboard.components.shared.table import paginate
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


# Theme buckets are channel directories parked under the reserved aa-*/zz-*
# prefixes (T-074 counts them in the 📡 Canales admin view; T-088 filters by
# them in the 📺 Videos tab).
_THEME_ALL_VALUE = "all"
_THEME_DEFAULT_LABEL = "Todos los temas"


def _is_theme_channel(channel: str) -> bool:
    """Whether a channel directory is a theme bucket (``aa-*`` / ``zz-*``)."""
    return channel.startswith(("aa-", "zz-"))


def _extract_theme_options(channels: list[str]) -> list[dict]:
    """Build the Tema dropdown options from channel directory names.

    Args:
        channels: Raw channel names (e.g. from ``VideoManager.get_channels``).

    Returns:
        Dropdown options: the ``Todos los temas`` default first, then one
        option per theme bucket, sorted. When no theme buckets exist only the
        default option is returned.
    """
    themes = sorted({ch for ch in channels if _is_theme_channel(ch)})
    options = [{"label": _THEME_DEFAULT_LABEL, "value": _THEME_ALL_VALUE}]
    options.extend({"label": ch, "value": ch} for ch in themes)
    return options


def _channel_matches_theme(channel: str, theme: str) -> bool:
    """Whether a channel directory belongs to the selected theme bucket.

    Exact match, plus the ``<theme>-*`` suffix so variant directory names of
    the same theme (the ``-videos``/``-channel`` shapes ``get_channels``
    folds) are also captured by the filter.
    """
    return channel == theme or channel.startswith(f"{theme}-")


def _date_sort_key(video: dict):
    """Sort key: dated videos first (newest), undated last."""
    date_value = video.get("published_date")
    if date_value is None or pd.isna(date_value):
        return (0, datetime.min.replace(tzinfo=timezone.utc))
    return (1, date_value)


# Matches the video id in every URL shape the ETLs emit: youtube.com/watch?v=
# (v first or after other params), /shorts/, /embed/, /live/, legacy /v/ and
# /e/, youtube-nocookie.com embeds, and youtu.be/ short links.
_YT_ID_PATTERN = re.compile(
    r"(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:[\w=&%.-]*&)?v=|v/|e/|shorts/|embed/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})",
    re.IGNORECASE,
)


def _extract_youtube_id(url) -> str | None:
    """Extract the 11-character YouTube video id from a URL.

    Args:
        url: Raw video URL as stored by the ETLs (``webpage_url`` from
            yt-dlp: ``watch?v=``, ``shorts/``, ``youtu.be/`` shapes).

    Returns:
        The video id, or None when the URL is empty/unknown — callers must
        degrade gracefully (no preview button, no embed).
    """
    if not url:
        return None
    match = _YT_ID_PATTERN.search(str(url))
    return match.group(1) if match else None


# hash -> minimal record for the embed-preview modal (spec 04 F3). Cards
# register themselves at render time so the pattern-matching callback can
# resolve {"type": "wt-video-preview-btn", "index": <hash>} back to a video.
_VIDEO_REGISTRY_MAX = 5000
_video_registry: dict[str, dict] = {}


def _register_video(video_hash: str, video: dict) -> None:
    """Remember the minimal fields a modal needs for a rendered card.

    The registry is capped: when it overflows it is cleared, which is safe
    because any card still on screen re-registers on the next container
    re-render.
    """
    if len(_video_registry) >= _VIDEO_REGISTRY_MAX:
        _video_registry.clear()
    _video_registry[video_hash] = {
        "title": video.get("title", "No Title"),
        "url": video.get("url", ""),
        "channel": video.get("channel", ""),
    }


def _published_iso(video: dict) -> str | None:
    """Best-effort ISO 8601 publish timestamp for client-side NUEVO badges.

    Prefers the parsed ``published_date``; falls back to the raw
    ``published_at`` string. Returns None for undated videos (the JS skips
    cards without the attribute).
    """
    pub = video.get("published_date")
    try:
        if pub is not None and not pd.isna(pub):
            return pub.isoformat()
    except (TypeError, ValueError):
        pass
    raw = video.get("published_at")
    return str(raw) if raw else None


def _build_video_modal_content(video: dict) -> tuple:
    """Build the (title, body, footer) children for the embed-preview modal.

    Args:
        video: Minimal record from ``_video_registry`` (title, url, channel).

    Returns:
        Tuple of (modal title children, body children with a responsive
        16:9 privacy-enhanced embed, footer children with the YouTube link
        and the close button).
    """
    video_id = _extract_youtube_id(video.get("url"))
    title = video.get("title", "No Title")
    watch_url = video.get("url") or f"https://www.youtube.com/watch?v={video_id}"
    channel = video.get("channel", "")

    # Padding-bottom trick: a responsive 16:9 box without aspect-ratio support
    # requirements; the iframe absolutely fills it.
    body = html.Div(
        html.Iframe(
            src=f"https://www.youtube-nocookie.com/embed/{video_id}",
            title=f"YouTube embed: {title}",
            # "fullscreen" replaces the allowFullScreen attribute (dash 4.x
            # html.Iframe only exposes the standard allow= permission string)
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share; fullscreen",
            style={"position": "absolute", "top": 0, "left": 0, "width": "100%", "height": "100%", "border": 0},
        ),
        style={"position": "relative", "width": "100%", "paddingBottom": "56.25%", "height": 0},
    )

    footer = html.Div(
        [
            html.Span(channel, className="text-muted small me-auto align-self-center"),
            dbc.Button("Ver en YouTube ↗", href=watch_url, target="_blank", external_link=True, color="primary", outline=True, size="sm"),
        ],
        className="d-flex w-100",
    )
    return title, body, footer


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

    def get_channel_stats(self) -> list[dict]:
        """Per-channel summary for the 📡 Canales admin view (spec 04 F4).

        Groups variant directory names under their canonical channel (same
        fold as ``get_channels``) and returns one row per channel with its
        stored video count, the newest publish date seen and whether the
        directory is a theme bucket (``aa-*`` / ``zz-*``).

        Returns:
            Rows sorted by video count (desc), each with keys
            ``channel``, ``count``, ``last_seen`` (``YYYY-MM-DD`` or None)
            and ``is_theme``.
        """
        self.ensure_loaded()
        grouped: dict[str, dict] = {}
        for raw_name in sorted(self.video_data):
            entry = grouped.setdefault(
                _canonical_channel(raw_name),
                {"channel": raw_name, "count": 0, "last_seen": None},
            )
            df = self.video_data[raw_name]
            entry["count"] += len(df)
            if "published_date" in df.columns:
                dates = df["published_date"].dropna()
                if not dates.empty:
                    newest = dates.max()
                    if entry["last_seen"] is None or newest > entry["last_seen"]:
                        entry["last_seen"] = newest

        stats = []
        for entry in grouped.values():
            last_seen = entry["last_seen"]
            stats.append(
                {
                    "channel": entry["channel"],
                    "count": entry["count"],
                    "last_seen": last_seen.strftime("%Y-%m-%d") if last_seen is not None else None,
                    "is_theme": _is_theme_channel(entry["channel"]),
                }
            )
        stats.sort(key=lambda s: (-s["count"], s["channel"].lower()))
        return stats

    def get_videos(self, channel=None, search_term=None, days_filter=None, limit=None, theme_filter=None):
        """Get filtered videos (``limit=None`` returns everything, for pagination).

        Args:
            channel: Channel directory name or ``"all"``.
            search_term: Case-insensitive substring filter on title,
                description and channel.
            days_filter: ``"all"`` or a day-count string for the date cutoff.
            limit: Max videos to return; ``None`` returns everything.
            theme_filter: Theme bucket (``aa-*``/``zz-*`` channel) or
                ``"all"``. Composes with ``channel`` as an intersection: only
                channels matching both selectors contribute videos.
        """
        self.ensure_loaded()

        all_videos = []

        # Resolve the channel selection down to a list of source directories
        if channel is None or channel == "all":
            source_channels = list(self.video_data.keys())
        else:
            source_channels = [channel] if channel in self.video_data else []

        # Theme filter (T-088): keep only channels under the selected theme
        # bucket; applied where channel selection happens so it composes with
        # the search/date filters downstream.
        if theme_filter and theme_filter != _THEME_ALL_VALUE:
            source_channels = [ch for ch in source_channels if _channel_matches_theme(ch, theme_filter)]

        for ch_name in source_channels:
            df = self.video_data[ch_name]
            for video in df.to_dict("records"):
                video_dict = video.copy()
                video_dict["channel"] = ch_name
                all_videos.append(video_dict)

        logger.debug(f"Retrieved {len(all_videos)} videos for channel '{channel}' (theme '{theme_filter}')")

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
    """Create a video card component.

    Cards carry ``data-video-hash`` (md5 of the URL) so ``video_state.js``
    can persist 👁 seen / ▶ watch-later state in localStorage (spec 04 F1).
    """
    thumbnail_url = video.get("thumbnail", "")
    duration = _format_duration(video.get("length"))
    views = _format_views(video.get("views"))
    video_hash = hashlib.md5((video.get("url") or video.get("title", "")).encode("utf-8")).hexdigest()
    video_id = _extract_youtube_id(video.get("url"))
    published_iso = _published_iso(video)

    # The modal callback resolves this card's video via the registry (spec 04 F3)
    _register_video(video_hash, video)

    # Circular ▶ overlay on the thumbnail: opens the in-dashboard embed modal
    # (spec 04 F3). Only rendered when the URL yields a video id.
    preview_button = (
        html.Button(
            "▶",
            id={"type": "wt-video-preview-btn", "index": video_hash},
            className="wt-video-preview-btn",
            title="Vista previa (embed en el dashboard)",
            type="button",
            style={
                "position": "absolute",
                "top": "50%",
                "left": "50%",
                "transform": "translate(-50%, -50%)",
                "width": "44px",
                "height": "44px",
                "borderRadius": "50%",
                "backgroundColor": "rgba(0,0,0,.55)",
                "border": "2px solid rgba(255,255,255,.85)",
                "color": "#fff",
                "fontSize": "1rem",
                "lineHeight": 1,
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "cursor": "pointer",
                "padding": 0,
                "zIndex": 2,
            },
        )
        if video_id
        else None
    )

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
                preview_button,
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
                preview_button,
            ],
            style={
                "position": "relative",
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
        # html.Div wrapper carries the data-* attribute (dbc components don't
        # accept wildcards); video_state.js keys on it
        html.Div(
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
                            html.Div(
                                [
                                    html.Button(
                                        "👁",
                                        className="btn btn-sm btn-outline-secondary wt-video-seen-btn p-1",
                                        title="Marcar como visto",
                                        type="button",
                                    ),
                                    html.Button(
                                        "▶",
                                        className="btn btn-sm btn-outline-secondary wt-video-later-btn p-1 ms-1",
                                        title="Ver más tarde",
                                        type="button",
                                    ),
                                ],
                                className="mt-2",
                            ),
                        ]
                    ),
                ],
                className="h-100",
            ),
            # html wrapper carries the data-* attribute (dbc components don't
            # accept wildcards); video_state.js keys on it
            className="h-100",
            **{
                "data-video-hash": video_hash,
                # Consumed by video_state.js for the NUEVO badge (spec 04 F5);
                # empty on undated cards, which the script then skips.
                "data-published-at": published_iso or "",
            },
        ),
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


def _video_modal_layout():
    """The embed-preview modal shell (spec 04 F3); content filled per video."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(id="wt-video-modal-title"), close_button=True),
            dbc.ModalBody(id="wt-video-modal-body"),
            # The close button must exist statically in the layout: a Dash
            # callback Input with a string id that only appears inside another
            # callback's output raises ReferenceError in the renderer.
            dbc.ModalFooter(
                [
                    html.Div(id="wt-video-modal-footer", className="d-flex w-100 align-items-center"),
                    dbc.Button("Cerrar", id="wt-video-modal-close", color="secondary", outline=True, size="sm", className="ms-2"),
                ]
            ),
        ],
        id="wt-video-modal",
        is_open=False,
        size="lg",
        centered=True,
        scrollable=True,
    )


def _channels_admin_section(stats: list[dict]) -> dbc.Card:
    """Build the read-only 📡 Canales summary card (spec 04 F4).

    Args:
        stats: Rows from ``VideoManager.get_channel_stats()``.

    Returns:
        Dark themed card with a compact table: channel, type (theme bucket
        vs real channel), stored video count and last publish date seen.
    """
    if not stats:
        return dbc.Card(dbc.CardBody("Sin canales cargados."), className="border-0 shadow-sm mb-3")

    total_videos = sum(s["count"] for s in stats)
    theme_count = sum(1 for s in stats if s["is_theme"])
    rows = [
        html.Tr(
            [
                html.Td(html.Span(s["channel"], className="fw-bold" if s["is_theme"] else "")),
                html.Td(dbc.Badge("tema", color="info", pill=True, className="fw-normal") if s["is_theme"] else dbc.Badge("canal", color="secondary", pill=True, className="fw-normal")),
                html.Td(f"{s['count']:,}", className="text-end"),
                html.Td(s["last_seen"] or "—", className="small text-muted"),
            ]
        )
        for s in stats
    ]
    table = dbc.Table(
        [html.Thead(html.Tr([html.Th("Canal"), html.Th("Tipo"), html.Th("Vídeos"), html.Th("Último vídeo")]))] + [html.Tbody(rows)],
        bordered=True,
        hover=True,
        striped=True,
        size="sm",
        color="dark",
        className="mb-0",
    )
    return dbc.Card(
        [
            dbc.CardHeader(
                html.Span(
                    [
                        f"{len(stats)} canales · {total_videos:,} vídeos · ",
                        html.Span(f"{theme_count} temas (aa-*/zz-*)", className="text-muted small"),
                    ],
                    className="small",
                )
            ),
            dbc.CardBody(html.Div(table, style={"maxHeight": "420px", "overflowY": "auto"}), className="p-2"),
        ],
        className="mb-3",
    )


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

    # Organize channels (theme buckets first)
    categories = [ch for ch in sorted(channels) if _is_theme_channel(ch)]
    others = [ch for ch in sorted(channels) if ch not in categories]
    ordered_channels = categories + others

    channel_options.extend([{"label": ch, "value": ch} for ch in ordered_channels])

    # Tema dropdown options (T-088): one per theme bucket, default first
    theme_options = _extract_theme_options(channels)

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
                            html.Label("Tema:", className="form-label small"),
                            dcc.Dropdown(
                                id="videos-theme-dropdown",
                                options=theme_options,
                                value=_THEME_ALL_VALUE,
                                placeholder=_THEME_DEFAULT_LABEL,
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
                            # Filled client-side by video_state.js (👁 visto / ▶ ver más tarde)
                            html.Div(id="videos-state-toolbar"),
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
            # Channels admin view (spec 04 F4): read-only summary table, collapsed
            html.Div(
                [
                    dbc.Button(
                        f"📡 Canales ({len(ordered_channels)})",
                        id="videos-channels-toggle",
                        color="secondary",
                        outline=True,
                        size="sm",
                        className="mb-2",
                        title="Resumen por canal: nº de vídeos y último vídeo visto (spec 04 F4)",
                    ),
                    dbc.Collapse(
                        _channels_admin_section(video_manager.get_channel_stats()),
                        id="videos-channels-collapse",
                        is_open=False,
                    ),
                ]
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
            # Embed-preview modal (spec 04 F3): opened by the ▶ overlay on a
            # card thumbnail; title/body/footer are rebuilt per video by
            # toggle_video_preview_modal.
            _video_modal_layout(),
            # Script to initialize items-per-page selector from localStorage
            html.Script(load_initial_preference("videos")),
        ]
    )


def register_video_callbacks(app):
    """Register video callbacks for filtering and pagination."""

    # Channels admin view (spec 04 F4): show/hide the read-only summary table
    @app.callback(
        Output("videos-channels-collapse", "is_open"),
        Input("videos-channels-toggle", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_videos_channels_section(n_clicks):
        """Toggle the 📡 Canales collapsible (odd clicks open)."""
        return bool(n_clicks and n_clicks % 2)

    @app.callback(
        Output("videos-container", "children"),
        Output("videos-pagination", "children"),
        Output("videos-page", "data"),
        Input("video-channel-dropdown-new", "value"),
        Input("videos-theme-dropdown", "value"),
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
        selected_theme,
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
            if selected_theme is None:
                selected_theme = _THEME_ALL_VALUE
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
            videos = video_manager.get_videos(channel=selected_channel, search_term=search_term, days_filter=date_filter, limit=None, theme_filter=selected_theme)

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

            # Shared pagination helper: slice one page and clamp it into range
            page_videos, total_pages, page = paginate(videos, page, items_per_page)

            video_cards = [create_video_card(video) for video in page_videos]

            channel_display = "all channels" if selected_channel == "all" else f"'{selected_channel}'"
            filters_text = []
            if selected_theme and selected_theme != _THEME_ALL_VALUE:
                filters_text.append(f"tema '{selected_theme}'")
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

    # Embed-preview modal (spec 04 F3): one callback owns every modal output.
    # Pattern-matching Input on the per-card ▶ overlay buttons + the modal's
    # own close button; is_open toggles and the content is rebuilt per video.
    @app.callback(
        Output("wt-video-modal", "is_open"),
        Output("wt-video-modal-title", "children"),
        Output("wt-video-modal-body", "children"),
        Output("wt-video-modal-footer", "children"),
        Input({"type": "wt-video-preview-btn", "index": ALL}, "n_clicks"),
        Input("wt-video-modal-close", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_video_preview_modal(preview_clicks, close_clicks):
        """Open the embed modal for the clicked card, or close it."""
        untouched = (dash.no_update, dash.no_update, dash.no_update, dash.no_update)
        try:
            import dash as _dash

            # ctx.triggered_id is the id object for a real pattern-matching
            # click, the literal id string for the close button, and None (or
            # the wildcard token) when cards are merely (re)rendered — the
            # only cases that must change the modal. Lazily-rendered cards
            # ALSO fire this callback with their concrete id (component-added
            # fire), so a real click additionally requires n_clicks >= 1.
            triggered_id = _dash.ctx.triggered_id

            if triggered_id == "wt-video-modal-close" and (close_clicks or 0) >= 1:
                return False, dash.no_update, dash.no_update, dash.no_update

            if isinstance(triggered_id, dict) and triggered_id.get("type") == "wt-video-preview-btn" and (preview_clicks or 0) >= 1:
                video = _video_registry.get(triggered_id.get("index"))
                if not video:
                    return untouched
                title, body, footer = _build_video_modal_content(video)
                return True, title, body, footer

            return untouched
        except Exception as e:
            logger.error(f"Error toggling video preview modal: {e}")
            return untouched

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
