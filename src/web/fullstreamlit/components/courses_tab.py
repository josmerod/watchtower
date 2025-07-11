"""
Courses tab component for the Watchtower Streamlit application.
Displays online course data from various platforms like Coursera and Udemy.
"""

import streamlit as st
import pandas as pd
import json
import os
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

def safe_json_load(file_path: str) -> List[Dict]:
    """Safely load JSON file with proper error handling and encoding."""
    if not os.path.exists(file_path):
        return []
    
    try:
        # Try UTF-8 first
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except UnicodeDecodeError:
        try:
            # Try with different encoding if UTF-8 fails
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error reading file {file_path} with encoding fallback: {str(e)}")
            return []
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON in file {file_path}: {str(e)}")
        return []
    except Exception as e:
        st.error(f"Unexpected error reading file {file_path}: {str(e)}")
        return []

def load_coursera_courses_from_multiple_paths():
    """Try loading Coursera courses from multiple potential paths"""
    return safe_json_load(COURSERA_FILE)

def load_udemy_courses_from_multiple_paths():
    """Try loading Udemy courses from multiple potential paths"""
    return safe_json_load(UDEMY_FILE)

def validate_course_data(courses_data: List[Dict], platform: str) -> List[Dict]:
    """Validate and clean course data."""
    if not courses_data:
        return []
    
    validated_courses = []
    for course in courses_data:
        # Ensure required fields exist
        if not isinstance(course, dict):
            continue
            
        # Ensure title and url exist (minimum requirements)
        if 'title' not in course or 'url' not in course:
            continue
            
        # Clean up data types
        cleaned_course = course.copy()
        
        # Handle boolean fields
        for bool_field in ['is_free', 'certificate_offered']:
            if bool_field in cleaned_course:
                if isinstance(cleaned_course[bool_field], str):
                    cleaned_course[bool_field] = cleaned_course[bool_field].lower() in ['true', '1', 'yes']
                elif not isinstance(cleaned_course[bool_field], bool):
                    cleaned_course[bool_field] = False
        
        # Handle missing fields with defaults
        if 'scraped_at' not in cleaned_course:
            cleaned_course['scraped_at'] = None
        
        validated_courses.append(cleaned_course)
    
    return validated_courses

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
        
        # Load Coursera data
        coursera_json = load_coursera_courses_from_multiple_paths()
        if coursera_json:
            try:
                # Validate data before creating DataFrame
                validated_coursera = validate_course_data(coursera_json, "coursera")
                if validated_coursera:
                    st.success(f"¡Cargados {len(validated_coursera)} cursos de Coursera directamente del archivo!")
                    loaded_data["coursera"] = pd.DataFrame(validated_coursera)
                else:
                    st.warning("Los datos de Coursera requieren validación.")
            except Exception as e:
                if logger:
                    logger.error(f"Error loading Coursera data directly: {str(e)}")
                st.error(f"Error cargando datos de Coursera: {str(e)}")
        else:
            if logger:
                logger.error("Could not find coursera_courses.json in any path")
            st.info("No se encontraron cursos de Coursera.")
        
        # Load Udemy data
        udemy_json = load_udemy_courses_from_multiple_paths()
        if udemy_json:
            try:
                # Validate data before creating DataFrame
                validated_udemy = validate_course_data(udemy_json, "udemy")
                if validated_udemy:
                    st.success(f"¡Cargados {len(validated_udemy)} cursos de Udemy directamente del archivo!")
                    loaded_data["udemy"] = pd.DataFrame(validated_udemy)
                else:
                    st.warning("Los datos de Udemy requieren validación.")
            except Exception as e:
                if logger:
                    logger.error(f"Error loading Udemy data directly: {str(e)}")
                st.error(f"Error cargando datos de Udemy: {str(e)}")
        else:
            if logger:
                logger.error("Could not find udemy_courses.json in any path")
            st.info("No se encontraron cursos de Udemy.")
        
        courses_data = loaded_data

    # Check if all dataframes are empty after emergency loading
    if not courses_data or all(df.empty for df in courses_data.values()):
        if logger:
            logger.warning("No course data available to display.")
        st.warning("No hay datos de cursos disponibles para mostrar.")
        return  # Exit if no data

    # Create tabs for different course platforms
    available_platforms = []
    for platform, df in courses_data.items():
        if not df.empty:
            available_platforms.append(platform.capitalize())

    if not available_platforms:
        st.warning("No hay datos de cursos válidos para mostrar en las pestañas.")
        return

    tabs = st.tabs(available_platforms)
    
    # Display content within each tab
    for i, platform in enumerate(available_platforms):
        with tabs[i]:
            platform_key = platform.lower()
            if platform_key == "coursera" and platform_key in courses_data:
                display_coursera_courses(courses_data[platform_key])
            elif platform_key == "udemy" and platform_key in courses_data:
                display_udemy_courses(courses_data[platform_key])

