"""
Videos tab component for the Watchtower Streamlit application.
Displays videos from different categories from YouTube.
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import glob
import json

# Determine project root to build absolute paths
COMPONENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(COMPONENT_DIR, "../../../../"))
# Define data paths using project root
VIDEOS_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "youtube")
# Define channels configuration path using project root
CHANNELS_CONFIG_PATH = os.path.join(
    PROJECT_ROOT, "src", "etl", "goldigging", "channels.json"
)

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
                logger.warning(f"File not found (skipping): {file_path}")
            # It's okay if the JSON file doesn't exist yet; return empty
            return pd.DataFrame()
    except Exception as e:
        if logger:
            logger.error(f"Error loading data from {file_path}: {str(e)}")
        # Use warning to surface parsing/loading issues but continue
        st.warning(f"Error al cargar datos desde {file_path}: {str(e)}")
        return pd.DataFrame()

# Helper function to format category names
def format_category_name(dir_name):
    """Converts directory name to a display-friendly name."""
    return dir_name.replace('_', ' ').replace('-', ' ').title()

# New function to discover categories and load video data
def discover_and_load_videos(base_dir, logger=None):
    """Discovers categories based on subdirectories and loads their video data."""
    categories = {}
    videos_data = {}
    
    if not os.path.isdir(base_dir):
        st.warning(f"Data directory no encontrado (skipping videos): {base_dir}")
        if logger:
            logger.error(f"Video data directory not found: {base_dir}")
        return categories, videos_data

    if logger:
        logger.info(f"Discovering video categories in {base_dir}")

    for item_path in glob.glob(os.path.join(base_dir, '*')):
        if os.path.isdir(item_path):
            category_id = os.path.basename(item_path)
            display_name = format_category_name(category_id)
            categories[category_id] = display_name
            
            video_file = os.path.join(item_path, "youtube_videos.json")
            if logger:
                logger.info(f"Attempting to load data for category '{category_id}' from {video_file}")
            
            df = load_data(video_file, logger)
            if not df.empty:
                # Normalize date and channel columns
                df["published_date"] = pd.to_datetime(df["published_at"])
                # Ensure channel_name exists for filtering
                if "channel" in df.columns:
                    df["channel_name"] = df["channel"]
                # Handle thumbnail URL if provided
                if "thumbnail_url" in df.columns:
                    df["thumbnail"] = df["thumbnail_url"]
                videos_data[category_id] = df
            elif logger:
                logger.warning(f"No data loaded or file not found for category '{category_id}' at {video_file}")

    if logger:
        logger.info(f"Discovered categories: {list(categories.values())}")
        logger.info(f"Loaded data for categories: {list(videos_data.keys())}")

    return categories, videos_data

# Load channels configuration from JSON
def load_channels_config(file_path, logger=None):
    """Load channels configuration from JSON file."""
    try:
        if os.path.exists(file_path):
            if logger:
                logger.info(f"Loading channels config from {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            if logger:
                logger.info(f"Successfully loaded channels config with {len(config)} categories")
            return config
        else:
            if logger:
                logger.error(f"Channels config file not found: {file_path}")
            st.warning(f"Archivo de configuración de canales no encontrado: {file_path}")
            return {}
    except Exception as e:
        if logger:
            logger.error(f"Error loading channels config from {file_path}: {str(e)}")
        st.warning(f"Error al cargar configuración de canales: {str(e)}")
        return {}

def render(logger=None):
    """Render the videos tab with category and optional channel filtering."""
    st.header("📺 Videos")

    # Attempt to load channels.json config
    channels_config = load_channels_config(CHANNELS_CONFIG_PATH, logger)
    # Discover available video directories and data
    discovered_cats, all_videos_data = discover_and_load_videos(VIDEOS_DATA_DIR, logger)

    # Determine categories: prefer config keys, else fallback to discovered directories
    if channels_config:
        # Use config for category list
        category_map = {
            cat_id: info.get("description") or format_category_name(cat_id)
            for cat_id, info in channels_config.items()
        }
        use_config = True
    else:
        st.warning("No se pudo cargar configuración de canales; usando categorías descubiertas.")
        category_map = discovered_cats
        use_config = False

    # Guard if no categories available
    if not category_map:
        st.warning("No hay categorías disponibles para mostrar.")
        return

    # Build display-name to category-id mapping
    display_to_id = {disp: cid for cid, disp in category_map.items()}
    selected_disp = st.selectbox(
        "Selecciona una categoría:",
        options=list(display_to_id.keys())
    )
    selected_id = display_to_id[selected_disp]

    # Retrieve videos or default to empty
    videos_df = all_videos_data.get(selected_id, pd.DataFrame())
    if videos_df.empty:
        st.warning("No se encontraron videos recientes para esta categoría.")

    # If using config, show channel list and enable channel filter
    if use_config:
        channels_list = channels_config.get(selected_id, {}).get("channels", [])
        if channels_list:
            st.subheader("Canales de esta categoría")
            cols = get_responsive_cols()
            for i in range(0, len(channels_list), cols):
                row = st.columns(cols)
                for j, ch in enumerate(channels_list[i : i + cols]):
                    url = (
                        f"https://www.youtube.com/channel/{ch}"
                        if ch.startswith("UC")
                        else f"https://www.youtube.com/c/{ch}"
                    )
                    with row[j % cols]:
                        st.markdown(f"[{ch}]({url})", unsafe_allow_html=True)

            # Filter by channel
            filter_opts = ["Todos los canales"] + channels_list
            sel_ch = st.selectbox("Selecciona un canal:", options=filter_opts)
            if sel_ch and sel_ch != "Todos los canales":
                videos_df = videos_df[videos_df.get("channel_name") == sel_ch]

    # Finally display videos or show info if none
    if not videos_df.empty:
        display_videos(videos_df, selected_disp)
    else:
        st.info(f"No hay videos disponibles para la categoría '{selected_disp}'.")

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
                    # Build the entire card HTML string
                    card_html = '<div class="video-card">'
                    
                    # Video thumbnail with link
                    if 'thumbnail' in video and pd.notna(video['thumbnail']):
                        card_html += f'<a href="{video["url"]}" target="_blank"><img src="{video["thumbnail"]}" style="width:100%; border-radius: 6px; margin-bottom: 10px;"></a>'
                    
                    # Video title with link
                    card_html += f'<h3><a href="{video["url"]}" target="_blank">{video["title"]}</a></h3>'
                    
                    # Channel name
                    if 'channel_name' in video and pd.notna(video['channel_name']):
                        card_html += f'<p style="margin-bottom: 5px;"><strong>Canal:</strong> {video["channel_name"]}</p>'
                    
                    # Published date
                    if 'published_date' in video and pd.notna(video['published_date']):
                        published_date = video['published_date'].strftime('%Y-%m-%d')
                        card_html += f'<p style="font-size: 0.9em; color: #CCC6F2;"><strong>Publicado:</strong> {published_date}</p>'
                    
                    card_html += '</div>'
                    
                    # Render the complete card with a single markdown call
                    st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info(f"No hay videos de {category_name.lower()} disponibles.") 