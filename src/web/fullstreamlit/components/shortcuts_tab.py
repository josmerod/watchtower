"""Shortcuts tab component for the Watchtower Streamlit application.
Displays quick access links to useful websites organized by category.
"""

import json
import os
from datetime import datetime

import streamlit as st


# Get the project root directory
def get_project_root():
    """Get the project root directory."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up from src/web/fullstreamlit/components to project root
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    )
    return project_root


# Define shortcuts data path using absolute path
PROJECT_ROOT = get_project_root()
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SHORTCUTS_DATA_DIR = os.path.join(DATA_DIR, "shortcuts")

CUSTOM_SHORTCUTS_FILE = os.path.join(SHORTCUTS_DATA_DIR, "custom_shortcuts.json")
PREDEFINED_SHORTCUTS_FILE = os.path.join(
    SHORTCUTS_DATA_DIR, "predefined_shortcuts.json"
)


def open_link_js(url: str, text: str = "Abriendo enlace...") -> str:
    """Generate JavaScript to open a link in a new tab."""
    return f"""
    <script>
        window.open('{url}', '_blank');
    </script>
    <div style="color: #10B981; font-weight: 500; text-align: center; padding: 8px;">
        {text}
    </div>
    """


def load_predefined_shortcuts(logger=None):
    """Load predefined shortcuts from JSON file."""
    try:
        os.makedirs(SHORTCUTS_DATA_DIR, exist_ok=True)

        if os.path.exists(PREDEFINED_SHORTCUTS_FILE):
            with open(PREDEFINED_SHORTCUTS_FILE, encoding="utf-8") as f:
                shortcuts = json.load(f)
            return shortcuts
        else:
            if logger:
                logger.error(
                    f"Predefined shortcuts file not found at {PREDEFINED_SHORTCUTS_FILE}"
                )
            return {}
    except Exception as e:
        if logger:
            logger.error(f"Error loading predefined shortcuts: {e!s}")
        return {}


def load_custom_shortcuts(logger=None):
    """Load custom shortcuts from JSON file."""
    try:
        os.makedirs(SHORTCUTS_DATA_DIR, exist_ok=True)

        if os.path.exists(CUSTOM_SHORTCUTS_FILE):
            with open(CUSTOM_SHORTCUTS_FILE, encoding="utf-8") as f:
                shortcuts = json.load(f)
            return shortcuts
        else:
            return []
    except Exception as e:
        if logger:
            logger.error(f"Error loading custom shortcuts: {e!s}")
        return []


def save_custom_shortcuts(shortcuts, logger=None):
    """Save custom shortcuts to JSON file."""
    try:
        os.makedirs(SHORTCUTS_DATA_DIR, exist_ok=True)

        with open(CUSTOM_SHORTCUTS_FILE, "w", encoding="utf-8") as f:
            json.dump(shortcuts, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        if logger:
            logger.error(f"Error saving custom shortcuts: {e!s}")
        return False


def render_shortcuts_section(logger=None):
    """Render the shortcuts section."""
    predefined_shortcuts = load_predefined_shortcuts(logger)

    if "custom_shortcuts" not in st.session_state:
        st.session_state.custom_shortcuts = load_custom_shortcuts(logger)

    # Search bar
    search = st.text_input(
        "🔍 Buscar acceso directo", placeholder="Buscar por nombre o descripción..."
    )

    # Combine all shortcuts for search
    all_shortcuts = []
    for category, shortcuts in predefined_shortcuts.items():
        for shortcut in shortcuts:
            shortcut_with_category = shortcut.copy()
            shortcut_with_category["category"] = category
            all_shortcuts.append(shortcut_with_category)

    for shortcut in st.session_state.custom_shortcuts:
        shortcut_with_category = shortcut.copy()
        shortcut_with_category["category"] = "Personalizados"
        all_shortcuts.append(shortcut_with_category)

    # Filter shortcuts if search is not empty
    if search:
        filtered_shortcuts = [
            s
            for s in all_shortcuts
            if (
                search.lower() in s["name"].lower()
                or search.lower() in s["description"].lower()
                or search.lower() in s["category"].lower()
            )
        ]

        if not filtered_shortcuts:
            st.warning(
                f"No se encontraron accesos directos que coincidan con '{search}'"
            )
        else:
            result_cols = st.columns(3)
            for i, shortcut in enumerate(filtered_shortcuts):
                with result_cols[i % 3]:
                    st.markdown(
                        f"""
                    <a href="{shortcut["url"]}" target="_blank" style="text-decoration: none;">
                        <div class="shortcut-item">
                            <div class="shortcut-icon">{shortcut["icon"]}</div>
                            <div class="shortcut-content">
                                <div class="shortcut-title">{shortcut["name"]} <span style="opacity: 0.6; font-size: 12px;">({shortcut["category"]})</span></div>
                                <div class="shortcut-description">{shortcut["description"]}</div>
                            </div>
                        </div>
                    </a>
                    """,
                        unsafe_allow_html=True,
                    )
    else:
        # Display categories
        col1, col2, col3 = st.columns(3)

        all_categories = list(predefined_shortcuts.keys())
        custom_categories = set()
        for shortcut in st.session_state.custom_shortcuts:
            category = shortcut.get("category", "Personalizados")
            if category not in predefined_shortcuts:
                custom_categories.add(category)

        all_categories.extend(sorted(custom_categories))

        for i, category in enumerate(all_categories):
            column = col1 if i % 3 == 0 else col2 if i % 3 == 1 else col3
            with column:
                st.markdown('<div class="shortcuts-category">', unsafe_allow_html=True)
                st.markdown(f"<h3>{category}</h3>", unsafe_allow_html=True)

                # Display predefined shortcuts
                if category in predefined_shortcuts:
                    for shortcut in predefined_shortcuts[category]:
                        st.markdown(
                            f'''
                        <a href="{shortcut["url"]}" target="_blank" style="text-decoration: none;">
                            <div class="shortcut-item">
                                <div class="shortcut-icon">{shortcut["icon"]}</div>
                                <div class="shortcut-content">
                                    <div class="shortcut-title">{shortcut["name"]}</div>
                                    <div class="shortcut-description">{shortcut["description"]}</div>
                                </div>
                            </div>
                        </a>
                        ''',
                            unsafe_allow_html=True,
                        )

                # Display custom shortcuts
                custom_shortcuts_in_category = [
                    s
                    for s in st.session_state.custom_shortcuts
                    if s.get("category", "Personalizados") == category
                ]

                for i, shortcut in enumerate(custom_shortcuts_in_category):
                    if category in predefined_shortcuts:
                        st.markdown(
                            f'''
                        <a href="{shortcut["url"]}" target="_blank" style="text-decoration: none;">
                            <div class="shortcut-item">
                                <div class="shortcut-icon">{shortcut["icon"]}</div>
                                <div class="shortcut-content">
                                    <div class="shortcut-title">{shortcut["name"]}</div>
                                    <div class="shortcut-description">{shortcut["description"]}</div>
                                </div>
                            </div>
                        </a>
                        ''',
                            unsafe_allow_html=True,
                        )
                    else:
                        c1, c2 = st.columns([5, 1])
                        with c1:
                            st.markdown(
                                f'''
                            <a href="{shortcut["url"]}" target="_blank" style="text-decoration: none;">
                                <div class="shortcut-item">
                                    <div class="shortcut-icon">{shortcut["icon"]}</div>
                                    <div class="shortcut-content">
                                        <div class="shortcut-title">{shortcut["name"]}</div>
                                        <div class="shortcut-description">{shortcut["description"]}</div>
                                    </div>
                                </div>
                            </a>
                            ''',
                                unsafe_allow_html=True,
                            )
                        with c2:
                            original_index = st.session_state.custom_shortcuts.index(
                                shortcut
                            )
                            if st.button(
                                "❌",
                                key=f"del_main_{category}_{original_index}",
                                help="Eliminar",
                            ):
                                st.session_state.custom_shortcuts.pop(original_index)
                                save_custom_shortcuts(
                                    st.session_state.custom_shortcuts, logger
                                )
                                st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)


def render_shortcuts_management(logger=None):
    """Render shortcuts management."""
    manage_tab1, manage_tab2 = st.tabs(["Añadir enlace", "Exportar/Importar"])

    with manage_tab1, st.form("add_custom_shortcut"):
        st.subheader("Añadir enlace personalizado")

        col1, col2 = st.columns([1, 1])
        with col1:
            custom_name = st.text_input("Nombre", placeholder="Nombre del enlace")
            custom_icon = st.text_input("Icono (emoji)", placeholder="🔗", max_chars=2)
            custom_category = st.text_input("Categoría", placeholder="Personalizados")

        with col2:
            custom_url = st.text_input("URL", placeholder="https://example.com")
            custom_desc = st.text_input("Descripción", placeholder="Breve descripción")

        submitted = st.form_submit_button("Añadir enlace")
        if submitted and custom_name and custom_url:
            st.session_state.custom_shortcuts.append(
                {
                    "name": custom_name,
                    "url": custom_url,
                    "icon": custom_icon if custom_icon else "🔗",
                    "description": custom_desc
                    if custom_desc
                    else "Enlace personalizado",
                    "category": custom_category
                    if custom_category
                    else "Personalizados",
                }
            )
            save_custom_shortcuts(st.session_state.custom_shortcuts, logger)
            st.success(f"Enlace '{custom_name}' añadido")
            st.rerun()

    with manage_tab2:
        export_tab, import_tab = st.tabs(["Exportar", "Importar"])

        with export_tab:
            if st.session_state.custom_shortcuts:
                json_data = json.dumps(
                    st.session_state.custom_shortcuts, indent=4, ensure_ascii=False
                )
                st.download_button(
                    label="Descargar como JSON",
                    data=json_data,
                    file_name=f"shortcuts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                )
            else:
                st.info("No hay accesos directos para exportar.")

        with import_tab:
            uploaded_file = st.file_uploader("Subir archivo JSON", type=["json"])

            if uploaded_file is not None:
                try:
                    file_content = uploaded_file.read().decode("utf-8")
                    imported_shortcuts = json.loads(file_content)

                    if isinstance(imported_shortcuts, list):
                        valid_shortcuts = []
                        for shortcut in imported_shortcuts:
                            if isinstance(shortcut, dict) and all(
                                key in shortcut for key in ["name", "url"]
                            ):
                                if "icon" not in shortcut:
                                    shortcut["icon"] = "🔗"
                                if "description" not in shortcut:
                                    shortcut["description"] = "Enlace importado"
                                if "category" not in shortcut:
                                    shortcut["category"] = "Importados"
                                valid_shortcuts.append(shortcut)

                        if valid_shortcuts:
                            if st.button(
                                f"Importar {len(valid_shortcuts)} enlaces",
                                type="primary",
                            ):
                                st.session_state.custom_shortcuts.extend(
                                    valid_shortcuts
                                )
                                save_custom_shortcuts(
                                    st.session_state.custom_shortcuts, logger
                                )
                                st.success(
                                    f"¡{len(valid_shortcuts)} enlaces importados!"
                                )
                                st.rerun()
                        else:
                            st.error("No se encontraron enlaces válidos.")
                    else:
                        st.error("El archivo debe contener una lista de objetos JSON.")

                except json.JSONDecodeError:
                    st.error("Error al leer el archivo JSON.")
                except Exception as e:
                    st.error(f"Error al importar: {e!s}")


def render(logger=None, data_service=None):
    """Render the shortcuts tab."""
    st.header("🔖 Accesos Directos")

    # Render shortcuts section
    render_shortcuts_section(logger)

    # Render management section
    st.markdown("---")
    st.markdown("### ⚙️ Gestión de Enlaces")
    render_shortcuts_management(logger)
