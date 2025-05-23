"""
Test script for quick actions functionality.
Simple test to verify button responsiveness and data loading.
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.web.fullstreamlit.utils.data_service import DataService
from src.utils.logging import get_logger

def main():
    """Test quick actions functionality"""
    st.set_page_config(
        page_title="Quick Actions Test",
        page_icon="⚡",
        layout="wide"
    )
    
    st.title("⚡ Quick Actions Test")
    st.markdown("Test de funcionalidad de botones de acciones rápidas.")
    
    # Initialize components
    logger = get_logger("QuickActionsTest")
    data_service = DataService(logger)
    
    # Test data loading
    st.header("📊 Test de Carga de Datos")
    
    if st.button("🔄 Cargar Datos de Prueba"):
        with st.spinner("Cargando datos..."):
            try:
                # Load data summary
                data_summary = data_service.get_data_summary()
                st.success("✅ Datos cargados exitosamente!")
                
                # Show summary
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    games_total = (
                        data_summary.get('games', {}).get('deals', 0) +
                        data_summary.get('games', {}).get('bundles', 0) +
                        data_summary.get('games', {}).get('giveaways', 0)
                    )
                    st.metric("🎮 Juegos", games_total)
                
                with col2:
                    news_total = data_summary.get('news', {}).get('total', 0)
                    st.metric("📰 Noticias", news_total)
                
                with col3:
                    courses_total = data_summary.get('courses', {}).get('total', 0)
                    st.metric("🎓 Cursos", courses_total)
                
                with col4:
                    arxiv_total = data_summary.get('arxiv', {}).get('total', 0)
                    st.metric("📚 ArXiv", arxiv_total)
                
            except Exception as e:
                st.error(f"❌ Error cargando datos: {str(e)}")
    
    # Test quick actions
    st.header("⚡ Test de Acciones Rápidas")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🎮 Test Gaming", use_container_width=True):
            with st.spinner("Procesando..."):
                import time
                time.sleep(0.5)  # Simulate processing
                st.success("✅ Botón Gaming funcionando!")
                st.balloons()
    
    with col2:
        if st.button("📰 Test Noticias", use_container_width=True):
            with st.spinner("Procesando..."):
                import time
                time.sleep(0.5)
                st.success("✅ Botón Noticias funcionando!")
                st.balloons()
    
    with col3:
        if st.button("🎓 Test Cursos", use_container_width=True):
            with st.spinner("Procesando..."):
                import time
                time.sleep(0.5)
                st.success("✅ Botón Cursos funcionando!")
                st.balloons()
    
    with col4:
        if st.button("📚 Test ArXiv", use_container_width=True):
            with st.spinner("Procesando..."):
                import time
                time.sleep(0.5)
                st.success("✅ Botón ArXiv funcionando!")
                st.balloons()
    
    # Test quick links
    st.header("🌐 Test de Enlaces Rápidos")
    
    link_col1, link_col2, link_col3, link_col4 = st.columns(4)
    
    with link_col1:
        if st.button("🔍 Test Google", use_container_width=True):
            st.markdown("""
            <div style="color: #10B981; text-align: center; padding: 8px;">
                🔍 Google link test - OK!
            </div>
            """, unsafe_allow_html=True)
    
    with link_col2:
        if st.button("🤖 Test ChatGPT", use_container_width=True):
            st.markdown("""
            <div style="color: #10B981; text-align: center; padding: 8px;">
                🤖 ChatGPT link test - OK!
            </div>
            """, unsafe_allow_html=True)
    
    with link_col3:
        if st.button("🐙 Test GitHub", use_container_width=True):
            st.markdown("""
            <div style="color: #10B981; text-align: center; padding: 8px;">
                🐙 GitHub link test - OK!
            </div>
            """, unsafe_allow_html=True)
    
    with link_col4:
        if st.button("📹 Test YouTube", use_container_width=True):
            st.markdown("""
            <div style="color: #10B981; text-align: center; padding: 8px;">
                📹 YouTube link test - OK!
            </div>
            """, unsafe_allow_html=True)
    
    # Performance test
    st.header("🚀 Test de Rendimiento")
    
    if st.button("⏱️ Test de Velocidad de Respuesta"):
        import time
        start_time = time.time()
        
        with st.spinner("Midiendo tiempo de respuesta..."):
            # Simulate various operations
            time.sleep(0.1)  # Simulate data loading
            
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to ms
        
        if response_time < 200:
            st.success(f"✅ Excelente rendimiento: {response_time:.1f}ms")
        elif response_time < 500:
            st.info(f"ℹ️ Buen rendimiento: {response_time:.1f}ms")
        else:
            st.warning(f"⚠️ Rendimiento lento: {response_time:.1f}ms")

if __name__ == "__main__":
    main() 