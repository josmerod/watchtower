"""
Debug script for Watchtower data loading issues.
Run this to diagnose problems with data files and paths.
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Add the project root to the path
from src.web.fullstreamlit.utils.data_service import DataService
from src.utils.logging import get_logger

def main():
    """Debug data loading issues"""
    st.set_page_config(
        page_title="Watchtower Data Debug",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 Watchtower Data Debug")
    st.markdown("Herramienta de depuración para identificar problemas con la carga de datos.")
    
    # Initialize components
    logger = get_logger("DataDebug")
    data_service = DataService(logger)
    
    st.header("📁 Verificación de Rutas")
    
    # Show resolved paths
    st.write(f"**Directorio de datos resuelto:** `{data_service.data_dir}`")
    st.write(f"**Existe el directorio:** {data_service.data_dir.exists()}")
    
    if data_service.data_dir.exists():
        st.success("✅ Directorio de datos encontrado")
        
        # List subdirectories
        subdirs = [d for d in data_service.data_dir.iterdir() if d.is_dir()]
        st.write(f"**Subdirectorios encontrados:** {len(subdirs)}")
        
        with st.expander("Ver subdirectorios"):
            for subdir in sorted(subdirs):
                st.write(f"- {subdir.name}")
    else:
        st.error("❌ Directorio de datos no encontrado")
        st.write("Verifica que el proyecto esté en la ubicación correcta.")
    
    st.header("🔍 Verificación de Archivos de Datos")
    
    # Check specific data files
    data_files_to_check = {
        "Games - Deals": data_service.data_dir / "games" / "deals.json",
        "Games - Bundles": data_service.data_dir / "games" / "bundles.json", 
        "Games - Giveaways": data_service.data_dir / "games" / "giveaways.json",
        "Games - Humble Bundles": data_service.data_dir / "games" / "humblebundles.json",
        "HackerNews": data_service.data_dir / "hackernews" / "hackernews.json",
        "HackerNews (alt)": data_service.data_dir / "hackernews" / "stories.json",
        "FutureTools": data_service.data_dir / "futuretools" / "futuretoolsnews.json",
        "FutureTools (alt)": data_service.data_dir / "futuretools" / "news.json",
        "Coursera": data_service.data_dir / "classcentral" / "coursera_courses.json",
        "Valencia Events": data_service.data_dir / "valencia_events" / "events.json",
        "ArXiv CSV": data_service.data_dir / "arxiv" / "processed" / "csv" / "papers.csv",
        "ArXiv JSON": data_service.data_dir / "arxiv" / "processed" / "json" / "papers.json",
    }
    
    for file_desc, file_path in data_files_to_check.items():
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"**{file_desc}**")
            st.code(str(file_path), language="text")
        
        with col2:
            if file_path.exists():
                st.success("✅ Existe")
            else:
                st.error("❌ No existe")
        
        with col3:
            if file_path.exists():
                try:
                    size = file_path.stat().st_size
                    if size > 1024*1024:  # > 1MB
                        st.write(f"{size // (1024*1024)} MB")
                    elif size > 1024:  # > 1KB
                        st.write(f"{size // 1024} KB")
                    else:
                        st.write(f"{size} B")
                except:
                    st.write("Error")
            else:
                st.write("-")
    
    st.header("🎮 YouTube Channels")
    
    # Check YouTube directories
    youtube_dir = data_service.data_dir / "youtube"
    if youtube_dir.exists():
        channels = [d for d in youtube_dir.iterdir() if d.is_dir()]
        st.write(f"**Canales encontrados:** {len(channels)}")
        
        for channel in sorted(channels):
            video_files = list(channel.glob("*.json"))
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**{channel.name}**")
                if video_files:
                    for vf in video_files:
                        st.write(f"  - {vf.name}")
                else:
                    st.write("  - Sin archivos JSON")
            
            with col2:
                if video_files:
                    st.success(f"✅ {len(video_files)} archivo(s)")
                else:
                    st.warning("⚠️ Sin datos")
    else:
        st.error("❌ Directorio de YouTube no encontrado")
    
    st.header("🧪 Prueba de Carga de Datos")
    
    if st.button("🔄 Probar carga de datos"):
        with st.spinner("Probando carga de datos..."):
            
            # Test games data
            st.subheader("🎮 Datos de Juegos")
            try:
                deals_df, bundles_df, giveaways_df = data_service.get_games_data()
                st.write(f"- Ofertas: {len(deals_df)} registros")
                st.write(f"- Bundles: {len(bundles_df)} registros")
                st.write(f"- Giveaways: {len(giveaways_df)} registros")
                
                if not deals_df.empty:
                    st.write("Columnas en ofertas:", list(deals_df.columns))
                
            except Exception as e:
                st.error(f"Error cargando datos de juegos: {str(e)}")
            
            # Test news data
            st.subheader("📰 Datos de Noticias")
            try:
                news_data = data_service.get_news_data()
                st.write(f"- Fuentes encontradas: {list(news_data.keys())}")
                for source, df in news_data.items():
                    st.write(f"  - {source}: {len(df)} artículos")
                    
            except Exception as e:
                st.error(f"Error cargando datos de noticias: {str(e)}")
            
            # Test videos data
            st.subheader("📺 Datos de Videos")
            try:
                videos_data = data_service.get_videos_data()
                st.write(f"- Canales encontrados: {list(videos_data.keys())}")
                for channel, df in videos_data.items():
                    st.write(f"  - {channel}: {len(df)} videos")
                    
            except Exception as e:
                st.error(f"Error cargando datos de videos: {str(e)}")
            
            # Test courses data
            st.subheader("🎓 Datos de Cursos")
            try:
                courses_data = data_service.get_courses_data()
                st.write(f"- Plataformas encontradas: {list(courses_data.keys())}")
                for platform, df in courses_data.items():
                    st.write(f"  - {platform}: {len(df)} cursos")
                    
            except Exception as e:
                st.error(f"Error cargando datos de cursos: {str(e)}")
            
            # Test summary
            st.subheader("📊 Resumen de Datos")
            try:
                summary = data_service.get_data_summary()
                st.json(summary)
                
            except Exception as e:
                st.error(f"Error generando resumen: {str(e)}")

if __name__ == "__main__":
    main() 