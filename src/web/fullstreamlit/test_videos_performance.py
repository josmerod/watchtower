"""
Performance test script for the optimized videos tab.
Measures loading times, rendering performance, and memory usage.
"""

import streamlit as st
import sys
import os
import time
from pathlib import Path
import psutil
import gc

# Add the project root to the path
from src.web.fullstreamlit.utils.data_service import DataService
from src.utils.logging import get_logger

def measure_memory():
    """Get current memory usage"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

def main():
    """Test videos performance"""
    st.set_page_config(
        page_title="Videos Performance Test",
        page_icon="📺",
        layout="wide"
    )
    
    st.title("📺 Videos Performance Test")
    st.markdown("Test de rendimiento para la pestaña de videos optimizada.")
    
    # Initialize components
    logger = get_logger("VideosPerformanceTest")
    data_service = DataService(logger)
    
    st.header("🚀 Test de Rendimiento")
    
    if st.button("⏱️ Ejecutar Test de Performance"):
        performance_results = {}
        
        # Memory before
        memory_before = measure_memory()
        st.write(f"💾 Memoria inicial: {memory_before:.1f} MB")
        
        # Test 1: Data Service Loading
        st.subheader("📊 Test 1: Carga de Datos")
        
        start_time = time.time()
        videos_data = data_service.get_videos_data()
        video_categories = data_service.get_video_categories()
        data_load_time = time.time() - start_time
        
        performance_results['data_load_time'] = data_load_time
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("⏱️ Tiempo de Carga", f"{data_load_time:.3f}s")
        with col2:
            st.metric("📁 Categorías", len(video_categories))
        with col3:
            total_videos = sum(len(df) for df in videos_data.values())
            st.metric("📺 Videos Totales", total_videos)
        
        # Memory after data loading
        memory_after_data = measure_memory()
        st.write(f"💾 Memoria después de cargar datos: {memory_after_data:.1f} MB (+{memory_after_data - memory_before:.1f} MB)")
        
        # Test 2: Category Processing
        st.subheader("🏷️ Test 2: Procesamiento de Categorías")
        
        if videos_data:
            start_time = time.time()
            
            largest_category = None
            largest_size = 0
            
            for category, df in videos_data.items():
                if len(df) > largest_size:
                    largest_size = len(df)
                    largest_category = category
            
            category_process_time = time.time() - start_time
            performance_results['category_process_time'] = category_process_time
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("⏱️ Tiempo de Procesamiento", f"{category_process_time:.3f}s")
            with col2:
                st.metric("📊 Categoría más Grande", f"{largest_category}: {largest_size}")
        
        # Test 3: Filtering Performance
        st.subheader("🔍 Test 3: Rendimiento de Filtros")
        
        if videos_data and largest_category:
            test_df = videos_data[largest_category].copy()
            
            # Test search filtering
            start_time = time.time()
            from src.web.fullstreamlit.components.videos_tab import filter_videos_by_search
            filtered_search = filter_videos_by_search(test_df, "test")
            search_filter_time = time.time() - start_time
            
            # Test date filtering  
            start_time = time.time()
            from src.web.fullstreamlit.components.videos_tab import filter_videos_by_date_range
            filtered_date = filter_videos_by_date_range(test_df, 30)
            date_filter_time = time.time() - start_time
            
            # Test pagination
            start_time = time.time()
            from src.web.fullstreamlit.components.videos_tab import paginate_dataframe
            paginated, total_pages, total_items = paginate_dataframe(test_df, 24, 1)
            pagination_time = time.time() - start_time
            
            performance_results.update({
                'search_filter_time': search_filter_time,
                'date_filter_time': date_filter_time,
                'pagination_time': pagination_time
            })
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🔍 Filtro Búsqueda", f"{search_filter_time:.3f}s")
            with col2:
                st.metric("📅 Filtro Fecha", f"{date_filter_time:.3f}s")
            with col3:
                st.metric("📄 Paginación", f"{pagination_time:.3f}s")
        
        # Test 4: HTML Rendering
        st.subheader("🖼️ Test 4: Generación de HTML")
        
        if videos_data and largest_category:
            test_df = videos_data[largest_category].head(50)  # Test with 50 videos
            
            start_time = time.time()
            from src.web.fullstreamlit.components.videos_tab import render_video_card_optimized
            import pandas as pd
            
            html_parts = []
            for _, video in test_df.iterrows():
                html_parts.append(render_video_card_optimized(video))
            
            html_render_time = time.time() - start_time
            performance_results['html_render_time'] = html_render_time
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🖼️ Tiempo Renderizado", f"{html_render_time:.3f}s")
            with col2:
                st.metric("📄 HTML Generado", f"{len(html_parts)} cards")
        
        # Memory after all operations
        memory_final = measure_memory()
        st.write(f"💾 Memoria final: {memory_final:.1f} MB (+{memory_final - memory_before:.1f} MB total)")
        
        # Performance Summary
        st.subheader("📊 Resumen de Rendimiento")
        
        total_time = sum(performance_results.values())
        
        # Create performance chart data
        import pandas as pd
        perf_df = pd.DataFrame([
            {"Operación": "Carga de Datos", "Tiempo (s)": performance_results.get('data_load_time', 0)},
            {"Operación": "Procesamiento", "Tiempo (s)": performance_results.get('category_process_time', 0)},
            {"Operación": "Filtro Búsqueda", "Tiempo (s)": performance_results.get('search_filter_time', 0)},
            {"Operación": "Filtro Fecha", "Tiempo (s)": performance_results.get('date_filter_time', 0)},
            {"Operación": "Paginación", "Tiempo (s)": performance_results.get('pagination_time', 0)},
            {"Operación": "Renderizado HTML", "Tiempo (s)": performance_results.get('html_render_time', 0)}
        ])
        
        st.dataframe(perf_df, use_container_width=True)
        
        # Performance assessment
        st.subheader("📈 Evaluación de Rendimiento")
        
        if total_time < 0.5:
            st.success(f"🟢 **Excelente rendimiento**: {total_time:.3f}s total")
        elif total_time < 1.0:
            st.info(f"🟡 **Buen rendimiento**: {total_time:.3f}s total")
        else:
            st.warning(f"🔴 **Rendimiento a mejorar**: {total_time:.3f}s total")
        
        # Memory assessment
        memory_usage = memory_final - memory_before
        if memory_usage < 50:
            st.success(f"🟢 **Uso de memoria eficiente**: +{memory_usage:.1f} MB")
        elif memory_usage < 100:
            st.info(f"🟡 **Uso de memoria moderado**: +{memory_usage:.1f} MB")
        else:
            st.warning(f"🔴 **Alto uso de memoria**: +{memory_usage:.1f} MB")
        
        # Recommendations
        st.subheader("💡 Recomendaciones")
        
        recommendations = []
        
        if performance_results.get('data_load_time', 0) > 0.2:
            recommendations.append("🔄 Considerar aumentar el TTL del cache para reducir recargas de datos")
        
        if performance_results.get('html_render_time', 0) > 0.1:
            recommendations.append("🖼️ Optimizar la generación de HTML o reducir videos por página")
        
        if memory_usage > 100:
            recommendations.append("💾 Implementar limpieza de memoria o lazy loading")
        
        if not recommendations:
            recommendations.append("✅ El rendimiento es óptimo, no se requieren mejoras")
        
        for rec in recommendations:
            st.write(f"- {rec}")
        
        # Cleanup
        gc.collect()
    
    # Comparison with old version
    st.header("📊 Comparación de Rendimiento")
    
    st.markdown("""
    ### 🆚 Mejoras Implementadas:
    
    **📈 Optimizaciones de Rendimiento:**
    - ✅ **Caching integrado**: Datos cacheados por 30 minutos
    - ✅ **Paginación eficiente**: Solo renderiza videos visibles
    - ✅ **Filtros optimizados**: Operaciones cacheadas con `@st.cache_data`
    - ✅ **HTML pre-compilado**: Generación optimizada de tarjetas
    - ✅ **Lazy loading**: Imágenes con carga diferida
    - ✅ **Session state**: Preserva estado entre renders
    
    **🚀 Mejoras de UX:**
    - ✅ **Búsqueda instantánea**: Filtrado por título y canal
    - ✅ **Filtros de fecha**: Última semana, mes, 3 meses
    - ✅ **Navegación mejorada**: Paginación superior e inferior
    - ✅ **Página salteable**: Selección directa de página
    - ✅ **Información de progreso**: Contadores y métricas
    
    **💾 Optimizaciones de Memoria:**
    - ✅ **DataFrames optimizados**: Procesamiento eficiente
    - ✅ **Cleanup automático**: Liberación de memoria
    - ✅ **Columnas responsivas**: Adaptación a pantalla
    """)
    
    # Performance tips
    st.header("💡 Tips de Rendimiento")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **🔧 Para Desarrolladores:**
        - Usa `@st.cache_data` para operaciones costosas
        - Implementa paginación para datasets grandes
        - Optimiza HTML con string concatenation
        - Usa session state para preservar filtros
        - Monitora memoria con `psutil`
        """)
    
    with col2:
        st.markdown("""
        **👤 Para Usuarios:**
        - Usa filtros para reducir resultados
        - Ajusta videos por página según tu conexión
        - Las búsquedas son instantáneas (cacheadas)
        - La paginación preserva filtros aplicados
        - Recarga la página si hay problemas de memoria
        """)

if __name__ == "__main__":
    main() 