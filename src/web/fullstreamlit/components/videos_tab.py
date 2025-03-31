"""
Videos tab component for the Watchtower Streamlit application.
Displays videos from different categories from YouTube.
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Define data paths locally
VIDEOS_DATA_DIR = "../../../data/youtube"
DEV_VIDEOS_FILE = os.path.join(VIDEOS_DATA_DIR, "dev", "youtube_videos.json")
PERSONAL_DEV_VIDEOS_FILE = os.path.join(VIDEOS_DATA_DIR, "personal_development", "youtube_videos.json")
ECONOMICS_VIDEOS_FILE = os.path.join(VIDEOS_DATA_DIR, "economics", "youtube_videos.json")

# Local version of get_responsive_cols
def get_responsive_cols():
    """Function to determine number of columns based on screen width"""
    # Get the current viewport width using JavaScript
    viewport_width = st.session_state.get('viewport_width', 1200)  # Default to 1200px
    
    if viewport_width >= 1200:
        return 6  # Large screens
    elif viewport_width >= 992:
        return 4  # Medium-large screens
    elif viewport_width >= 768:
        return 3  # Medium screens
    elif viewport_width >= 576:
        return 2  # Small screens
    else:
        return 1  # Extra small screens

# Local version of load_data
def load_data(file_path, logger=None):
    """Load data from JSON file with error handling"""
    try:
        if os.path.exists(file_path):
            if logger:
                logger.info(f"Loading data from {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                import json
                data = json.load(f)
            df = pd.DataFrame(data)
            if logger:
                logger.info(f"Successfully loaded {len(df)} records from {file_path}")
            return df
        else:
            if logger:
                logger.error(f"File not found: {file_path}")
            st.error(f"Archivo no encontrado: {file_path}")
            return pd.DataFrame()
    except Exception as e:
        if logger:
            logger.error(f"Error loading data from {file_path}: {str(e)}")
        st.error(f"Error al cargar datos desde {file_path}: {str(e)}")
        return pd.DataFrame()

# Local version of get_videos_data
def get_videos_data(file_path, logger=None):
    """Fetch and process videos data"""
    if logger:
        logger.info("Loading videos data")
    videos_df = load_data(file_path, logger)

    if not videos_df.empty:
        videos_df["published_date"] = pd.to_datetime(videos_df["published_at"])
        # Add thumbnail URLs if available
        if "thumbnail_url" in videos_df.columns:
            videos_df["thumbnail"] = videos_df["thumbnail_url"]

    return videos_df

def render(logger=None):
    """Render the videos tab"""
    st.header("📺 Videos")

    # Load videos data
    dev_videos_df = get_videos_data(DEV_VIDEOS_FILE, logger)
    personal_dev_videos_df = get_videos_data(PERSONAL_DEV_VIDEOS_FILE, logger)
    economics_videos_df = get_videos_data(ECONOMICS_VIDEOS_FILE, logger)

    if dev_videos_df.empty and personal_dev_videos_df.empty and economics_videos_df.empty:
        st.warning("No hay videos disponibles para mostrar.")
    else:
        # Create tabs for different video categories
        video_tabs = st.tabs(["Desarrollo", "Desarrollo Personal", "Economía"])

        with video_tabs[0]:
            display_videos(dev_videos_df, "Desarrollo")

        with video_tabs[1]:
            display_videos(personal_dev_videos_df, "Desarrollo Personal")

        with video_tabs[2]:
            display_videos(economics_videos_df, "Economía")


def display_videos(videos_df, category_name):
    """Display videos for a specific category"""
    st.header(category_name)
    if not videos_df.empty:
        # Sort by published date
        videos_df = videos_df.sort_values("published_date", ascending=False)
        
        # Get responsive columns based on screen width
        num_cols = get_responsive_cols()
        
        # Display videos in a grid
        for i in range(0, len(videos_df), num_cols):
            cols = st.columns(num_cols)
            for j, (_, video) in enumerate(videos_df.iloc[i:i + num_cols].iterrows()):
                with cols[j % num_cols]:
                    with st.container():
                        st.markdown('<div class="video-card">', unsafe_allow_html=True)
                        
                        # Video thumbnail with link
                        if 'thumbnail' in video and pd.notna(video['thumbnail']):
                            st.markdown(
                                f'<a href="{video["url"]}" target="_blank"><img src="{video["thumbnail"]}" width="100%"></a>',
                                unsafe_allow_html=True
                            )
                        
                        # Video title with link
                        st.markdown(
                            f'<h3><a href="{video["url"]}" target="_blank">{video["title"]}</a></h3>',
                            unsafe_allow_html=True
                        )
                        
                        # Channel name
                        if 'channel_name' in video and pd.notna(video['channel_name']):
                            st.markdown(f'**Canal:** {video["channel_name"]}', unsafe_allow_html=True)
                        
                        # Published date
                        if 'published_date' in video and pd.notna(video['published_date']):
                            published_date = video['published_date'].strftime('%Y-%m-%d')
                            st.markdown(f'**Publicado:** {published_date}', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info(f"No hay videos de {category_name.lower()} disponibles.") 