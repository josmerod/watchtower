"""
Videos tab component for the Watchtower Streamlit application.
Optimized for performance with caching, vectorized operations, and minimal DOM updates.
"""

import streamlit as st
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import gc

@st.fragment
def render_pagination_controls(current_page: int, total_pages: int, prefix: str = "") -> int:
    """Render pagination controls as fragment to avoid full page reruns."""
    if total_pages <= 1:
        return current_page
    
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    
    with col_prev:
        if st.button("⬅️ Anterior", disabled=current_page <= 1, key=f"prev_videos_{prefix}"):
            return max(1, current_page - 1)
    
    with col_info:
        if total_pages <= 10:
            page_options = list(range(1, total_pages + 1))
            selected_page = st.selectbox(
                "Ir a página:",
                options=page_options,
                index=current_page - 1,
                key=f"page_jumper_{prefix}"
            )
            if selected_page != current_page:
                return selected_page
        else:
            st.write(f"Página {current_page} de {total_pages}")
    
    with col_next:
        if st.button("➡️ Siguiente", disabled=current_page >= total_pages, key=f"next_videos_{prefix}"):
            return min(total_pages, current_page + 1)
    
    return current_page

@st.cache_data(max_entries=100, show_spinner=False)
def search_filter_vectorized(df_shape: Tuple[int, int], search_term: str, titles: List[str], channels: List[str]) -> np.ndarray:
    """Vectorized search filtering using numpy for performance."""
    if not search_term:
        return np.ones(df_shape[0], dtype=bool)
    
    search_lower = search_term.lower()
    
    # Vectorized string operations
    title_matches = np.array([search_lower in str(title).lower() for title in titles], dtype=bool)
    channel_matches = np.array([search_lower in str(channel).lower() for channel in channels], dtype=bool)
    
    return title_matches | channel_matches

@st.cache_data(max_entries=50, show_spinner=False)
def date_filter_vectorized(df_shape: Tuple[int, int], days: int, dates: List[datetime]) -> np.ndarray:
    """Vectorized date filtering for performance."""
    if days <= 0:
        return np.ones(df_shape[0], dtype=bool)
    
    cutoff_date = datetime.now() - timedelta(days=days)
    return np.array([date >= cutoff_date if date else False for date in dates], dtype=bool)

@st.cache_data(max_entries=1000, show_spinner=False, ttl=300)
def generate_video_cards_html(video_records: List[Dict], batch_id: str) -> List[str]:
    """Generate HTML cards for video batch with caching to avoid repeated rendering."""
    html_cards = []
    
    for video in video_records:
        thumbnail = video.get('thumbnail', '')
        url = video.get('url', '#')
        title = str(video.get('title', ''))[:100]
        channel_name = video.get('channel_name', '')
        
        # Format publication date
        published_date = ''
        if 'published_date' in video and video['published_date']:
            try:
                if hasattr(video['published_date'], 'strftime'):
                    published_date = video['published_date'].strftime('%Y-%m-%d')
                else:
                    published_date = str(video['published_date'])[:10]
            except:
                published_date = ''
        
        # Generate card HTML
        html = f'''<div class="video-card">
            <a href="{url}" target="_blank">
                <img src="{thumbnail}" loading="lazy" style="width:100%; border-radius: 6px; margin-bottom: 10px; aspect-ratio: 16/9; object-fit: cover;">
            </a>
            <h3><a href="{url}" target="_blank">{title}</a></h3>
            <p style="margin-bottom: 5px;"><strong>Canal:</strong> {channel_name}</p>
            <p style="font-size: 0.9em; color: #CCC6F2;"><strong>Publicado:</strong> {published_date}</p>
        </div>'''
        
        html_cards.append(html)
    
    return html_cards

def get_responsive_columns() -> int:
    """Calculate responsive column count based on viewport width."""
    width = st.session_state.get('viewport_width', 1200)
    
    if width >= 1400: return 6
    if width >= 1200: return 5
    if width >= 992: return 4
    if width >= 768: return 3
    if width >= 576: return 2
    return 1

@st.cache_data(max_entries=20, show_spinner=False)
def extract_video_data(videos_data: Dict[str, pd.DataFrame], category_id: str) -> Tuple[List[str], List[str], List[datetime], List[Dict]]:
    """Extract and cache video data to minimize DataFrame operations."""
    if category_id not in videos_data:
        return [], [], [], []
    
    df = videos_data[category_id]
    if df.empty:
        return [], [], [], []
    
    # Extract all needed data in single pass
    titles = df['title'].fillna('').astype(str).tolist()
    channels = df.get('channel_name', pd.Series([''] * len(df))).fillna('').astype(str).tolist()
    dates = df.get('published_date', pd.Series([None] * len(df))).tolist()
    records = df.to_dict('records')
    
    return titles, channels, dates, records

