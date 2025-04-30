"""
Admin tab component for the Watchtower Streamlit application.
Provides administrative functionality for the application.
"""

import streamlit as st
import subprocess
import os
import json
from typing import Dict, List, Optional
import toml


# Define videos data directory
VIDEOS_DATA_DIR = "../../../data/youtube"

# Define available themes
THEMES: Dict[str, Dict[str, str]] = {
    "Default": {
        "primaryColor": "#FF4B4B",
        "backgroundColor": "#1E1E2E",
        "secondaryBackgroundColor": "#2D2B55",
        "textColor": "#E2E8F0",
        "font": "sans serif",
    },
    "Dark": {
        "primaryColor": "#A37FFF",
        "backgroundColor": "#0E1117",
        "secondaryBackgroundColor": "#262730",
        "textColor": "#FAFAFA",
        "font": "sans serif",
    },
    "Blue": {
        "primaryColor": "#1E88E5",
        "backgroundColor": "#FFFFFF",
        "secondaryBackgroundColor": "#E3F2FD",
        "textColor": "#262730",
        "font": "sans serif",
    },
    "Green": {
        "primaryColor": "#4CAF50",
        "backgroundColor": "#FFFFFF",
        "secondaryBackgroundColor": "#E8F5E9",
        "textColor": "#262730",
        "font": "sans serif",
    },
}


def update_theme_config(theme_name: str) -> bool:
    """
    Update the Streamlit config.toml file with the selected theme.
    
    Args:
        theme_name: Name of the theme to apply
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Define path to config.toml relative to the application
        config_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            "../../../../.streamlit/config.toml"
        ))
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Load existing config if it exists
        if os.path.exists(config_path):
            config = toml.load(config_path)
        else:
            config = {}
        
        # Make sure theme section exists
        if "theme" not in config:
            config["theme"] = {}
        
        # Update theme settings
        theme_settings = THEMES[theme_name]
        for key, value in theme_settings.items():
            config["theme"][key] = value
        
        # Write updated config
        with open(config_path, "w") as f:
            toml.dump(config, f)
        
        return True
    except Exception as e:
        st.error(f"Error updating theme: {str(e)}")
        return False


def render(logger=None):
    """Render the admin tab"""
    st.header("⚙️ Admin Panel")

    st.markdown(
        """
    <div class="card">
        <h3>Panel de Administración</h3>
        <p>Esta sección permite ejecutar tareas de administración del sistema.</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Theme selection section
    st.subheader("🎨 Selección de Tema")
    
    # Initialize theme in session state if not already there
    if "theme" not in st.session_state:
        st.session_state.theme = "Default"
    
    # Theme selection dropdown
    selected_theme = st.selectbox(
        "Seleccionar tema",
        options=list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.theme),
        help="Selecciona un tema para personalizar la apariencia de la aplicación"
    )
    
    # Apply theme button
    if st.button("Aplicar tema"):
        st.session_state.theme = selected_theme
        
        # Update config.toml with new theme
        if update_theme_config(selected_theme):
            st.success(f"Tema '{selected_theme}' aplicado correctamente. Reinicia la aplicación para ver los cambios.")
            
            # Create a restart message with instructions
            st.info("""
            Para ver los cambios, debes reiniciar la aplicación:
            1. Detén el servidor de Streamlit (Ctrl+C en la terminal)
            2. Inicia nuevamente la aplicación
            """)
        else:
            st.error(f"No se pudo aplicar el tema '{selected_theme}'")
    
    # Show a preview of the selected theme
    st.markdown("### Vista previa del tema")
    theme_preview = THEMES[selected_theme]
    preview_html = f"""
    <div style="padding: 10px; border-radius: 5px; background-color: {theme_preview["backgroundColor"]}; color: {theme_preview["textColor"]};">
        <h4 style="color: {theme_preview["primaryColor"]};">Título de ejemplo</h4>
        <p>Este es un ejemplo de cómo se verá el texto con el tema seleccionado.</p>
        <div style="background-color: {theme_preview["secondaryBackgroundColor"]}; padding: 5px; border-radius: 3px;">
            <p>Este es un ejemplo de fondo secundario.</p>
        </div>
    </div>
    """
    st.markdown(preview_html, unsafe_allow_html=True)

    # Existing functionality
    st.subheader("📊 Herramientas de Administración")
    
    if st.button("Ejecutar todos los scrapers"):
        try:
            st.info("Ejecutando scrapers...")
            # Run all scrapers
            scripts = [
                "../../../src/etl/games/games_get_deals.py",
                "../../../src/etl/news/news_get_futuretools.py",
                "../../../src/etl/news/news_get_ycombinator.py",
                "../../../src/etl/news/news_get_genai_medium.py",
                "../../../src/etl/news/news_get_planesvalencia.py",
                "../../../src/etl/news/news_get_gooddevs.py",
                "../../../src/etl/news/news_get_bensbites.py",
                "../../../src/etl/goldigging/goldigging_coursera_courses.py",
                
            ]

            for script in scripts:
                subprocess.run(["python3", script])

            st.success("Todos los scrapers ejecutados correctamente")
            st.rerun()
        except Exception as e:
            st.error(f"Error al ejecutar los scrapers: {str(e)}")

    # Add section to scan YouTube directories
    st.subheader("Actualización de videos de YouTube")

    # Get available YouTube categories
    youtube_categories = [
        d
        for d in os.listdir(VIDEOS_DATA_DIR)
        if os.path.isdir(os.path.join(VIDEOS_DATA_DIR, d))
    ]

    # Option to update all channels
    if st.button("Actualizar todos los canales de YouTube"):
        try:
            st.info("Ejecutando actualización de videos...")
            # Get all category directories
            categories = youtube_categories

            success_count = 0
            for category in categories:
                try:
                    script_path = (
                        f"../../../src/etl/goldigging/goldigging_youtube_posts.py"
                    )
                    subprocess.run(["python3", script_path, "--category", category])
                    success_count += 1
                except Exception as category_e:
                    st.warning(
                        f"Error actualizando categoría {category}: {str(category_e)}"
                    )

            st.success(
                f"Actualizadas {success_count} de {len(categories)} categorías correctamente"
            )
            st.rerun()
        except Exception as e:
            st.error(f"Error al actualizar videos: {str(e)}")

    # Option to update specific channels
    st.subheader("Actualizar categoría específica")

    # Select a category to update
    selected_category = st.selectbox(
        "Seleccionar categoría",
        options=youtube_categories,
        help="Selecciona una categoría de videos para actualizar",
    )

    if st.button("Actualizar categoría seleccionada"):
        try:
            st.info(f"Actualizando videos de la categoría: {selected_category}")
            script_path = f"../../../src/etl/youtube/youtube_get_videos.py"
            result = subprocess.run(
                ["python3", script_path, "--category", selected_category],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                st.success(f"Categoría {selected_category} actualizada correctamente")
                st.text(result.stdout)
            else:
                st.error(f"Error al actualizar la categoría {selected_category}")
                st.text(result.stderr)
            st.rerun()
        except Exception as e:
            st.error(f"Error al actualizar videos: {str(e)}")
