"""
Events tab component for the Watchtower Streamlit application.
Displays events in Valencia.
"""

import streamlit as st
import pandas as pd
import os
import json
from src.web.fullstreamlit.utils.helpers import make_clickable, get_responsive_cols

# Get the project root directory
def get_project_root():
    """Get the project root directory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up from src/web/fullstreamlit/components to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
    return project_root

# Define events data path using absolute path
PROJECT_ROOT = get_project_root()
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
VALENCIA_EVENTS_DATA_DIR = os.path.join(DATA_DIR, "valencia_events")

# Define event data path
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
                        # Build the entire card HTML string
                        card_html = f"<div class='card'>"
                        card_html += f"<h3>{event['title']}</h3>" # Use h3 for consistency
                        
                        # Display dates if available
                        if pd.notna(event.get("date_text")):
                            card_html += f"<p><strong>Fechas:</strong> {event.get('date_text', 'No especificado')}</p>"
                        
                        # Display category if available
                        if pd.notna(event.get("category")) and event.get("category") != "":
                            card_html += f"<p><strong>Categoría:</strong> {event.get('category', 'No especificado')}</p>"
                        
                        # Display source
                        card_html += f"<p><strong>Fuente:</strong> {event.get('source', 'No especificado')}</p>"
                        
                        # Add link to event
                        if "url" in event and pd.notna(event["url"]):
                            card_html += make_clickable(event["url"], "Ver evento") # Already returns HTML
                        
                        card_html += "</div>"
                        
                        # Render the complete card
                        st.markdown(card_html, unsafe_allow_html=True)
            
            # Provide option to view as table
            if st.checkbox("Ver como tabla"):
                # Ensure 'url' is included for the LinkColumn
                display_cols_source = ["title", "date_text", "category", "source", "url"]
                # Select only columns that actually exist in filtered_events_df
                actual_cols_to_select = [col for col in display_cols_source if col in filtered_events_df.columns]
                
                df_for_editor = filtered_events_df[actual_cols_to_select].copy()

                # Rename columns for st.data_editor
                rename_map = {
                    "title": "Título",
                    "date_text": "Fechas",
                    "category": "Categoría",
                    "source": "Fuente",
                    "url": "URL_Enlace" # New name for the raw URL column
                }
                # Apply renaming only for columns that exist in df_for_editor
                active_rename_map = {k: v for k, v in rename_map.items() if k in df_for_editor.columns}
                df_for_editor.rename(columns=active_rename_map, inplace=True)

                # Ensure final column order for st.data_editor
                final_ordered_columns = ["Título", "Fechas", "Categoría", "Fuente", "URL_Enlace"]
                
                # Filter this list to include only columns that actually exist in df_for_editor
                columns_for_editor_display = [col for col in final_ordered_columns if col in df_for_editor.columns]
                df_for_editor = df_for_editor[columns_for_editor_display]

                st.data_editor(
                    df_for_editor,
                    column_config={
                        "Título": st.column_config.TextColumn(width="medium", help="Nombre del evento"),
                        "Fechas": st.column_config.TextColumn(width="medium", help="Fechas del evento"),
                        "Categoría": st.column_config.TextColumn(width="small", help="Categoría del evento"),
                        "Fuente": st.column_config.TextColumn(width="small", help="Fuente de la información"),
                        "URL_Enlace": st.column_config.LinkColumn(
                            label="Enlace",
                            display_text="Ver Evento",
                            width="medium",
                            help="Enlace a la página del evento"
                        )
                    },
                    disabled=True,
                    hide_index=True,
                    use_container_width=True
                )

                if not df_for_editor.empty:
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            label="📥 Descargar CSV (Eventos Valencia)",
                            data=df_for_editor.to_csv(index=False).encode('utf-8'),
                            file_name="valencia_events_data.csv",
                            mime='text/csv',
                            key="csv_download_valencia_events"
                        )
                    with col2:
                        st.download_button(
                            label="📥 Descargar JSON (Eventos Valencia)",
                            data=df_for_editor.to_json(orient='records', indent=2).encode('utf-8'),
                            file_name="valencia_events_data.json",
                            mime='application/json',
                            key="json_download_valencia_events"
                        )