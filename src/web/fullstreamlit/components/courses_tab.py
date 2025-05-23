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
    # Card styling for courses
    courses_html = '<div class="courses-card">'
    courses_html += '<h2>Cursos de Coursera</h2>'

    if not courses_df.empty:
        # Use the original DataFrame to preserve JSON order - create a copy first
        filtered_courses_df = courses_df.copy()
        
        # Store original index to maintain order
        filtered_courses_df = filtered_courses_df.reset_index(drop=True)
        original_order = filtered_courses_df.index.copy()
        
        # Convert scraped_at to datetime if it exists (for display only, not sorting)
        if "scraped_at" in filtered_courses_df.columns:
            # Convert to datetime but preserve original order
            filtered_courses_df["scraped_at"] = pd.to_datetime(filtered_courses_df["scraped_at"], errors='coerce')
            
            # Format scraped_at for display
            filtered_courses_df["fecha_adición"] = filtered_courses_df["scraped_at"].dt.strftime("%Y-%m-%d")
            
            # Ensure we maintain the original order
            filtered_courses_df = filtered_courses_df.reindex(original_order)
        
        # Add text search for title and description
        search_term = st.text_input("Buscar cursos:", placeholder="Ingrese palabras clave...")
        if search_term:
            # Convert search term to lowercase for case-insensitive search
            search_term = search_term.lower()
            
            # Search in title
            title_mask = filtered_courses_df["title"].str.lower().str.contains(search_term, na=False)
            
            # Search in description if it exists
            if "description" in filtered_courses_df.columns:
                desc_mask = filtered_courses_df["description"].str.lower().str.contains(search_term, na=False)
                # Combine masks (title OR description)
                search_mask = title_mask | desc_mask
            else:
                search_mask = title_mask
            
            # Apply search filter
            filtered_courses_df = filtered_courses_df[search_mask]
            
            # Show how many results were found
            st.write(f"Se encontraron {len(filtered_courses_df)} cursos con '{search_term}'")
        
        # Create a row with two columns for filters
        col1, col2 = st.columns(2)
        
        # Add filters for subject and language
        with col1:
            if "subject" in filtered_courses_df.columns:
                # Get unique subjects, sorted alphabetically
                subjects = sorted(filtered_courses_df["subject"].dropna().unique().tolist())
                
                # Add an "All Subjects" option at the beginning
                subjects = ["Todos los temas"] + subjects
                
                selected_subject = st.selectbox("Filtrar por tema:", subjects)
                
                # Apply the filter if a specific subject is selected
                if selected_subject != "Todos los temas":
                    filtered_courses_df = filtered_courses_df[filtered_courses_df["subject"] == selected_subject]
        
        # Filter by language
        with col2:
            if "language" in filtered_courses_df.columns:
                # Get unique languages, sorted alphabetically
                languages = sorted(filtered_courses_df["language"].dropna().unique().tolist())
                
                # Add an "All Languages" option
                languages = ["Todos los idiomas"] + languages
                
                selected_language = st.selectbox("Filtrar por idioma:", languages)
                
                # Apply the filter if a specific language is selected
                if selected_language != "Todos los idiomas":
                    filtered_courses_df = filtered_courses_df[filtered_courses_df["language"] == selected_language]
        
        # Add option to show only free courses if that column exists
        if "is_free" in filtered_courses_df.columns:
            show_only_free = st.checkbox("Mostrar solo cursos gratuitos")
            if show_only_free:
                filtered_courses_df = filtered_courses_df[filtered_courses_df["is_free"] == True]
        
        # Display the number of courses after filtering
        st.write(f"Mostrando {len(filtered_courses_df)} cursos")
        
        # Select columns to display
        columns_to_display = ["title", "institution", "subject", "language", "duration", "start_date"]
        
        # Add scraped_at date to display columns if it exists
        if "fecha_adición" in filtered_courses_df.columns:
            columns_to_display.append("fecha_adición")
        
        # Make sure all required columns exist
        display_columns = [col for col in columns_to_display if col in filtered_courses_df.columns]
        display_courses_df = filtered_courses_df[display_columns].copy()
        
        # Add clickable link to course
        display_courses_df["Ver Curso"] = filtered_courses_df["url"].apply(
            lambda x: make_clickable(x, "Ver Detalles")
        )
        
        # Check for certificate information
        if "certificate_offered" in filtered_courses_df.columns:
            display_courses_df["Certificado"] = filtered_courses_df["certificate_offered"].apply(
                lambda x: "✅" if x else "❌"
            )
            
        # Check for free course information
        if "is_free" in filtered_courses_df.columns:
            display_courses_df["Gratis"] = filtered_courses_df["is_free"].apply(
                lambda x: "✅" if x else "❌"
            )
        
        # Rename columns for display
        column_mapping = {
            "title": "Título",
            "institution": "Institución",
            "subject": "Tema",
            "language": "Idioma",
            "duration": "Duración",
            "start_date": "Fecha de Inicio",
            "fecha_adición": "Añadido"
        }
        
        # Only rename columns that exist
        rename_cols = {k: v for k, v in column_mapping.items() if k in display_courses_df.columns}
        display_courses_df.rename(columns=rename_cols, inplace=True)
        
        # Generate HTML table
        courses_html += display_courses_df.to_html(escape=False, index=False)
    else:
        courses_html += '<p>No hay cursos de Coursera disponibles.</p>'

    # Close the card div
    courses_html += '</div>'
    st.markdown(courses_html, unsafe_allow_html=True)

def display_udemy_courses(courses_df: pd.DataFrame):
    """
    Display Udemy courses
    
    Parameters
    ----------
    courses_df : pd.DataFrame
        DataFrame containing Udemy courses data
    """
    # Card styling for Udemy courses
    courses_html = '<div class="courses-card">'
    courses_html += '<h2>Cursos de Udemy</h2>'

    if not courses_df.empty:
        filtered_df = courses_df.copy()
        
        # Store original index to maintain order
        filtered_df = filtered_df.reset_index(drop=True)
        original_order = filtered_df.index.copy()
        
        # Convert scraped_at to datetime for display
        if "scraped_at" in filtered_df.columns:
            filtered_df["scraped_at"] = pd.to_datetime(filtered_df["scraped_at"], errors='coerce')
            filtered_df["fecha_adición"] = filtered_df["scraped_at"].dt.strftime("%Y-%m-%d")
            
            # Maintain original order
            filtered_df = filtered_df.reindex(original_order)
            
        # Display number of courses
        st.write(f"Mostrando {len(filtered_df)} cursos de Udemy")
        
        # Select display columns
        display_df = filtered_df[["title", "fecha_adición", "url"]].copy()
        # Add clickable link
        display_df["Ver Curso"] = display_df["url"].apply(lambda x: make_clickable(x, "Ver Detalles"))
        # Rename columns
        display_df.rename(columns={"title": "Título", "fecha_adición": "Añadido"}, inplace=True)
        # Generate HTML table
        courses_html += display_df.to_html(escape=False, index=False)
    else:
        courses_html += '<p>No hay cursos de Udemy disponibles.</p>'

    courses_html += '</div>'
    st.markdown(courses_html, unsafe_allow_html=True) 