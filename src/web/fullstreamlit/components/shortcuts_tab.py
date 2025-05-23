"""
Shortcuts tab component for the Watchtower Streamlit application.
Displays quick access links to useful websites organized by category with data dashboard.
"""

import streamlit as st
import json
import os
from typing import Dict, Any
from datetime import datetime
import pandas as pd
import time
import threading

# Get the project root directory
def get_project_root():
    """Get the project root directory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up from src/web/fullstreamlit/components to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
    return project_root

# Define shortcuts data path using absolute path
PROJECT_ROOT = get_project_root()
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SHORTCUTS_DATA_DIR = os.path.join(DATA_DIR, "shortcuts")

CUSTOM_SHORTCUTS_FILE = os.path.join(SHORTCUTS_DATA_DIR, "custom_shortcuts.json")
PREDEFINED_SHORTCUTS_FILE = os.path.join(SHORTCUTS_DATA_DIR, "predefined_shortcuts.json")

def open_link_js(url: str, text: str = "Abriendo enlace...") -> str:
    """Generate JavaScript to open a link in a new tab"""
    return f"""
    <script>
        window.open('{url}', '_blank');
    </script>
    <div style="color: #10B981; font-weight: 500; text-align: center; padding: 8px;">
        {text}
    </div>
    """

def load_predefined_shortcuts(logger=None):
    """Load predefined shortcuts from JSON file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(SHORTCUTS_DATA_DIR, exist_ok=True)
        
        if os.path.exists(PREDEFINED_SHORTCUTS_FILE):
            if logger:
                logger.info(f"Loading predefined shortcuts from {PREDEFINED_SHORTCUTS_FILE}")
            with open(PREDEFINED_SHORTCUTS_FILE, "r", encoding="utf-8") as f:
                shortcuts = json.load(f)
            if logger:
                logger.info(f"Successfully loaded predefined shortcuts with {len(shortcuts)} categories")
            return shortcuts
        else:
            if logger:
                logger.error(f"Predefined shortcuts file not found at {PREDEFINED_SHORTCUTS_FILE}")
            return {}
    except Exception as e:
        if logger:
            logger.error(f"Error loading predefined shortcuts: {str(e)}")
        return {}

# Local versions of loader functions
def load_custom_shortcuts(logger=None):
    """Load custom shortcuts from JSON file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(SHORTCUTS_DATA_DIR, exist_ok=True)
        
        if os.path.exists(CUSTOM_SHORTCUTS_FILE):
            if logger:
                logger.info(f"Loading custom shortcuts from {CUSTOM_SHORTCUTS_FILE}")
            with open(CUSTOM_SHORTCUTS_FILE, "r", encoding="utf-8") as f:
                shortcuts = json.load(f)
            if logger:
                logger.info(f"Successfully loaded {len(shortcuts)} custom shortcuts")
            return shortcuts
        else:
            if logger:
                logger.info(f"No custom shortcuts file found at {CUSTOM_SHORTCUTS_FILE}")
            return []
    except Exception as e:
        if logger:
            logger.error(f"Error loading custom shortcuts: {str(e)}")
        return []

def save_custom_shortcuts(shortcuts, logger=None):
    """Save custom shortcuts to JSON file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(SHORTCUTS_DATA_DIR, exist_ok=True)
        
        if logger:
            logger.info(f"Saving {len(shortcuts)} custom shortcuts to {CUSTOM_SHORTCUTS_FILE}")
        with open(CUSTOM_SHORTCUTS_FILE, "w", encoding="utf-8") as f:
            json.dump(shortcuts, f, indent=4, ensure_ascii=False)
        if logger:
            logger.info("Custom shortcuts saved successfully")
        return True
    except Exception as e:
        if logger:
            logger.error(f"Error saving custom shortcuts: {str(e)}")
        return False

