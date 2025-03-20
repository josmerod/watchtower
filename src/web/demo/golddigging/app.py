import streamlit as st
import pandas as pd
import json
import os
import sys
from datetime import datetime, timedelta
import plotly.express as px

# Add project root to path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)

from src.utils.logging import get_logger

# Initialize logger
logger = get_logger("YouTube_Dashboard")

# Constants
DATA_DIR = "../../../../data/youtube"
VIDEOS_FILE = os.path.join(DATA_DIR, "youtube_videos.json")

logger.info("Starting YouTube Videos Panel")

# Page config
st.set_page_config(
    page_title="YouTube Videos Dashboard",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS
st.markdown(
    """
<style>
    .video-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1.2rem;
        background-color: #222222;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .video-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .video-title {
        font-weight: bold;
        font-size: 1.25rem;
        margin-bottom: 0.5rem;
        color: #1a1a1a;
    }
    .video-meta {
        color: #ccc;
        font-size: 0.9rem;
        margin-bottom: 0.7rem;
    }
    .video-stats {
        display: flex;
        justify-content: space-between;
        margin-top: 0.8rem;
        color: #ccc;
        font-size: 0.95rem;
    }
    .channel-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        background-color: #e6f7ff;
        border-radius: 12px;
        font-size: 0.85rem;
        margin-right: 0.5rem;
    }
    .metric-card {
        background-color: #f0f0f0;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        padding: 1rem;
        text-align: center;
    }
</style>
""",
    unsafe_allow_html=True,
)


def get_channel_badge_class(channel):
    """Return the CSS class for a channel badge"""
    return channel.lower().replace(" ", "-")


def load_data(file_path):
    """Load and parse JSON data file"""
    try:
        if os.path.exists(file_path):
            logger.info(f"Loading data from {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            df = pd.DataFrame(data)

            # Convert published_at to datetime
            df["published_at"] = pd.to_datetime(df["published_at"])

            # Format video length from seconds to HH:MM:SS
            df["duration"] = df["length"].apply(
                lambda x: str(timedelta(seconds=int(x)))
            )

            # Extract video ID from URL
            df["video_id"] = df["url"].apply(
                lambda x: x.split("=")[-1] if "=" in x else x.split("/")[-1]
            )

            # Generate thumbnail URL
            df["thumbnail"] = df["video_id"].apply(
                lambda x: f"https://img.youtube.com/vi/{x}/mqdefault.jpg"
            )

            # Generate channel URL
            df["channel_url"] = df["channel"].apply(
                lambda x: f"https://www.youtube.com/@{x.replace(' ', '')}"
            )

            return df
        else:
            logger.error(f"File not found: {file_path}")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_data():
    """Get and cache data"""
    return load_data(VIDEOS_FILE)


# Load data
df = get_data()

# App title
st.title("🎬 YouTube Videos Analytics Dashboard")
st.markdown(
    "Explore and analyze YouTube videos data with interactive filtering and visualization."
)

if df.empty:
    st.error("No data available. Please check the data file.")
else:
    # Get unique channels for filter
    channels = sorted(df["channel"].unique().tolist())

    # Sidebar filters
    st.sidebar.header("Filters")

    # Channel filter
    selected_channels = st.sidebar.multiselect(
        "Select Channels", options=channels, default=channels
    )

    # Date range filter
    min_date = df["published_at"].min().date()
    max_date = df["published_at"].max().date()

    date_range = st.sidebar.date_input(
        "Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )

    # Ensure date_range is a tuple with two values
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = date_range
        end_date = start_date

    # Convert to datetime for filtering with timezone information
    start_datetime = pd.Timestamp(datetime.combine(start_date, datetime.min.time())).tz_localize('UTC')
    end_datetime = pd.Timestamp(datetime.combine(end_date, datetime.max.time())).tz_localize('UTC')

    # Apply filters
    filtered_df = df[
        (df["channel"].isin(selected_channels))
        & (df["published_at"] >= start_datetime)
        & (df["published_at"] <= end_datetime)
    ].sort_values("published_at", ascending=False)

    # Dashboard metrics
    st.subheader("Dashboard Overview")

    # Display metrics in a grid
    col1, col2 = st.columns(2)

    with col1:
        st.metric("Total Videos", len(filtered_df))

    with col2:
        total_hours = filtered_df["length"].sum() / 3600
        st.metric("Total Hours", f"{total_hours:.1f}")

    # Main content area
    tab1, tab2 = st.tabs(["🔍 Videos", "📊 Analytics"])

    # Tab 1: Videos
    with tab1:
        st.subheader(f"Showing {len(filtered_df)} Videos")

        # Add search functionality
        search_term = st.text_input("Search in titles", "")

        display_df = filtered_df
        if search_term:
            display_df = filtered_df[
                filtered_df["title"].str.contains(search_term, case=False)
            ]
            st.info(f"Found {len(display_df)} videos matching '{search_term}'")

        # Display videos as cards
        for _, video in display_df.iterrows():
            with st.container():
                cols = st.columns([1, 3])

                with cols[0]:
                    # Make the image clickable to go to the video
                    st.markdown(
                        f"<a href='{video['url']}' target='_blank'><img src='{video['thumbnail']}' width='100%'></a>",
                        unsafe_allow_html=True
                    )

                with cols[1]:
                    channel_class = get_channel_badge_class(video["channel"])
                    
                    st.markdown(
                        f"""
                    <div class="video-card">
                        <div class="video-title">
                            <a href="{video['url']}" target="_blank">{video['title']}</a>
                        </div>
                        <div class="video-meta">
                            <a href="{video['url']}" target="_blank">
                                <span class="channel-badge {channel_class}">{video['channel']}</span>
                            </a> | 
                            ⏱️ {video['duration']} | 
                            Published: {video['published_at'].strftime("%Y-%m-%d")}
                        </div>
                        <div class="video-stats">
                            <span></span>
                        </div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                    # Show description on expand
                    with st.expander("Description"):
                        st.write(video["description"])

    # Tab 2: Analytics
    with tab2:
        st.subheader("Channel Analytics")

        # Channel distribution
        st.markdown("#### Videos by Channel")
        channel_counts = filtered_df["channel"].value_counts().reset_index()
        channel_counts.columns = ["Channel", "Count"]

        fig1 = px.bar(
            channel_counts,
            x="Channel",
            y="Count",
            color="Count",
            color_continuous_scale="Viridis",
            text="Count",
        )
        fig1.update_layout(
            xaxis_title="Channel", yaxis_title="Number of Videos", height=400
        )
        fig1.update_traces(textposition="outside")
        st.plotly_chart(fig1, use_container_width=True)

        # Videos over time
        st.markdown("#### Publishing Frequency")
        filtered_df["date"] = filtered_df["published_at"].dt.date
        videos_per_day = (
            filtered_df.groupby(["date", "channel"]).size().reset_index(name="count")
        )

        fig3 = px.line(
            videos_per_day, x="date", y="count", color="channel", markers=True
        )
        fig3.update_layout(
            xaxis_title="Date", yaxis_title="Videos Published", height=400
        )
        st.plotly_chart(fig3, use_container_width=True)

    # Download filtered data
    st.sidebar.markdown("---")
    st.sidebar.download_button(
        label="Download Filtered Data as CSV",
        data=filtered_df.to_csv(index=False).encode("utf-8"),
        file_name=f"youtube_videos_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

# Footer
st.markdown("---")
st.markdown(
    f"Data last updated: {df['metadata'].iloc[0]['processed_at'] if not df.empty else 'N/A'}"
)
st.markdown(
    """<div style="font-size: 0.8rem; color: #777;">
    This dashboard visualizes YouTube videos data. It does not use the YouTube API directly.
    </div>""",
    unsafe_allow_html=True,
)