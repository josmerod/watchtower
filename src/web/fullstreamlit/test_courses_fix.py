"""
Test script to verify courses tab fixes.
Tests both Udemy file loading and course ordering.
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Add the project root to the path
from web.fullstreamlit.utils.data_service import DataService
from utils.logging import get_logger

def main():
    """Test courses functionality"""
    st.set_page_config(
        page_title="Courses Fix Test",
        page_icon="🎓",
        layout="wide"
    )
    
    st.title("🎓 Courses Fix Test")
    st.markdown("Test de correcciones en la carga de cursos y ordenamiento.")
    
    # Initialize components
    logger = get_logger("CoursesFixTest")
    data_service = DataService(logger)
    
    st.header("📊 Test de Carga de Cursos")
    
    if st.button("🔄 Cargar Datos de Cursos"):
        with st.spinner("Cargando datos de cursos..."):
            try:
                # Test direct file access
                st.subheader("🔍 Verificación de Archivos")
                
                # Check Udemy file
                udemy_file = data_service.data_dir / "udemy" / "udemy_courses.json"
                if udemy_file.exists():
                    st.success(f"✅ Archivo Udemy encontrado: {udemy_file}")
                    
                    # Get file size
                    size = udemy_file.stat().st_size
                    st.write(f"📦 Tamaño: {size // 1024} KB")
                else:
                    st.error(f"❌ Archivo Udemy NO encontrado: {udemy_file}")
                
                # Check Coursera file
                coursera_file = data_service.data_dir / "classcentral" / "coursera_courses.json"
                if coursera_file.exists():
                    st.success(f"✅ Archivo Coursera encontrado: {coursera_file}")
                    
                    # Get file size
                    size = coursera_file.stat().st_size
                    st.write(f"📦 Tamaño: {size // 1024} KB")
                else:
                    st.error(f"❌ Archivo Coursera NO encontrado: {coursera_file}")
                
                st.subheader("📚 Test de DataService")
                
                # Load courses data using DataService
                courses_data = data_service.get_courses_data()
                
                if courses_data:
                    st.success("✅ Datos cargados exitosamente!")
                    
                    # Show summary
                    for platform, df in courses_data.items():
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric(f"🎓 {platform.title()}", len(df))
                        
                        with col2:
                            if not df.empty:
                                # Check if original order is maintained
                                if 'scraped_at' in df.columns:
                                    st.write(f"📅 Primer curso: {df.iloc[0].get('title', 'Sin título')[:50]}...")
                                    st.write(f"📅 Último curso: {df.iloc[-1].get('title', 'Sin título')[:50]}...")
                                else:
                                    st.write(f"📄 Columnas: {', '.join(df.columns[:5])}...")
                
                    # Test ordering preservation
                    st.subheader("🔢 Test de Ordenamiento")
                    
                    for platform, df in courses_data.items():
                        if not df.empty and 'scraped_at' in df.columns:
                            st.write(f"**{platform.title()}:**")
                            
                            # Show first 5 courses with their scraped dates
                            preview_df = df.head(5)[['title', 'scraped_at']].copy()
                            preview_df['scraped_at'] = preview_df['scraped_at'].astype(str)
                            
                            st.dataframe(preview_df, use_container_width=True)
                            
                            # Check if dates are in descending order (newest first)
                            dates = df['scraped_at'].dropna()
                            if len(dates) > 1:
                                is_descending = dates.is_monotonic_decreasing
                                is_ascending = dates.is_monotonic_increasing
                                
                                if is_descending:
                                    st.info(f"📅 {platform.title()}: Ordenado por fecha (nuevo → viejo)")
                                elif is_ascending:
                                    st.warning(f"📅 {platform.title()}: Ordenado por fecha (viejo → nuevo)")
                                else:
                                    st.success(f"📅 {platform.title()}: Orden original preservado")
                else:
                    st.error("❌ No se pudieron cargar los datos de cursos")
                
            except Exception as e:
                st.error(f"❌ Error en el test: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
    # Manual file check
    st.header("🔍 Verificación Manual de Archivos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📁 Listar archivos Udemy"):
            udemy_dir = Path("data/udemy")
            if udemy_dir.exists():
                files = list(udemy_dir.glob("*.json"))
                st.write("Archivos JSON en data/udemy:")
                for file in files:
                    st.write(f"- {file.name}")
            else:
                st.error("Directorio data/udemy no encontrado")
    
    with col2:
        if st.button("📁 Listar archivos Coursera"):
            coursera_dir = Path("data/classcentral")
            if coursera_dir.exists():
                files = list(coursera_dir.glob("*.json"))
                st.write("Archivos JSON en data/classcentral:")
                for file in files:
                    st.write(f"- {file.name}")
            else:
                st.error("Directorio data/classcentral no encontrado")

if __name__ == "__main__":
    main() 