def render_data_dashboard(data_summary: Dict[str, Any]):
    """Render the data summary dashboard"""
    st.markdown("### 📊 Resumen de Datos del Sistema")
    
    # Initialize session state for button clicks
    if 'quick_action_clicked' not in st.session_state:
        st.session_state.quick_action_clicked = {}
    
    # Check if we have valid data
    if not data_summary or all(
        data_summary.get(key, {}).get('total', 0) == 0 and 
        data_summary.get(key, {}).get('deals', 0) == 0
        for key in ['games', 'courses', 'news', 'videos']
    ):
        st.warning("⚠️ Algunos datos no se pudieron cargar. Esto puede deberse a archivos faltantes o problemas de conectividad.")
        
        # Show data directory status
        with st.expander("🔍 Información de depuración"):
            st.write("**Estado de los datos:**")
            st.write("- Verificar que los archivos de datos existen en las rutas correctas")
            st.write("- Revisar los logs de la aplicación para más detalles")
            st.write("- Algunos servicios de datos pueden estar temporalmente no disponibles")
    
    # Create metric columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_games = data_summary.get('games', {}).get('deals', 0) + \
                     data_summary.get('games', {}).get('bundles', 0) + \
                     data_summary.get('games', {}).get('giveaways', 0)
        st.metric(
            label="🎮 Juegos",
            value=f"{total_games}",
            delta=f"Ofertas: {data_summary.get('games', {}).get('deals', 0)}"
        )
        
    with col2:
        st.metric(
            label="📰 Noticias", 
            value=data_summary.get('news', {}).get('total', 0),
            delta=f"Fuentes: {len(data_summary.get('news', {}).get('sources', []))}"
        )
        
    with col3:
        st.metric(
            label="🎓 Cursos",
            value=data_summary.get('courses', {}).get('total', 0),
            delta=f"Plataformas: {len(data_summary.get('courses', {}).get('platforms', []))}"
        )
        
    with col4:
        st.metric(
            label="📺 Videos",
            value=data_summary.get('videos', {}).get('total', 0),
            delta=f"Canales: {data_summary.get('videos', {}).get('channels', 0)}"
        )
    
    # Detailed breakdown
    with st.expander("📈 Detalles por Categoría"):
        details_col1, details_col2, details_col3 = st.columns(3)
        
        with details_col1:
            st.markdown("**🎮 Gaming**")
            games_data = data_summary.get('games', {})
            st.write(f"• Ofertas: {games_data.get('deals', 0)}")
            st.write(f"• Bundles: {games_data.get('bundles', 0)}")
            st.write(f"• Giveaways: {games_data.get('giveaways', 0)}")
            if games_data.get('latest_deal'):
                st.write(f"• Última oferta: {games_data['latest_deal'][:30]}...")
            
            st.markdown("**📚 Research**")
            arxiv_data = data_summary.get('arxiv', {})
            st.write(f"• Papers ArXiv: {arxiv_data.get('total', 0)}")
            st.write(f"• Recientes (7d): {arxiv_data.get('recent', 0)}")
            
        with details_col2:
            st.markdown("**📰 Noticias por Fuente**")
            news_sources = data_summary.get('news', {}).get('by_source', {})
            if news_sources:
                for source, count in news_sources.items():
                    st.write(f"• {source.title()}: {count}")
            else:
                st.write("• No hay fuentes de noticias disponibles")
            
            st.markdown("**🏙️ Eventos Valencia**")
            events_data = data_summary.get('events', {})
            st.write(f"• Total eventos: {events_data.get('total', 0)}")
            st.write(f"• Próximos: {events_data.get('upcoming', 0)}")
            
        with details_col3:
            st.markdown("**🎓 Cursos por Plataforma**")
            course_platforms = data_summary.get('courses', {}).get('by_platform', {})
            if course_platforms:
                for platform, count in course_platforms.items():
                    st.write(f"• {platform.title()}: {count}")
            else:
                st.write("• No hay plataformas de cursos disponibles")
            
            st.markdown("**📺 Top Canales YouTube**")
            video_channels = data_summary.get('videos', {}).get('by_channel', {})
            if video_channels:
                top_channels = sorted(video_channels.items(), key=lambda x: x[1], reverse=True)[:5]
                for channel, count in top_channels:
                    display_name = channel.replace('_', ' ').replace('-', ' ').title()
                    st.write(f"• {display_name}: {count}")
            else:
                st.write("• No hay canales de YouTube disponibles")
    
    # Quick actions
    st.markdown("### ⚡ Acciones Rápidas")
    quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)
    
    with quick_col1:
        games_available = data_summary.get('games', {}).get('deals', 0) > 0
        games_count = data_summary.get('games', {}).get('deals', 0)
        
        # Check if button was recently clicked
        recently_clicked = st.session_state.quick_action_clicked.get('games', False)
        
        if st.button(f"🎮 Ver Ofertas Gaming ({games_count})", use_container_width=True, disabled=not games_available or recently_clicked, key="quick_games"):
            if games_available:
                # Mark as clicked to prevent rapid clicks
                st.session_state.quick_action_clicked['games'] = True
                
                # Show preview of latest games data
                with st.spinner("Cargando información de juegos..."):
                    st.success("🎮 Últimas ofertas de juegos disponibles!")
                    latest_deal = data_summary.get('games', {}).get('latest_deal')
                    if latest_deal:
                        st.info(f"📦 Última oferta: {latest_deal}")
                    st.markdown("💡 **Tip:** Ve a la pestaña 'Juegos' para ver todas las ofertas, bundles y giveaways.")
                    time.sleep(0.1)
                
                # Reset click state after a brief delay
                def reset_games_click():
                    time.sleep(2)
                    if 'quick_action_clicked' in st.session_state:
                        st.session_state.quick_action_clicked['games'] = False
                
                threading.Thread(target=reset_games_click, daemon=True).start()
        
    with quick_col2:
        news_available = data_summary.get('news', {}).get('total', 0) > 0
        news_count = data_summary.get('news', {}).get('total', 0)
        
        recently_clicked = st.session_state.quick_action_clicked.get('news', False)
        
        if st.button(f"📰 Leer Noticias ({news_count})", use_container_width=True, disabled=not news_available or recently_clicked, key="quick_news"):
            if news_available:
                st.session_state.quick_action_clicked['news'] = True
                
                # Show preview of news sources
                with st.spinner("Cargando información de noticias..."):
                    st.success("📰 Noticias disponibles!")
                    news_sources = data_summary.get('news', {}).get('sources', [])
                    if news_sources:
                        sources_text = ", ".join([s.title() for s in news_sources[:3]])
                        if len(news_sources) > 3:
                            sources_text += f" y {len(news_sources) - 3} más"
                        st.info(f"📡 Fuentes: {sources_text}")
                    st.markdown("💡 **Tip:** Ve a la pestaña 'Noticias' para leer artículos completos.")
                    time.sleep(0.1)
                
                def reset_news_click():
                    time.sleep(2)
                    if 'quick_action_clicked' in st.session_state:
                        st.session_state.quick_action_clicked['news'] = False
                
                threading.Thread(target=reset_news_click, daemon=True).start()
        
    with quick_col3:
        courses_available = data_summary.get('courses', {}).get('total', 0) > 0
        courses_count = data_summary.get('courses', {}).get('total', 0)
        
        recently_clicked = st.session_state.quick_action_clicked.get('courses', False)
        
        if st.button(f"🎓 Explorar Cursos ({courses_count})", use_container_width=True, disabled=not courses_available or recently_clicked, key="quick_courses"):
            if courses_available:
                st.session_state.quick_action_clicked['courses'] = True
                
                # Show preview of course platforms
                with st.spinner("Cargando información de cursos..."):
                    st.success("🎓 Cursos disponibles!")
                    platforms = data_summary.get('courses', {}).get('platforms', [])
                    if platforms:
                        platforms_text = ", ".join([p.title() for p in platforms])
                        st.info(f"🏫 Plataformas: {platforms_text}")
                    st.markdown("💡 **Tip:** Ve a la pestaña 'Cursos' para explorar por plataforma.")
                    time.sleep(0.1)
                
                def reset_courses_click():
                    time.sleep(2)
                    if 'quick_action_clicked' in st.session_state:
                        st.session_state.quick_action_clicked['courses'] = False
                
                threading.Thread(target=reset_courses_click, daemon=True).start()
        
    with quick_col4:
        arxiv_available = data_summary.get('arxiv', {}).get('total', 0) > 0
        arxiv_count = data_summary.get('arxiv', {}).get('total', 0)
        recent_count = data_summary.get('arxiv', {}).get('recent', 0)
        
        recently_clicked = st.session_state.quick_action_clicked.get('arxiv', False)
        
        if st.button(f"📚 Papers ArXiv ({arxiv_count})", use_container_width=True, disabled=not arxiv_available or recently_clicked, key="quick_arxiv"):
            if arxiv_available:
                st.session_state.quick_action_clicked['arxiv'] = True
                
                # Show preview of ArXiv data
                with st.spinner("Cargando información de ArXiv..."):
                    st.success("📚 Papers de investigación disponibles!")
                    if recent_count > 0:
                        st.info(f"🔬 {recent_count} papers nuevos esta semana")
                    st.markdown("💡 **Tip:** Ve a la pestaña 'ArXiv Papers' para buscar y filtrar investigaciones.")
                    time.sleep(0.1)
                
                def reset_arxiv_click():
                    time.sleep(2)
                    if 'quick_action_clicked' in st.session_state:
                        st.session_state.quick_action_clicked['arxiv'] = False
                
                threading.Thread(target=reset_arxiv_click, daemon=True).start()

    # Add a section for quick website access
    st.markdown("### 🌐 Acceso Rápido a Sitios Web")

    # Popular shortcuts for quick access
    quick_links_col1, quick_links_col2, quick_links_col3, quick_links_col4 = st.columns(4)

    with quick_links_col1:
        if st.button("🔍 Google", use_container_width=True, key="link_google"):
            st.markdown(open_link_js("https://google.com"), unsafe_allow_html=True)

    with quick_links_col2:
        if st.button("🤖 ChatGPT", use_container_width=True, key="link_chatgpt"):
            st.markdown(open_link_js("https://chat.openai.com"), unsafe_allow_html=True)

    with quick_links_col3:
        if st.button("🐙 GitHub", use_container_width=True, key="link_github"):
            st.markdown(open_link_js("https://github.com"), unsafe_allow_html=True)

    with quick_links_col4:
        if st.button("📹 YouTube", use_container_width=True, key="link_youtube"):
            st.markdown(open_link_js("https://youtube.com"), unsafe_allow_html=True)

    # System status section
    if data_summary:
        total_items = (
            data_summary.get('games', {}).get('deals', 0) + 
            data_summary.get('games', {}).get('bundles', 0) + 
            data_summary.get('games', {}).get('giveaways', 0) +
            data_summary.get('news', {}).get('total', 0) +
            data_summary.get('courses', {}).get('total', 0) +
            data_summary.get('videos', {}).get('total', 0) +
            data_summary.get('arxiv', {}).get('total', 0) +
            data_summary.get('events', {}).get('total', 0)
        )
        
        if total_items > 0:
            st.markdown(f"""
            <div style="text-align: center; margin-top: 20px; padding: 10px; background-color: #1E293B; border-radius: 8px; border: 1px solid #475569;">
                <span style="color: #10B981; font-size: 18px;">🟢</span>
                <span style="color: #E5E7EB; margin-left: 8px;">Sistema operativo - <strong>{total_items:,}</strong> elementos totales cargados</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="text-align: center; margin-top: 20px; padding: 10px; background-color: #1E293B; border-radius: 8px; border: 1px solid #DC2626;">
                <span style="color: #EF4444; font-size: 18px;">🔴</span>
                <span style="color: #E5E7EB; margin-left: 8px;">Sistema con problemas - No hay datos disponibles</span>
            </div>
            """, unsafe_allow_html=True)

