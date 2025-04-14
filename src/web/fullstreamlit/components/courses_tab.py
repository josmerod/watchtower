"""
Courses tab component for the Watchtower Streamlit application.
Displays courses from different platforms like Coursera, edX, etc.
"""

import streamlit as st
import pandas as pd
import json
import os
from src.web.fullstreamlit.utils.helpers import make_clickable
from typing import Dict, List, Optional, Any, Union

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
        
        # Try multiple paths to find the file
        coursera_file = None
        paths_to_try = [
            "data/classcentral/coursera_courses.json",
            "../../../data/classcentral/coursera_courses.json",
            os.path.abspath("data/classcentral/coursera_courses.json"),
            "C:/Users/josem/watchtower/data/classcentral/coursera_courses.json",
            # Additional paths with different working directory assumptions
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../../data/classcentral/coursera_courses.json"),
            os.path.join(os.getcwd(), "data/classcentral/coursera_courses.json"),
            os.path.join(os.getcwd(), "../../../data/classcentral/coursera_courses.json")
        ]
        
        if logger:
            logger.info(f"Current working directory: {os.getcwd()}")
            
        for path in paths_to_try:
            if os.path.exists(path):
                coursera_file = path
                if logger:
                    logger.info(f"Found coursera file at: {path}")
                break
        
        if coursera_file:
            try:
                with open(coursera_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Display successful load message directly to user
                st.success(f"¡Cargados {len(data)} cursos de Coursera directamente del archivo!")
                
                courses_data = {"coursera": pd.DataFrame(data)}
            except Exception as e:
                if logger:
                    logger.error(f"Error loading coursera data directly: {str(e)}")
                st.error(f"Error cargando datos: {str(e)}")
        else:
            if logger:
                logger.error("Could not find coursera_courses.json in any path")
            st.error("No se pudo encontrar el archivo de cursos de Coursera.")

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
        # Use the original DataFrame to preserve JSON order
        filtered_courses_df = courses_df.copy()
        
        # Convert scraped_at to datetime if it exists (for display only, not sorting)
        if "scraped_at" in filtered_courses_df.columns:
            # Convert to datetime but don't sort
            filtered_courses_df["scraped_at"] = pd.to_datetime(filtered_courses_df["scraped_at"])
            
            # Format scraped_at for display
            filtered_courses_df["fecha_adición"] = filtered_courses_df["scraped_at"].dt.strftime("%Y-%m-%d")
        
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