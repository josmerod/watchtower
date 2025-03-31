"""
Events tab component for the Watchtower Streamlit application.
Displays events in Valencia.
"""

import streamlit as st
import pandas as pd
import os
import json
from src.web.fullstreamlit.utils.helpers import make_clickable, get_responsive_cols

# Define event data path
VALENCIA_EVENTS_DATA_DIR = "../../../data/valencia_events"
VALENCIA_EVENTS_FILE = os.path.join(VALENCIA_EVENTS_DATA_DIR, "valencia_events.json")

# Local implementation of load_data
def load_data(file_path, _logger=None):
    """Load data from JSON file with error handling"""
    try:
        if os.path.exists(file_path):
            if _logger:
                _logger.info(f"Loading data from {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            if _logger:
                _logger.info(f"Successfully loaded {len(df)} records from {file_path}")
            return df
        else:
            if _logger:
                _logger.error(f"File not found: {file_path}")
            st.error(f"Archivo no encontrado: {file_path}")
            return pd.DataFrame()
    except Exception as e:
        if _logger:
            _logger.error(f"Error loading data from {file_path}: {str(e)}")
        st.error(f"Error al cargar datos desde {file_path}: {str(e)}")
        return pd.DataFrame()

# Local implementation of get_valencia_events_data
@st.cache_data(ttl=3600)
def get_valencia_events_data(_logger=None):
    """Fetch and process Valencia events data"""
    if _logger:
        _logger.info("Loading Valencia events data")
    valencia_events_df = load_data(VALENCIA_EVENTS_FILE, _logger)
    
    if not valencia_events_df.empty:
        # Convert dates if available
        if "start_date" in valencia_events_df.columns:
            valencia_events_df["start_date"] = pd.to_datetime(
                valencia_events_df["start_date"], format="%d/%m/%Y", errors="coerce"
            )
        if "end_date" in valencia_events_df.columns:
            valencia_events_df["end_date"] = pd.to_datetime(
                valencia_events_df["end_date"], format="%d/%m/%Y", errors="coerce"
            )
            
    return valencia_events_df

def render(logger=None):
    """Render the events tab"""
    st.header("🏙️ Eventos en Valencia")
    
    # Load Valencia events data
    valencia_events_df = get_valencia_events_data(_logger=logger)
    logger.info(f"Loaded {len(valencia_events_df)} Valencia events")
    
    if valencia_events_df.empty:
        logger.warning("No Valencia events data available")
        st.warning("No hay datos de eventos disponibles.")
    else:
        # Filters
        search_term = st.text_input("🔍 Buscar en títulos de eventos", "")
        
        # Category filter if categories are available
        categories = valencia_events_df["category"].dropna().unique().tolist()
        if categories:
            selected_categories = st.multiselect(
                "Filtrar por categoría",
                ["Todas"] + categories,
                default=["Todas"]
            )
        
        # Apply filters
        filtered_events_df = valencia_events_df.copy()
        
        if search_term:
            filtered_events_df = filtered_events_df[
                filtered_events_df["title"].str.contains(
                    search_term, case=False, na=False
                )
            ]
        
        if categories and selected_categories and "Todas" not in selected_categories:
            filtered_events_df = filtered_events_df[
                filtered_events_df["category"].isin(selected_categories)
            ]
        
        logger.info(f"Filtered to {len(filtered_events_df)} Valencia events")
        
        # Display results
        if filtered_events_df.empty:
            logger.warning("No event matches found")
            st.warning("No hay eventos que coincidan con los filtros seleccionados.")
        else:
            # Sort by start date if available
            if "start_date" in filtered_events_df.columns:
                filtered_events_df = filtered_events_df.sort_values(
                    by="start_date", ascending=True, na_position="last"
                )
            
            # Display events in a grid format similar to videos
            num_cols = get_responsive_cols()
            for i in range(0, len(filtered_events_df), num_cols):
                cols = st.columns(num_cols)
                for j, (_, event) in enumerate(filtered_events_df.iloc[i:i + num_cols].iterrows()):
                    with cols[j % num_cols]:
                        with st.container():
                            st.markdown(f"<div class='card'>", unsafe_allow_html=True)
                            st.subheader(event["title"])
                            
                            # Display dates if available
                            if pd.notna(event.get("date_text")):
                                st.write(f"**Fechas:** {event.get('date_text', 'No especificado')}")
                            
                            # Display category if available
                            if pd.notna(event.get("category")) and event.get("category") != "":
                                st.write(f"**Categoría:** {event.get('category', 'No especificado')}")
                            
                            # Display source
                            st.write(f"**Fuente:** {event.get('source', 'No especificado')}")
                            
                            # Add link to event
                            if "url" in event and pd.notna(event["url"]):
                                st.markdown(make_clickable(event["url"], "Ver evento"), unsafe_allow_html=True)
                            
                            st.markdown("</div>", unsafe_allow_html=True)
            
            # Provide option to view as table
            if st.checkbox("Ver como tabla"):
                display_cols = ["title", "date_text", "category", "source"]
                display_df = filtered_events_df[display_cols].copy()
                
                # Add URL column with clickable links
                display_df["Ver evento"] = filtered_events_df["url"].apply(
                    lambda x: make_clickable(x, "Ver")
                )
                
                # Rename columns for display
                display_df.rename(
                    columns={
                        "title": "Título",
                        "date_text": "Fechas",
                        "category": "Categoría",
                        "source": "Fuente",
                    },
                    inplace=True,
                )
                
                # Display as HTML table
                st.markdown(
                    display_df.to_html(escape=False, index=False),
                    unsafe_allow_html=True,
                ) 