def render_shortcuts_section(logger=None):
    """Render the traditional shortcuts section"""
    # Load predefined shortcuts
    predefined_shortcuts = load_predefined_shortcuts(logger)
    
    # Ensure custom_shortcuts exists in session state
    if 'custom_shortcuts' not in st.session_state:
        st.session_state.custom_shortcuts = load_custom_shortcuts(logger)
    
    # Search bar for filtering shortcuts
    search = st.text_input("🔍 Buscar acceso directo", placeholder="Buscar por nombre o descripción...")
    
    # Combine predefined and custom shortcuts for search
    all_shortcuts = []
    for category, shortcuts in predefined_shortcuts.items():
        for shortcut in shortcuts:
            shortcut_with_category = shortcut.copy()
            shortcut_with_category['category'] = category
            all_shortcuts.append(shortcut_with_category)
    
    # Add custom shortcuts if any
    for shortcut in st.session_state.custom_shortcuts:
        shortcut_with_category = shortcut.copy()
        shortcut_with_category['category'] = "Personalizados"
        all_shortcuts.append(shortcut_with_category)
    
    # Filter shortcuts if search is not empty
    if search:
        filtered_shortcuts = [s for s in all_shortcuts if (
            search.lower() in s['name'].lower() or 
            search.lower() in s['description'].lower() or
            search.lower() in s['category'].lower()
        )]
        
        if not filtered_shortcuts:
            st.warning(f"No se encontraron accesos directos que coincidan con '{search}'")
        else:
            # Create three columns for search results
            result_cols = st.columns(3)
            
            # Distribute shortcuts across the three columns
            for i, shortcut in enumerate(filtered_shortcuts):
                with result_cols[i % 3]:
                    st.markdown(f"""
                    <a href="{shortcut['url']}" target="_blank" style="text-decoration: none;">
                        <div class="shortcut-item">
                            <div class="shortcut-icon">{shortcut['icon']}</div>
                            <div class="shortcut-content">
                                <div class="shortcut-title">{shortcut['name']} <span style="opacity: 0.6; font-size: 12px;">({shortcut['category']})</span></div>
                                <div class="shortcut-description">{shortcut['description']}</div>
                            </div>
                        </div>
                    </a>
                    """, unsafe_allow_html=True)
    else:
        # Create three fixed columns for categories
        col1, col2, col3 = st.columns(3)
        
        # Combine predefined and custom categories
        all_categories = list(predefined_shortcuts.keys())
        
        # Add custom categories that aren't in predefined ones
        custom_categories = set()
        for shortcut in st.session_state.custom_shortcuts:
            category = shortcut.get("category", "Personalizados")
            if category not in predefined_shortcuts:
                custom_categories.add(category)
        
        all_categories.extend(sorted(list(custom_categories)))
        
        # Distribute categories across columns
        for i, category in enumerate(all_categories):
            column = col1 if i % 3 == 0 else col2 if i % 3 == 1 else col3
            with column:
                st.markdown(f'<div class="shortcuts-category">', unsafe_allow_html=True)
                st.markdown(f'<h3>{category}</h3>', unsafe_allow_html=True)
                
                # Display predefined shortcuts for this category
                if category in predefined_shortcuts:
                    for shortcut in predefined_shortcuts[category]:
                        st.markdown(f'''
                        <a href="{shortcut['url']}" target="_blank" style="text-decoration: none;">
                            <div class="shortcut-item">
                                <div class="shortcut-icon">{shortcut['icon']}</div>
                                <div class="shortcut-content">
                                    <div class="shortcut-title">{shortcut['name']}</div>
                                    <div class="shortcut-description">{shortcut['description']}</div>
                                </div>
                            </div>
                        </a>
                        ''', unsafe_allow_html=True)
                
                # Display custom shortcuts for this category
                custom_shortcuts_in_category = [s for s in st.session_state.custom_shortcuts 
                                               if s.get("category", "Personalizados") == category]
                
                for i, shortcut in enumerate(custom_shortcuts_in_category):
                    # For predefined categories, no delete button
                    if category in predefined_shortcuts:
                        st.markdown(f'''
                        <a href="{shortcut['url']}" target="_blank" style="text-decoration: none;">
                            <div class="shortcut-item">
                                <div class="shortcut-icon">{shortcut['icon']}</div>
                                <div class="shortcut-content">
                                    <div class="shortcut-title">{shortcut['name']}</div>
                                    <div class="shortcut-description">{shortcut['description']}</div>
                                </div>
                            </div>
                        </a>
                        ''', unsafe_allow_html=True)
                    else:
                        # Custom category with delete button
                        c1, c2 = st.columns([5, 1])
                        with c1:
                            st.markdown(f'''
                            <a href="{shortcut['url']}" target="_blank" style="text-decoration: none;">
                                <div class="shortcut-item">
                                    <div class="shortcut-icon">{shortcut['icon']}</div>
                                    <div class="shortcut-content">
                                        <div class="shortcut-title">{shortcut['name']}</div>
                                        <div class="shortcut-description">{shortcut['description']}</div>
                                    </div>
                                </div>
                            </a>
                            ''', unsafe_allow_html=True)
                        with c2:
                            # Find the index in the original list for deletion
                            original_index = st.session_state.custom_shortcuts.index(shortcut)
                            if st.button("❌", key=f"del_main_{category}_{original_index}", help="Eliminar este enlace"):
                                st.session_state.custom_shortcuts.pop(original_index)
                                # Save changes
                                save_custom_shortcuts(st.session_state.custom_shortcuts, logger)
                                st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)