def render(logger=None, videos_data: Optional[Dict[str, pd.DataFrame]] = None):
    """Render videos tab with performance optimizations."""
    
    st.header("📺 Videos")
    
    # Initialize session state
    session_defaults = {
        'videos_page': 1,
        'videos_search': "",
        'videos_category_id': None,
        'viewport_width': 1200
    }
    
    for key, value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Load data if not provided
    if not videos_data:
        if logger:
            logger.warning("No videos data provided, attempting emergency load")
        
        try:
            import sys
            import os
            from src.web.fullstreamlit.utils.data_service import DataService
            
            data_service = DataService(logger)
            videos_data = data_service.get_videos_data()
            video_categories = data_service.get_video_categories()
        except Exception as e:
            if logger:
                logger.error(f"Failed to load video data: {str(e)}")
            st.error("❌ No se pudieron cargar los datos de videos.")
            return
    else:
        # Generate display names for categories
        video_categories = {
            key: key.replace('_', ' ').replace('-', ' ').title() 
            for key in videos_data.keys()
        }
    
    if not videos_data:
        st.warning("⚠️ No hay datos de videos disponibles.")
        return
    
    # Category selection
    category_options = list(video_categories.values())
    if not category_options:
        st.warning("⚠️ No hay categorías de videos disponibles.")
        return
    
    # Set default category if none selected
    if st.session_state.videos_category_id not in videos_data:
        st.session_state.videos_category_id = list(videos_data.keys())[0]
    
    selected_display = st.selectbox(
        "🏷️ Selecciona una categoría:",
        options=category_options,
        index=category_options.index(video_categories[st.session_state.videos_category_id]) if st.session_state.videos_category_id in video_categories else 0,
        key="video_category_select"
    )
    
    # Update category ID if changed
    new_category_id = None
    for cat_id, display_name in video_categories.items():
        if display_name == selected_display:
            new_category_id = cat_id
            break
    
    if new_category_id != st.session_state.videos_category_id:
        st.session_state.videos_category_id = new_category_id
        st.session_state.videos_page = 1  # Reset pagination
    
    # Extract video data
    titles, channels, dates, records = extract_video_data(videos_data, st.session_state.videos_category_id)
    
    if not records:
        st.info(f"ℹ️ No hay videos disponibles para '{selected_display}'.")
        return
    
    # Filter controls
    col1, col2, col3 = st.columns([3, 2, 1])
    
    with col1:
        search_term = st.text_input(
            "🔍 Buscar videos:",
            value=st.session_state.videos_search,
            placeholder="Buscar por título o canal...",
            key="video_search"
        )
    
    with col2:
        date_filter = st.selectbox(
            "📅 Filtrar por fecha:",
            options=["Todos", "Última semana", "Último mes", "Últimos 3 meses"],
            key="video_date_filter"
        )
    
    with col3:
        page_size = st.selectbox(
            "📄 Por página:",
            options=[12, 24, 36, 48],
            index=1,
            key="video_page_size"
        )
    
    # Apply filters
    df_shape = (len(records), len(records[0]) if records else 0)
    
    # Search filter
    search_mask = search_filter_vectorized(df_shape, search_term, titles, channels)
    
    # Date filter
    date_days_map = {"Última semana": 7, "Último mes": 30, "Últimos 3 meses": 90}
    date_mask = date_filter_vectorized(df_shape, date_days_map.get(date_filter, 0), dates)
    
    # Combine filters
    combined_mask = search_mask & date_mask
    filtered_indices = np.where(combined_mask)[0]
    
    # Reset page if search changed
    if search_term != st.session_state.videos_search:
        st.session_state.videos_page = 1
        st.session_state.videos_search = search_term
    
    # Pagination
    total_items = len(filtered_indices)
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1
    current_page = min(st.session_state.videos_page, total_pages)
    
    # Calculate page slice
    start_idx = (current_page - 1) * page_size
    end_idx = min(start_idx + page_size, total_items)
    
    # Get current page data
    page_indices = filtered_indices[start_idx:end_idx]
    page_records = [records[i] for i in page_indices]
    
    # Display results info
    st.write(f"📊 Mostrando {len(page_records)} de {total_items} videos")
    
    if total_items == 0:
        st.info("🔍 No se encontraron videos con los filtros aplicados.")
        return
    
    # Top pagination controls
    new_page = render_pagination_controls(current_page, total_pages, "top")
    if new_page != current_page:
        st.session_state.videos_page = new_page
        st.rerun()
    
    # Render video grid
    if page_records:
        num_cols = get_responsive_columns()
        
        # Generate HTML for current page
        batch_id = f"{st.session_state.videos_category_id}_{current_page}_{page_size}_{search_term}_{date_filter}"
        html_cards = generate_video_cards_html(page_records, batch_id)
        
        # Render in responsive grid
        video_container = st.container()
        
        with video_container:
            for i in range(0, len(html_cards), num_cols):
                cols = st.columns(num_cols)
                batch_html = html_cards[i:i + num_cols]
                
                for j, html in enumerate(batch_html):
                    col_idx = j % num_cols
                    with cols[col_idx]:
                        st.markdown(html, unsafe_allow_html=True)
    
    # Bottom pagination
    if total_pages > 1:
        st.markdown("---")
        new_page_bottom = render_pagination_controls(current_page, total_pages, "bottom")
        if new_page_bottom != current_page:
            st.session_state.videos_page = new_page_bottom
            st.rerun()
    
    # Memory cleanup for large datasets
    if total_items > 1000:
        gc.collect()