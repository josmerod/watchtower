"""
Admin tab component for the Watchtower Streamlit application.
Provides administrative functionality for the application.
"""

import streamlit as st
import subprocess
import os

# Define videos data directory
VIDEOS_DATA_DIR = "../../../data/youtube"

def render(logger=None):
    """Render the admin tab"""
    st.header("⚙️ Admin Panel")
    
    st.markdown("""
    <div class="card">
        <h3>Panel de Administración</h3>
        <p>Esta sección permite ejecutar tareas de administración del sistema.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Ejecutar todos los scrapers"):
        try:
            st.info("Ejecutando scrapers...")
            # Run all scrapers
            scripts = [
                "../../../src/etl/games/games_get_deals.py",
                "../../../src/etl/news/news_get_futuretools.py",
                "../../../src/etl/news/news_get_ycombinator.py",
                "../../../src/etl/news/news_get_genai_medium.py",
                "../../../src/etl/news/news_get_bensbites.py"
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
    youtube_categories = [d for d in os.listdir(VIDEOS_DATA_DIR) 
                        if os.path.isdir(os.path.join(VIDEOS_DATA_DIR, d))]
    
    # Option to update all channels
    if st.button("Actualizar todos los canales de YouTube"):
        try:
            st.info("Ejecutando actualización de videos...")
            # Get all category directories
            categories = youtube_categories
            
            success_count = 0
            for category in categories:
                try:
                    script_path = f"../../../src/etl/youtube/youtube_get_videos.py"
                    subprocess.run(["python3", script_path, "--category", category])
                    success_count += 1
                except Exception as category_e:
                    st.warning(f"Error actualizando categoría {category}: {str(category_e)}")
            
            st.success(f"Actualizadas {success_count} de {len(categories)} categorías correctamente")
            st.rerun()
        except Exception as e:
            st.error(f"Error al actualizar videos: {str(e)}")
    
    # Option to update specific channels
    st.subheader("Actualizar categoría específica")
    
    # Select a category to update
    selected_category = st.selectbox(
        "Seleccionar categoría",
        options=youtube_categories,
        help="Selecciona una categoría de videos para actualizar"
    )
    
    if st.button("Actualizar categoría seleccionada"):
        try:
            st.info(f"Actualizando videos de la categoría: {selected_category}")
            script_path = f"../../../src/etl/youtube/youtube_get_videos.py"
            result = subprocess.run(
                ["python3", script_path, "--category", selected_category],
                capture_output=True,
                text=True
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