def render_shortcuts_management(logger=None):
    """Render the shortcuts management section"""
    # Tabs for managing shortcuts
    manage_tab1, manage_tab2, manage_tab3, manage_tab4 = st.tabs(["Añadir enlace", "Organizar", "Exportar configuración", "Importar configuración"])
    
    with manage_tab1:
        # Form for adding custom shortcuts
        with st.form("add_custom_shortcut"):
            st.subheader("Añadir enlace personalizado")
            
            # Get existing categories from predefined shortcuts
            predefined_shortcuts = load_predefined_shortcuts(logger)
            existing_categories = list(predefined_shortcuts.keys()) + ["Personalizados", "Nueva categoría..."]
            
            # Get custom categories from custom shortcuts
            custom_categories = set()
            for shortcut in st.session_state.custom_shortcuts:
                if "category" in shortcut and shortcut["category"]:
                    custom_categories.add(shortcut["category"])
            
            # Combine all categories without duplicates
            all_categories = sorted(list(set(existing_categories) | custom_categories))
            if "Nueva categoría..." in all_categories:
                all_categories.remove("Nueva categoría...")
                all_categories.append("Nueva categoría...")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                custom_name = st.text_input("Nombre", placeholder="Nombre del enlace")
                custom_icon = st.text_input("Icono (emoji)", placeholder="🔗", max_chars=2)
                
                # Category selection
                category_selection = st.selectbox(
                    "Categoría",
                    all_categories,
                    index=all_categories.index("Personalizados") if "Personalizados" in all_categories else 0
                )
                
                # Show input for new category if "Nueva categoría..." selected
                new_category = None
                if category_selection == "Nueva categoría...":
                    new_category = st.text_input("Nombre de nueva categoría", placeholder="Mi categoría")
        
            with col2:
                custom_url = st.text_input("URL", placeholder="https://example.com")
                custom_desc = st.text_input("Descripción (opcional)", placeholder="Breve descripción")
            
            # Submit button
            submitted = st.form_submit_button("Añadir enlace")
            if submitted and custom_name and custom_url:
                # Get the category
                final_category = new_category if category_selection == "Nueva categoría..." and new_category else category_selection
                
                # If it's a new valid category, add it
                if final_category != "Nueva categoría...":
                    # Save to session state
                    st.session_state.custom_shortcuts.append({
                        "name": custom_name,
                        "url": custom_url,
                        "icon": custom_icon if custom_icon else "🔗",
                        "description": custom_desc if custom_desc else "Enlace personalizado",
                        "category": final_category
                    })
                    # Save changes to file
                    save_custom_shortcuts(st.session_state.custom_shortcuts, logger)
                    st.success(f"Enlace '{custom_name}' añadido a la categoría '{final_category}'")
                    st.rerun()
                else:
                    st.error("Por favor, ingresa un nombre válido para la nueva categoría")
    
    with manage_tab2:
        st.subheader("Organizar accesos directos")
        
        if not st.session_state.custom_shortcuts:
            st.info("No hay accesos directos personalizados para organizar.")
        else:
            # Group shortcuts by category
            shortcuts_by_category = {}
            predefined_shortcuts = load_predefined_shortcuts(logger)
            
            for i, shortcut in enumerate(st.session_state.custom_shortcuts):
                category = shortcut.get("category", "Personalizados")
                if category not in shortcuts_by_category:
                    shortcuts_by_category[category] = []
                
                # Add index to shortcut for reference
                shortcut_with_index = shortcut.copy()
                shortcut_with_index["index"] = i
                shortcuts_by_category[category].append(shortcut_with_index)
            
            # Get existing categories from predefined shortcuts for moving items
            existing_categories = list(predefined_shortcuts.keys()) + ["Personalizados"] + list(shortcuts_by_category.keys())
            existing_categories = sorted(list(set(existing_categories)))
            
            # Display shortcuts by category with organization options
            for category, shortcuts in shortcuts_by_category.items():
                with st.expander(f"{category} ({len(shortcuts)} enlaces)", expanded=True):
                    for shortcut in shortcuts:
                        col1, col2, col3 = st.columns([4, 2, 1])
                        
                        with col1:
                            st.markdown(f'''
                            <div class="shortcut-item" style="margin-bottom: 5px;">
                                <div class="shortcut-icon">{shortcut['icon']}</div>
                                <div class="shortcut-content">
                                    <div class="shortcut-title">{shortcut['name']}</div>
                                </div>
                            </div>
                            ''', unsafe_allow_html=True)
                        
                        with col2:
                            # Category movement dropdown
                            move_to = st.selectbox(
                                "Mover a",
                                existing_categories,
                                index=existing_categories.index(category),
                                key=f"move_{shortcut['index']}"
                            )
                            
                            if move_to != category:
                                # Update category
                                st.session_state.custom_shortcuts[shortcut['index']]["category"] = move_to
                                # Save changes
                                save_custom_shortcuts(st.session_state.custom_shortcuts, logger)
                                st.success(f"'{shortcut['name']}' movido a '{move_to}'")
                                st.rerun()
                        
                        with col3:
                            # Delete button
                            if st.button("❌", key=f"del_org_{shortcut['index']}", help="Eliminar este enlace"):
                                st.session_state.custom_shortcuts.pop(shortcut['index'])
                                # Save changes
                                save_custom_shortcuts(st.session_state.custom_shortcuts, logger)
                                st.success(f"Enlace '{shortcut['name']}' eliminado")
                                st.rerun()
            
            # Button to remove empty categories
            if st.button("Limpiar categorías vacías"):
                # Get categories with shortcuts
                used_categories = set()
                for shortcut in st.session_state.custom_shortcuts:
                    category = shortcut.get("category", "Personalizados")
                    used_categories.add(category)
                
                # Remove unused categories
                for shortcut in st.session_state.custom_shortcuts:
                    category = shortcut.get("category")
                    if category and category not in used_categories:
                        shortcut.pop("category", None)
                
                # Save changes
                save_custom_shortcuts(st.session_state.custom_shortcuts, logger)
                st.success("Categorías vacías eliminadas")
                st.rerun()
    
    with manage_tab3:
        st.subheader("Exportar configuración")
        
        export_tab1, export_tab2 = st.tabs(["Python", "JSON"])
        
        with export_tab1:
            # Generate Python code snippet for current custom shortcuts
            if st.session_state.custom_shortcuts:
                code_snippet = "# Añade esto a la estructura SHORTCUTS en el archivo app.py\n"
                code_snippet += "\"Personalizados\": [\n"
                
                for shortcut in st.session_state.custom_shortcuts:
                    code_snippet += f"    {{\"name\": \"{shortcut['name']}\", \"url\": \"{shortcut['url']}\", \"icon\": \"{shortcut['icon']}\", \"description\": \"{shortcut['description']}\"}},\n"
                
                code_snippet += "]\n"
                
                st.code(code_snippet, language="python")
                
                st.download_button(
                    label="Descargar como Python (.py)",
                    data=code_snippet,
                    file_name=f"shortcuts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py",
                    mime="text/plain"
                )
            else:
                st.info("No hay accesos directos personalizados para exportar.")
        
        with export_tab2:
            # Generate JSON for current custom shortcuts
            if st.session_state.custom_shortcuts:
                json_data = json.dumps(st.session_state.custom_shortcuts, indent=4, ensure_ascii=False)
                st.code(json_data, language="json")
                
                st.download_button(
                    label="Descargar como JSON (.json)",
                    data=json_data,
                    file_name=f"shortcuts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            else:
                st.info("No hay accesos directos personalizados para exportar.")
    
    with manage_tab4:
        st.subheader("Importar configuración")
        
        # File uploader for importing shortcuts
        uploaded_file = st.file_uploader(
            "Subir archivo de configuración",
            type=['json'],
            help="Sube un archivo JSON con la configuración de accesos directos"
        )
        
        # Option to replace or merge
        import_mode = st.radio(
            "Modo de importación",
            ["Reemplazar todos los enlaces", "Fusionar con los existentes"],
            help="Reemplazar eliminará todos los enlaces actuales, fusionar los mantendrá"
        )
        
        if uploaded_file is not None:
            try:
                # Read and parse the uploaded file
                file_content = uploaded_file.read().decode('utf-8')
                imported_shortcuts = json.loads(file_content)
                
                # Validate the structure
                if isinstance(imported_shortcuts, list):
                    valid_shortcuts = []
                    for shortcut in imported_shortcuts:
                        if isinstance(shortcut, dict) and all(key in shortcut for key in ['name', 'url']):
                            # Add missing fields with defaults
                            if 'icon' not in shortcut:
                                shortcut['icon'] = '🔗'
                            if 'description' not in shortcut:
                                shortcut['description'] = 'Enlace importado'
                            if 'category' not in shortcut:
                                shortcut['category'] = 'Importados'
                            valid_shortcuts.append(shortcut)
                    
                    if valid_shortcuts:
                        # Preview the shortcuts to be imported
                        st.subheader("Vista previa de enlaces a importar:")
                        
                        preview_df = pd.DataFrame(valid_shortcuts)
                        st.dataframe(preview_df[['name', 'url', 'category', 'description']], use_container_width=True)
                        
                        # Import button
                        if st.button(f"Importar {len(valid_shortcuts)} enlaces", type="primary"):
                            if import_mode == "Reemplazar todos los enlaces":
                                st.session_state.custom_shortcuts = valid_shortcuts
                            else:  # Merge mode
                                st.session_state.custom_shortcuts.extend(valid_shortcuts)
                            
                            # Save changes
                            save_custom_shortcuts(st.session_state.custom_shortcuts, logger)
                            st.success(f"¡{len(valid_shortcuts)} enlaces importados exitosamente!")
                            st.rerun()
                    else:
                        st.error("No se encontraron enlaces válidos en el archivo.")
                else:
                    st.error("El archivo debe contener una lista de objetos JSON.")
                    
            except json.JSONDecodeError:
                st.error("Error al leer el archivo JSON. Verifica que el formato sea correcto.")
            except Exception as e:
                st.error(f"Error al importar accesos directos: {str(e)}")

def render(logger=None, data_service=None):
    """Render the shortcuts tab with dashboard"""
    st.header("🔖 Accesos Directos y Dashboard")
    
    st.markdown("""
    <div class="card" style="background-color: #2D2B55; padding: 18px; border-radius: 8px; border-left: 5px solid #A37FFF; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);">
        <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #E2E8F0;">
            Panel principal con resumen de datos del sistema y enlaces rápidos a sitios web y herramientas útiles.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Render dashboard if data service is available
    if data_service:
        try:
            if logger:
                logger.info("Attempting to generate data summary...")
            data_summary = data_service.get_data_summary()
            
            if data_summary:
                render_data_dashboard(data_summary)
                st.markdown("---")
            else:
                st.error("❌ No se pudo generar el resumen de datos.")
                if logger:
                    logger.error("Data summary returned empty or None")
        except Exception as e:
            if logger:
                logger.error(f"Error generating data summary: {str(e)}", exc_info=True)
            st.error(f"❌ Error al generar el resumen de datos: {str(e)}")
            st.info("Mostrando solo los accesos directos.")
    else:
        st.warning("⚠️ Servicio de datos no disponible. Mostrando solo los accesos directos.")
    
    # Render shortcuts section
    st.markdown("### 🔗 Enlaces Útiles")
    render_shortcuts_section(logger)
    
    # Render management section
    st.markdown("---")
    st.markdown("### ⚙️ Gestión de Enlaces")
    render_shortcuts_management(logger) 