"""
Videos tab component for the Watchtower Streamlit application.
Displays videos from different categories from YouTube.
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import glob

# Define data paths locally
VIDEOS_DATA_DIR = "../../../data/youtube"

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
        st.error(f"Directory not found: {base_dir}")
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
                df["published_date"] = pd.to_datetime(df["published_at"])
                if "thumbnail_url" in df.columns:
                     df["thumbnail"] = df["thumbnail_url"]
                videos_data[category_id] = df
            elif logger:
                logger.warning(f"No data loaded or file not found for category '{category_id}' at {video_file}")

    if logger:
        logger.info(f"Discovered categories: {list(categories.values())}")
        logger.info(f"Loaded data for categories: {list(videos_data.keys())}")

    return categories, videos_data

def render(logger=None):
    """Render the videos tab"""
    st.header("📺 Videos")

    # Discover categories and load all video data
    categories, all_videos_data = discover_and_load_videos(VIDEOS_DATA_DIR, logger)

    if not all_videos_data:
        st.warning("No hay videos disponibles para mostrar en ninguna categoría.")
    else:
        # Create a mapping from display name back to category ID
        display_name_to_id = {v: k for k, v in categories.items() if k in all_videos_data}
        
        if not display_name_to_id:
             st.warning("No hay datos de video válidos para las categorías descubiertas.")
             return # Exit if no valid data found

        category_options = list(display_name_to_id.keys())
        
        # Category selector
        selected_display_name = st.selectbox(
            "Selecciona una categoría:",
            options=category_options,
            index=0 # Default to the first category
        )

        if selected_display_name:
            selected_category_id = display_name_to_id[selected_display_name]
            selected_videos_df = all_videos_data.get(selected_category_id)

            if selected_videos_df is not None and not selected_videos_df.empty:
                display_videos(selected_videos_df, selected_display_name)
            else:
                # This case should ideally not happen if display_name_to_id is built correctly
                 st.info(f"No hay videos disponibles para la categoría '{selected_display_name}'.")

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