def safe_datetime_conversion(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
    """Safely convert datetime column with error handling."""
    if date_column not in df.columns:
        return df
    
    try:
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
        return df
    except Exception as e:
        st.warning(f"Error converting {date_column} to datetime: {str(e)}")
        return df

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

    # Create a working copy
    try:
        filtered_courses_df = courses_df.copy()
        
        # Safe datetime conversion
        filtered_courses_df = safe_datetime_conversion(filtered_courses_df, "scraped_at")
        
        # Sort by scraped_at date in descending order (newest first)
        if "scraped_at" in filtered_courses_df.columns:
            try:
                # Sort by scraped_at, putting NaT values at the end
                filtered_courses_df = filtered_courses_df.sort_values(
                    by="scraped_at", ascending=False, na_position='last'
                )
                st.info(f"📅 Cursos ordenados por fecha de adición (más recientes primero)")
            except Exception as e:
                st.warning(f"No se pudo ordenar por fecha: {str(e)}")
        
        # Create fecha_adición column safely
        if "scraped_at" in filtered_courses_df.columns:
            try:
                filtered_courses_df["fecha_adición"] = filtered_courses_df["scraped_at"].dt.strftime("%Y-%m-%d")
            except Exception:
                filtered_courses_df["fecha_adición"] = "N/A"
        else:
            filtered_courses_df["fecha_adición"] = "N/A"
    except Exception as e:
        st.error(f"Error procesando datos de Coursera: {str(e)}")
        return

    # Filters
    with st.expander("Filtros y Opciones para Coursera", expanded=True):
        search_term = st.text_input("Buscar cursos:", placeholder="Ingrese palabras clave...", key="coursera_search")
        
        if search_term:
            search_term_lower = search_term.lower()
            try:
                title_mask = filtered_courses_df["title"].str.lower().str.contains(search_term_lower, na=False)
                desc_mask = pd.Series([False] * len(filtered_courses_df))
                if "description" in filtered_courses_df.columns:
                    desc_mask = filtered_courses_df["description"].str.lower().str.contains(search_term_lower, na=False)
                search_mask = title_mask | desc_mask
                filtered_courses_df = filtered_courses_df[search_mask]
                
                # Re-sort after filtering to maintain newest-first order
                if "scraped_at" in filtered_courses_df.columns and not filtered_courses_df.empty:
                    filtered_courses_df = filtered_courses_df.sort_values(
                        by="scraped_at", ascending=False, na_position='last'
                    )
            except Exception as e:
                st.warning(f"Error en búsqueda: {str(e)}")

        col1, col2 = st.columns(2)
        with col1:
            if "subject" in filtered_courses_df.columns:
                try:
                    subjects = sorted(filtered_courses_df["subject"].dropna().unique().tolist())
                    subjects = ["Todos los temas"] + subjects
                    selected_subject = st.selectbox("Filtrar por tema:", subjects, key="coursera_subject")
                    if selected_subject != "Todos los temas":
                        filtered_courses_df = filtered_courses_df[filtered_courses_df["subject"] == selected_subject]
                        
                        # Re-sort after filtering to maintain newest-first order
                        if "scraped_at" in filtered_courses_df.columns and not filtered_courses_df.empty:
                            filtered_courses_df = filtered_courses_df.sort_values(
                                by="scraped_at", ascending=False, na_position='last'
                            )
                except Exception as e:
                    st.warning(f"Error en filtro por tema: {str(e)}")
        
        with col2:
            if "language" in filtered_courses_df.columns:
                try:
                    languages = sorted(filtered_courses_df["language"].dropna().unique().tolist())
                    languages = ["Todos los idiomas"] + languages
                    selected_language = st.selectbox("Filtrar por idioma:", languages, key="coursera_language")
                    if selected_language != "Todos los idiomas":
                        filtered_courses_df = filtered_courses_df[filtered_courses_df["language"] == selected_language]
                        
                        # Re-sort after filtering to maintain newest-first order
                        if "scraped_at" in filtered_courses_df.columns and not filtered_courses_df.empty:
                            filtered_courses_df = filtered_courses_df.sort_values(
                                by="scraped_at", ascending=False, na_position='last'
                            )
                except Exception as e:
                    st.warning(f"Error en filtro por idioma: {str(e)}")

        if "is_free" in filtered_courses_df.columns:
            show_only_free = st.checkbox("Mostrar solo cursos gratuitos", key="coursera_free_checkbox")
            if show_only_free:
                try:
                    filtered_courses_df = filtered_courses_df[filtered_courses_df["is_free"] == True]
                    
                    # Re-sort after filtering to maintain newest-first order
                    if "scraped_at" in filtered_courses_df.columns and not filtered_courses_df.empty:
                        filtered_courses_df = filtered_courses_df.sort_values(
                            by="scraped_at", ascending=False, na_position='last'
                        )
                except Exception as e:
                    st.warning(f"Error en filtro de cursos gratuitos: {str(e)}")

    st.write(f"Mostrando {len(filtered_courses_df)} cursos")

    if not filtered_courses_df.empty:
        try:
            # Ensure 'url' is present for the link column
            if 'url' not in filtered_courses_df.columns:
                st.error("La columna 'url' es necesaria y no está presente en los datos de Coursera.")
                return

            df_for_editor = filtered_courses_df.copy()

            # Safe column renaming
            rename_map_editor = {
                "title": "Título",
                "institution": "Institución", 
                "subject": "Tema",
                "language": "Idioma",
                "duration": "Duración",
                "start_date": "Fecha de Inicio",
                "fecha_adición": "Añadido",
                "is_free": "Gratis",
                "certificate_offered": "Certificado",
                "url": "URL_Enlace"
            }

            # Only rename columns that exist
            existing_columns = {k: v for k, v in rename_map_editor.items() if k in df_for_editor.columns}
            df_for_editor.rename(columns=existing_columns, inplace=True)

            # Define column order, but only use existing columns
            final_ordered_columns = [
                "Título", "Institución", "Tema", "Idioma",
                "Duración", "Fecha de Inicio", "Añadido",
                "Gratis", "Certificado", "URL_Enlace"
            ]
            
            available_columns = [col for col in final_ordered_columns if col in df_for_editor.columns]
            df_for_editor = df_for_editor[available_columns]

            # Create column config dynamically
            column_config = {}
            for col in available_columns:
                if col == "URL_Enlace":
                    column_config[col] = st.column_config.LinkColumn(
                        label="Enlace", display_text="Ver Detalles", width="medium"
                    )
                elif col in ["Gratis", "Certificado"]:
                    column_config[col] = st.column_config.CheckboxColumn(width="small")
                else:
                    column_config[col] = st.column_config.TextColumn(width="medium")

            st.data_editor(
                df_for_editor,
                column_config=column_config,
                disabled=True,
                hide_index=True,
                use_container_width=True
            )

            # Download buttons
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                csv_data = df_for_editor.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar CSV (Coursera)",
                    data=csv_data,
                    file_name="coursera_courses_data.csv",
                    mime='text/csv',
                    key="csv_download_coursera"
                )
            with col2:
                json_data = df_for_editor.to_json(orient='records', indent=2).encode('utf-8')
                st.download_button(
                    label="📥 Descargar JSON (Coursera)",
                    data=json_data,
                    file_name="coursera_courses_data.json",
                    mime='application/json',
                    key="json_download_coursera"
                )
        except Exception as e:
            st.error(f"Error mostrando datos de Coursera: {str(e)}")
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

    try:
        filtered_df = courses_df.copy()

        # Safe datetime conversion
        filtered_df = safe_datetime_conversion(filtered_df, "scraped_at")
        
        # Sort by scraped_at date in descending order (newest first)
        if "scraped_at" in filtered_df.columns:
            try:
                # Sort by scraped_at, putting NaT values at the end
                filtered_df = filtered_df.sort_values(
                    by="scraped_at", ascending=False, na_position='last'
                )
                st.info(f"📅 Cursos ordenados por fecha de adición (más recientes primero)")
            except Exception as e:
                st.warning(f"No se pudo ordenar por fecha: {str(e)}")
        
        # Create fecha_adición column safely
        if "scraped_at" in filtered_df.columns:
            try:
                filtered_df["fecha_adición"] = filtered_df["scraped_at"].dt.strftime("%Y-%m-%d")
            except Exception:
                filtered_df["fecha_adición"] = "N/A"
        else:
            filtered_df["fecha_adición"] = "N/A"
            
        st.write(f"Mostrando {len(filtered_df)} cursos de Udemy")
        
        if not filtered_df.empty:
            # Ensure 'url' is present
            if 'url' not in filtered_df.columns:
                st.error("La columna 'url' es necesaria y no está presente en los datos de Udemy.")
                return

            df_for_editor = filtered_df.copy()

            # Safe column renaming
            rename_map_editor = {
                "title": "Título",
                "fecha_adición": "Añadido",
                "url": "URL_Enlace"
            }

            existing_columns = {k: v for k, v in rename_map_editor.items() if k in df_for_editor.columns}
            df_for_editor.rename(columns=existing_columns, inplace=True)

            # Column order
            final_ordered_columns = ["Título", "Añadido", "URL_Enlace"]
            available_columns = [col for col in final_ordered_columns if col in df_for_editor.columns]
            df_for_editor = df_for_editor[available_columns]

            # Create column config
            column_config = {}
            for col in available_columns:
                if col == "URL_Enlace":
                    column_config[col] = st.column_config.LinkColumn(
                        label="Enlace", display_text="Ver Detalles", width="medium"
                    )
                else:
                    column_config[col] = st.column_config.TextColumn(width="large" if col == "Título" else "medium")

            st.data_editor(
                df_for_editor,
                column_config=column_config,
                disabled=True,
                hide_index=True,
                use_container_width=True
            )

            # Download buttons
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                csv_data = df_for_editor.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar CSV (Udemy)",
                    data=csv_data,
                    file_name="udemy_courses_data.csv",
                    mime='text/csv',
                    key="csv_download_udemy"
                )
            with col2:
                json_data = df_for_editor.to_json(orient='records', indent=2).encode('utf-8')
                st.download_button(
                    label="📥 Descargar JSON (Udemy)",
                    data=json_data,
                    file_name="udemy_courses_data.json",
                    mime='application/json',
                    key="json_download_udemy"
                )
        else:
            st.info("No hay cursos de Udemy para mostrar.")
    except Exception as e:
        st.error(f"Error procesando datos de Udemy: {str(e)}")