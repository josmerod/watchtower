"""
Courses tab component for the Watchtower Streamlit application.
Displays online course data from various platforms like Coursera and Udemy.
"""

import streamlit as st
import pandas as pd
import json
import os
from src.web.fullstreamlit.utils.helpers import make_clickable, get_responsive_cols
from typing import Dict, List, Optional, Any, Union

# Get the project root directory
def get_project_root():
    """Get the project root directory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up from src/web/fullstreamlit/components to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
    return project_root

# Define course data paths using absolute paths
PROJECT_ROOT = get_project_root()
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

COURSERA_DATA_DIR = os.path.join(DATA_DIR, "classcentral")
UDEMY_DATA_DIR = os.path.join(DATA_DIR, "udemy")

COURSERA_FILE = os.path.join(COURSERA_DATA_DIR, "coursera_courses.json")
UDEMY_FILE = os.path.join(UDEMY_DATA_DIR, "udemy_courses.json")

def load_coursera_courses_from_multiple_paths():
    """Try loading Coursera courses from multiple potential paths"""
    
    # Try the main path first
    if os.path.exists(COURSERA_FILE):
        try:
            with open(COURSERA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Error reading Coursera data from main path: {str(e)}")
    
    # If main path fails, return empty data
    st.warning("No se encontraron cursos de Coursera en las rutas esperadas")
    return []

def load_udemy_courses_from_multiple_paths():
    """Try loading Udemy courses from multiple potential paths"""
    
    # Try the main path first
    if os.path.exists(UDEMY_FILE):
        try:
            with open(UDEMY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Error reading Udemy data from main path: {str(e)}")
    
    # If main path fails, return empty data
    st.warning("No se encontraron cursos de Udemy en las rutas esperadas")
    return []

def render(courses_data: Dict[str, pd.DataFrame], logger=None):
    """
    Render the courses tab with data from different platforms
    
    Parameters
    ----------
    courses_data : Dict[str, pd.DataFrame]
        Dictionary containing dataframes for each platform {'coursera': coursera_df, ...}
    logger : Optional[Any]
        Logger instance for logging errors/warnings
    """
    st.header("🎓 Cursos Online")
    
    # Emergency direct loading if data is empty
    if not courses_data or all(df.empty for df in courses_data.values()):
        if logger:
            logger.warning("No data from loader, trying direct load")
        
        # Load available course data from JSON files
        loaded_data = {}
        coursera_json = load_coursera_courses_from_multiple_paths()
        if coursera_json:
            try:
                st.success(f"¡Cargados {len(coursera_json)} cursos de Coursera directamente del archivo!")
                loaded_data["coursera"] = pd.DataFrame(coursera_json)
            except Exception as e:
                if logger:
                    logger.error(f"Error loading Coursera data directly: {str(e)}")
                st.error(f"Error cargando datos de Coursera: {str(e)}")
        else:
            if logger:
                logger.error("Could not find coursera_courses.json in any path")
            st.error("No se pudo encontrar el archivo de cursos de Coursera.")
        
        udemy_json = load_udemy_courses_from_multiple_paths()
        if udemy_json:
            try:
                st.success(f"¡Cargados {len(udemy_json)} cursos de Udemy directamente del archivo!")
                loaded_data["udemy"] = pd.DataFrame(udemy_json)
            except Exception as e:
                if logger:
                    logger.error(f"Error loading Udemy data directly: {str(e)}")
                st.error(f"Error cargando datos de Udemy: {str(e)}")
        else:
            if logger:
                logger.error("Could not find udemy_courses.json in any path")
            st.info("No se pudo encontrar el archivo de cursos de Udemy.")
        
        courses_data = loaded_data

    # Check if all dataframes are empty after emergency loading
    all_empty = all(df.empty for df in courses_data.values())
    if all_empty or not courses_data:
        if logger:
            logger.warning("No course data available to display.")
        st.warning("No hay datos de cursos disponibles para mostrar.")
        return  # Exit if no data

    # Create tabs for different course platforms
    tab_titles = []
    for platform, df in courses_data.items():
        if not df.empty:
            # Capitalize first letter of platform name for display
            tab_titles.append(platform.capitalize())

    if not tab_titles:  # Should not happen if the initial check passed, but good practice
        st.warning("No hay datos de cursos válidos para mostrar en las pestañas.")
        return

    tabs = st.tabs(tab_titles)
    tab_map = {title: tab for title, tab in zip(tab_titles, tabs)}

    # Display content within each tab
    for platform, tab in tab_map.items():
        with tab:
            if platform.lower() == "coursera":
                display_coursera_courses(courses_data["coursera"])
            elif platform.lower() == "udemy":
                display_udemy_courses(courses_data["udemy"])
            # Add other platforms as they are added
            # elif platform.lower() == "edx":
            #     display_edx_courses(courses_data["edx"])
            # etc.


def display_coursera_courses(courses_df: pd.DataFrame):
    """
    Display Coursera courses
    
    Parameters
    ----------
    courses_df : pd.DataFrame
        DataFrame containing Coursera courses data
    """
    if courses_df.empty:
        st.warning("No hay cursos de Coursera disponibles.")
        return

    # Use the original DataFrame to preserve JSON order - create a copy first
    filtered_courses_df = courses_df.copy()
    
    # Store original index to maintain order
    filtered_courses_df = filtered_courses_df.reset_index(drop=True)
    original_order = filtered_courses_df.index.copy()
    
    # Convert scraped_at to datetime if it exists (for display only, not sorting)
    if "scraped_at" in filtered_courses_df.columns:
        filtered_courses_df["scraped_at"] = pd.to_datetime(filtered_courses_df["scraped_at"], errors='coerce')
        filtered_courses_df["fecha_adición"] = filtered_courses_df["scraped_at"].dt.strftime("%Y-%m-%d")
        filtered_courses_df = filtered_courses_df.reindex(original_order) # Ensure original order
    else:
        # Ensure fecha_adición column exists even if scraped_at is missing, for schema consistency
        filtered_courses_df["fecha_adición"] = None 

    with st.expander("Filtros y Opciones para Coursera", expanded=True):
        search_term = st.text_input("Buscar cursos:", placeholder="Ingrese palabras clave...", key="coursera_search")
        if search_term:
            search_term_lower = search_term.lower()
            title_mask = filtered_courses_df["title"].str.lower().str.contains(search_term_lower, na=False)
            desc_mask = pd.Series([False] * len(filtered_courses_df)) # Default if no description
            if "description" in filtered_courses_df.columns:
                desc_mask = filtered_courses_df["description"].str.lower().str.contains(search_term_lower, na=False)
            search_mask = title_mask | desc_mask
            filtered_courses_df = filtered_courses_df[search_mask]
            # Note: No st.write for search results here, count will be shown later

        col1, col2 = st.columns(2)
        with col1:
            if "subject" in filtered_courses_df.columns:
                subjects = sorted(filtered_courses_df["subject"].dropna().unique().tolist())
                subjects = ["Todos los temas"] + subjects
                selected_subject = st.selectbox("Filtrar por tema:", subjects, key="coursera_subject")
                if selected_subject != "Todos los temas":
                    filtered_courses_df = filtered_courses_df[filtered_courses_df["subject"] == selected_subject]
        
        with col2:
            if "language" in filtered_courses_df.columns:
                languages = sorted(filtered_courses_df["language"].dropna().unique().tolist())
                languages = ["Todos los idiomas"] + languages
                selected_language = st.selectbox("Filtrar por idioma:", languages, key="coursera_language")
                if selected_language != "Todos los idiomas":
                    filtered_courses_df = filtered_courses_df[filtered_courses_df["language"] == selected_language]

        if "is_free" in filtered_courses_df.columns:
            show_only_free = st.checkbox("Mostrar solo cursos gratuitos", key="coursera_free_checkbox")
            if show_only_free:
                filtered_courses_df = filtered_courses_df[filtered_courses_df["is_free"] == True]

    st.write(f"Mostrando {len(filtered_courses_df)} cursos")

    if not filtered_courses_df.empty:
        # Define all potential columns that could be displayed
        potential_display_cols = ["title", "institution", "subject", "language", "duration", "start_date", "fecha_adición"]
        
        # Select only existing columns from the filtered DataFrame
        display_columns = [col for col in potential_display_cols if col in filtered_courses_df.columns]
        display_courses_df = filtered_courses_df[display_columns].copy()

        # Add special columns
        display_courses_df["Ver Curso"] = filtered_courses_df["url"].apply(lambda x: make_clickable(x, "Ver Detalles"))
        
        if "is_free" in filtered_courses_df.columns:
            display_courses_df["Gratis"] = filtered_courses_df["is_free"].apply(lambda x: "✅" if x else "❌")
        else:
            display_courses_df["Gratis"] = "N/A" # Or "❌" or "" depending on desired display for missing data

        if "certificate_offered" in filtered_courses_df.columns:
            display_courses_df["Certificado"] = filtered_courses_df["certificate_offered"].apply(lambda x: "✅" if x else "❌")
        else:
            display_courses_df["Certificado"] = "N/A" # Or "❌" or ""

        # Rename columns for final display
        rename_map = {
            "title": "Título",
            "institution": "Institución",
            "subject": "Tema",
            "language": "Idioma",
            "duration": "Duración",
            "start_date": "Fecha de Inicio",
            "fecha_adición": "Añadido",
            "Ver Curso": "Link"
            # Gratis and Certificado are already named correctly
        }
        display_courses_df.rename(columns=rename_map, inplace=True)

        # Ensure final column order, including only those present in display_courses_df
        final_column_order = [
            "Título", "Institución", "Tema", "Idioma", 
            "Duración", "Fecha de Inicio", "Añadido", 
            "Gratis", "Certificado", "Link"
        ]
        
        # Filter final_column_order to only include columns that actually exist in display_courses_df
        ordered_columns_present = [col for col in final_column_order if col in display_courses_df.columns]
        display_courses_df = display_courses_df[ordered_columns_present]
        
        st.markdown(display_courses_df.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.info("No hay cursos que coincidan con los filtros seleccionados.")

def display_udemy_courses(courses_df: pd.DataFrame):
    """
    Display Udemy courses
    
    Parameters
    ----------
    courses_df : pd.DataFrame
        DataFrame containing Udemy courses data
    """
    if courses_df.empty:
        st.warning("No hay cursos de Udemy disponibles.")
        return

    filtered_df = courses_df.copy()
    
    # Store original index to maintain order if needed, though less critical here without complex filtering
    # filtered_df = filtered_df.reset_index(drop=True) 
    # original_order = filtered_df.index.copy()
        
    if "scraped_at" in filtered_df.columns:
        filtered_df["scraped_at"] = pd.to_datetime(filtered_df["scraped_at"], errors='coerce')
        filtered_df["fecha_adición"] = filtered_df["scraped_at"].dt.strftime("%Y-%m-%d")
        # filtered_df = filtered_df.reindex(original_order) # if maintaining original order strictly
    else:
        # Ensure fecha_adición column exists for schema consistency
        filtered_df["fecha_adición"] = None 
            
    st.write(f"Mostrando {len(filtered_df)} cursos de Udemy")
        
    if not filtered_df.empty:
        # Select and prepare display columns
        cols_to_select = ["title"]
        if "fecha_adición" in filtered_df.columns:
             cols_to_select.append("fecha_adición")
        
        # Ensure 'url' is present for the link, even if not directly in cols_to_select yet
        if 'url' not in filtered_df.columns:
            st.error("La columna 'url' es necesaria y no está presente en los datos de Udemy.")
            return # Cannot create links

        display_df = filtered_df[cols_to_select + ['url']].copy() # Include URL for link creation

        display_df["Ver Curso"] = display_df["url"].apply(lambda x: make_clickable(x, "Ver Detalles"))
        
        # Rename columns for final display
        rename_map = {
            "title": "Título",
            "fecha_adición": "Añadido",
            "Ver Curso": "Link"
        }
        display_df.rename(columns=rename_map, inplace=True)
        
        # Final column order
        final_columns_ordered = ["Título"]
        if "Añadido" in display_df.columns:
            final_columns_ordered.append("Añadido")
        final_columns_ordered.append("Link")
        
        # Filter final_columns_ordered to only include columns that actually exist in display_df
        ordered_columns_present = [col for col in final_columns_ordered if col in display_df.columns]
        display_df = display_df[ordered_columns_present]

        st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        # This case might not be reached if the initial empty check for courses_df is effective
        st.info("No hay cursos de Udemy para mostrar (después de procesar).")