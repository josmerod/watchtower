"""
Shortcuts tab component for the Watchtower Streamlit application.
Displays quick access links to useful websites organized by category.
"""

import streamlit as st
import json
import os

# Define paths
SHORTCUTS_DATA_DIR = "../../../data/shortcuts"
CUSTOM_SHORTCUTS_FILE = os.path.join(SHORTCUTS_DATA_DIR, "custom_shortcuts.json")
PREDEFINED_SHORTCUTS_FILE = os.path.join(SHORTCUTS_DATA_DIR, "predefined_shortcuts.json")

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

def render(logger=None):
    """Render the shortcuts tab"""
    st.header("🔖 Accesos Directos")
    
    st.markdown("""
    <div class="card" style="background-color: #2D2B55; padding: 18px; border-radius: 8px; border-left: 5px solid #A37FFF; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);">
        <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #E2E8F0;">
            Enlaces rápidos a sitios web y herramientas útiles. Personaliza esta sección añadiendo enlaces personalizados usando el panel inferior.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
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
        
        # Calculate how to distribute categories across columns
        categories_per_column = max(1, len(all_categories) // 3 + (1 if len(all_categories) % 3 > 0 else 0))
        
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
    
    # Tabs for managing shortcuts
    manage_tab1, manage_tab2, manage_tab3, manage_tab4 = st.tabs(["Añadir enlace", "Organizar", "Exportar configuración", "Importar configuración"])
    
    with manage_tab1:
        # Form for adding custom shortcuts
        with st.form("add_custom_shortcut"):
            st.subheader("Añadir enlace personalizado")
            
            # Get existing categories from predefined shortcuts
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
                    file_name="custom_shortcuts.py",
                    mime="text/plain",
                )
            else:
                st.info("Añade algunos enlaces personalizados para generar código exportable")
        
        with export_tab2:
            # Generate JSON for current custom shortcuts
            if st.session_state.custom_shortcuts:
                json_data = json.dumps(st.session_state.custom_shortcuts, indent=4, ensure_ascii=False)
                st.code(json_data, language="json")
                
                st.download_button(
                    label="Descargar como JSON",
                    data=json_data,
                    file_name="custom_shortcuts.json",
                    mime="application/json",
                )
            else:
                st.info("Añade algunos enlaces personalizados para generar JSON exportable")
    
    with manage_tab4:
        st.subheader("Importar configuración")
        
        # Upload JSON file
        uploaded_file = st.file_uploader("Subir archivo JSON de accesos directos", type=["json"])
        
        if uploaded_file is not None:
            try:
                # Read JSON from uploaded file
                imported_shortcuts = json.load(uploaded_file)
                
                # Validate structure
                valid_shortcuts = []
                for item in imported_shortcuts:
                    if isinstance(item, dict) and 'name' in item and 'url' in item:
                        # Add missing fields if needed
                        if 'icon' not in item:
                            item['icon'] = '🔗'
                        if 'description' not in item:
                            item['description'] = 'Enlace importado'
                        valid_shortcuts.append(item)
                
                # Preview imported shortcuts
                st.write(f"Accesos directos encontrados: {len(valid_shortcuts)}")
                
                for shortcut in valid_shortcuts:
                    st.markdown(f'''
                    <div class="shortcut-item">
                        <div class="shortcut-icon">{shortcut['icon']}</div>
                        <div class="shortcut-content">
                            <div class="shortcut-title">{shortcut['name']}</div>
                            <div class="shortcut-description">{shortcut['description']}</div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
                
                # Add options to replace or merge
                option = st.radio(
                    "¿Cómo quieres importar estos accesos directos?",
                    ["Reemplazar todos los actuales", "Añadir a los actuales"]
                )
                
                if st.button("Importar accesos directos"):
                    if option == "Reemplazar todos los actuales":
                        st.session_state.custom_shortcuts = valid_shortcuts
                    else:  # Añadir a los actuales
                        st.session_state.custom_shortcuts.extend(valid_shortcuts)
                    
                    # Save changes
                    save_custom_shortcuts(st.session_state.custom_shortcuts, logger)
                    st.success(f"Se han importado {len(valid_shortcuts)} accesos directos")
                    st.rerun()
                
            except Exception as e:
                st.error(f"Error al importar accesos directos: {str(e)}") 