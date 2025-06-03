"""
Games tab component for the Watchtower Streamlit application.
Displays game deals, bundles, and giveaways.
"""

import streamlit as st
import pandas as pd
# from src.web.fullstreamlit.utils.helpers import make_clickable # Removed
from . import new_releases_tab # Added import

def render(deals_df, bundles_df, giveaways_df, trending_df, new_releases_df, logger=None):
    """Render the games tab"""
    st.header("🎮 Juegos")

    # Check if all dataframes are empty
    if (deals_df.empty and bundles_df.empty and giveaways_df.empty and 
        trending_df.empty and (new_releases_df is None or new_releases_df.empty)):
        if logger:
            logger.warning("No game data available to display (deals, bundles, giveaways, trending, new releases).")
        st.warning("No hay datos de juegos disponibles para mostrar.")
        return # Exit if no data

    # Create tabs for different game sections
    tab_titles = []
    if not giveaways_df.empty:
        tab_titles.append("Juegos Gratuitos")
    if not bundles_df.empty:
        tab_titles.append("Paquetes de Juegos")
    if not deals_df.empty:
        tab_titles.append("Ofertas de Juegos")
    if not trending_df.empty:
        tab_titles.append("Tendencias Itch.io")
    if new_releases_df is not None and not new_releases_df.empty:
        tab_titles.append("Nuevos Lanzamientos")

    if not tab_titles: # Should not happen if the initial check passed, but good practice
        st.warning("No hay datos de juegos válidos para mostrar en las pestañas.")
        return

    tabs = st.tabs(tab_titles)
    tab_map = {title: tab for title, tab in zip(tab_titles, tabs)}

    # Display content within each tab
    if "Juegos Gratuitos" in tab_map:
        with tab_map["Juegos Gratuitos"]:
            display_giveaways(giveaways_df)

    if "Paquetes de Juegos" in tab_map:
        with tab_map["Paquetes de Juegos"]:
            display_bundles(bundles_df)

    if "Ofertas de Juegos" in tab_map:
        with tab_map["Ofertas de Juegos"]:
            display_deals(deals_df)

    if "Tendencias Itch.io" in tab_map:
        with tab_map["Tendencias Itch.io"]:
            display_trending(trending_df)

    if "Nuevos Lanzamientos" in tab_map:
        with tab_map["Nuevos Lanzamientos"]:
            new_releases_tab.render(new_releases_df, logger)

    # Removed the multiselect and the old sequential display logic.
    # The container div is also removed as tabs handle the layout.


def display_deals(deals_df):
    """Display game deals"""
    if deals_df.empty:
        st.info("No hay ofertas de juegos disponibles en este momento.")
        return

    filtered_deals_df = deals_df.copy()
    available_columns = filtered_deals_df.columns.tolist()

    # Determine title column
    title_col_actual = None
    if "title" in available_columns:
        title_col_actual = "title"
    elif "name" in available_columns:
        title_col_actual = "name"

    if not title_col_actual:
        st.error("Los datos de ofertas no tienen una columna de título ('title' or 'name').")
        return

    # Define source columns for selection
    source_columns_to_select = [title_col_actual]
    if "store" in available_columns:
        source_columns_to_select.append("store")
    if "price" in available_columns:
        source_columns_to_select.append("price")
    if "discount" in available_columns: # This is often a string like "-90%"
        source_columns_to_select.append("discount")
    if "published_date" in available_columns:
        source_columns_to_select.append("published_date")
    if "link" in available_columns: # Needed for the clickable link
        source_columns_to_select.append("link")

    # Sort by discount value if available (assuming 'discount_value' is numeric for sorting)
    if "discount_value" in available_columns:
        filtered_deals_df = filtered_deals_df.sort_values(by="discount_value", ascending=False)

    display_deals_df = filtered_deals_df[source_columns_to_select].copy()

    # Format price
    if "price" in display_deals_df.columns:
        display_deals_df["price"] = display_deals_df["price"].apply(
            lambda x: f"€{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else x
        )

    # Rename columns
    rename_map = {
        title_col_actual: "Título",
        "store": "Tienda",
        "price": "Precio",
        "discount": "Descuento",
        "published_date": "Fecha de Publicación",
        "link": "URL_Enlace"  # Raw URL column
    }

    # Select only the source columns that exist and are needed, then rename
    actual_source_columns_for_rename = [col for col in rename_map.keys() if col in display_deals_df.columns]
    df_for_editor = display_deals_df[actual_source_columns_for_rename].copy()
    df_for_editor.rename(columns=rename_map, inplace=True)

    # Final column order for data_editor
    final_columns_ordered = ["Título", "Tienda", "Precio", "Descuento", "Fecha de Publicación", "URL_Enlace"]

    # Filter to include only columns present in df_for_editor
    columns_for_editor_display = [col for col in final_columns_ordered if col in df_for_editor.columns]
    df_for_editor = df_for_editor[columns_for_editor_display]

    st.write(f"Mostrando {len(df_for_editor)} ofertas")
    st.data_editor(
        df_for_editor,
        column_config={
            "Título": st.column_config.TextColumn(width="medium", help="Título del juego"),
            "Tienda": st.column_config.TextColumn(width="small", help="Tienda de la oferta"),
            "Precio": st.column_config.TextColumn(width="small", help="Precio actual"),
            "Descuento": st.column_config.TextColumn(width="small", help="Porcentaje de descuento"),
            "Fecha de Publicación": st.column_config.TextColumn(width="small", help="Fecha de publicación de la oferta"),
            "URL_Enlace": st.column_config.LinkColumn(label="Enlace", display_text="Ver Oferta", width="small", help="Enlace directo a la oferta")
        },
        disabled=True,
        hide_index=True,
        use_container_width=True
    )

    if not df_for_editor.empty:
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Descargar CSV (Ofertas)",
                data=df_for_editor.to_csv(index=False).encode('utf-8'),
                file_name="game_deals_data.csv",
                mime='text/csv',
                key="csv_download_deals"
            )
        with col2:
            st.download_button(
                label="📥 Descargar JSON (Ofertas)",
                data=df_for_editor.to_json(orient='records', indent=2).encode('utf-8'),
                file_name="game_deals_data.json",
                mime='application/json',
                key="json_download_deals"
            )

def display_bundles(bundles_df):
    """Display game bundles"""
    if bundles_df.empty:
        st.info("No hay paquetes de juegos disponibles en este momento.")
        return

    filtered_bundles_df = bundles_df.copy()
    available_columns = filtered_bundles_df.columns.tolist()

    title_col_actual = "title" if "title" in available_columns else "name"
    if not title_col_actual:
        st.error("Los datos de paquetes no tienen una columna de título.")
        return

    with st.expander("Filtros y Opciones para Paquetes", expanded=False):
        group_col_actual = None
        if "store" in available_columns: # Prioritize 'store' as filter key
            group_col_actual = "store"
        elif "type" in available_columns:
            group_col_actual = "type"

        if group_col_actual:
            unique_groups = sorted(filtered_bundles_df[group_col_actual].dropna().unique().tolist())
            options = ["Todos"] + unique_groups
            selected_group = st.selectbox(
                f"Filtrar por {group_col_actual.replace('_', ' ').capitalize()}:",
                options=options,
                index=0,
                key="bundle_filter_selectbox"
            )
            if selected_group != "Todos":
                filtered_bundles_df = filtered_bundles_df[filtered_bundles_df[group_col_actual] == selected_group]

    # Determine date column and its display name
    date_col_actual = None
    date_col_display_name = None
    if "published_date" in available_columns:
        date_col_actual = "published_date"
        date_col_display_name = "Fecha de Publicación"
    elif "end_date" in available_columns:
        date_col_actual = "end_date"
        date_col_display_name = "Fecha de Expiración"

    if date_col_actual: # Sort by date if available
        filtered_bundles_df[date_col_actual] = pd.to_datetime(filtered_bundles_df[date_col_actual], errors='coerce')
        filtered_bundles_df = filtered_bundles_df.sort_values(by=date_col_actual, ascending=False)
    else: # Fallback sort by title
        filtered_bundles_df = filtered_bundles_df.sort_values(by=title_col_actual)

    # Add game_count if 'games' list exists and 'game_count' doesn't
    if "game_count" not in available_columns and "games" in available_columns:
        filtered_bundles_df["game_count"] = filtered_bundles_df["games"].apply(lambda x: len(x) if isinstance(x, list) else 0)
        available_columns.append("game_count") # Add to available if created

    # Select columns for display
    source_columns_to_select = [title_col_actual]
    if "store" in available_columns: source_columns_to_select.append("store")
    if "game_count" in available_columns: source_columns_to_select.append("game_count")
    if "price" in available_columns: source_columns_to_select.append("price")
    if "type" in available_columns: source_columns_to_select.append("type") # This is bundle category like "Humble Choice"
    if date_col_actual: source_columns_to_select.append(date_col_actual)
    if "link" in available_columns: source_columns_to_select.append("link")

    # Ensure no duplicates if title_col_actual or date_col_actual is already in the list by name
    source_columns_to_select = sorted(list(set(source_columns_to_select)), key=source_columns_to_select.index)


    display_bundles_df_intermediate = filtered_bundles_df[source_columns_to_select].copy()

    # Price formatting (moved before rename)
    if "price" in display_bundles_df_intermediate.columns:
        display_bundles_df_intermediate["price"] = display_bundles_df_intermediate["price"].apply(
            lambda x: f"€{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else x
        )

    if date_col_actual and date_col_actual in display_bundles_df_intermediate.columns:
         if pd.api.types.is_datetime64_any_dtype(display_bundles_df_intermediate[date_col_actual]):
            display_bundles_df_intermediate[date_col_actual] = display_bundles_df_intermediate[date_col_actual].dt.strftime('%Y-%m-%d')

    # Prepare df_for_editor
    df_for_editor_rename_map = {
        title_col_actual: "Título",
        "store": "Fuente",
        "game_count": "Juegos", # Renamed as per instruction
        "price": "Precio",
        "type": "Tipo",
        "link": "URL_Enlace"
    }
    # Add the actual date column to the rename map, using its display name as the target
    # This ensures the column in df_for_editor has the name like "Fecha de Publicación"
    if date_col_actual and date_col_display_name:
        df_for_editor_rename_map[date_col_actual] = date_col_display_name

    actual_source_columns_for_rename = [col for col in df_for_editor_rename_map.keys() if col in display_bundles_df_intermediate.columns]
    df_for_editor = display_bundles_df_intermediate[actual_source_columns_for_rename].copy()
    df_for_editor.rename(columns=df_for_editor_rename_map, inplace=True)

    # Define final column order for data_editor
    # The date column now has its display name (e.g., "Fecha de Publicación") in df_for_editor
    final_columns_ordered = ["Título", "Fuente", "Juegos", "Precio", "Tipo"]
    if date_col_display_name and date_col_display_name in df_for_editor.columns:
        final_columns_ordered.append(date_col_display_name)
    final_columns_ordered.append("URL_Enlace")

    columns_for_editor_display = [col for col in final_columns_ordered if col in df_for_editor.columns]
    df_for_editor = df_for_editor[columns_for_editor_display]

    # Determine column config for 'Juegos' based on data type
    juegos_column_config = None
    if "Juegos" in df_for_editor.columns and pd.api.types.is_numeric_dtype(df_for_editor["Juegos"]):
        juegos_column_config = st.column_config.NumberColumn(width="small", help="Número de juegos en el paquete", format="%d")
    else:
        juegos_column_config = st.column_config.TextColumn(width="small", help="Número de juegos en el paquete")

    column_config_data_editor = {
        "Título": st.column_config.TextColumn(width="medium", help="Título del paquete"),
        "Fuente": st.column_config.TextColumn(width="small", help="Fuente/Origen del paquete"),
        "Juegos": juegos_column_config,
        "Precio": st.column_config.TextColumn(width="small", help="Precio del paquete"),
        "Tipo": st.column_config.TextColumn(width="small", help="Categoría del paquete"),
        "URL_Enlace": st.column_config.LinkColumn(label="Enlace", display_text="Ver Paquete", width="small", help="Enlace directo al paquete")
    }
    if date_col_display_name and date_col_display_name in df_for_editor.columns: # Add date to column_config if it exists
        column_config_data_editor[date_col_display_name] = st.column_config.TextColumn(label="Fecha", width="small", help="Fecha de publicación o expiración")

    st.write(f"Mostrando {len(df_for_editor)} paquetes de juegos")
    st.data_editor(
        df_for_editor,
        column_config=column_config_data_editor,
        disabled=True,
        hide_index=True,
        use_container_width=True
    )

    if not df_for_editor.empty:
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Descargar CSV (Paquetes)",
                data=df_for_editor.to_csv(index=False).encode('utf-8'),
                file_name="game_bundles_data.csv",
                mime='text/csv',
                key="csv_download_bundles"
            )
        with col2:
            st.download_button(
                label="📥 Descargar JSON (Paquetes)",
                data=df_for_editor.to_json(orient='records', indent=2).encode('utf-8'),
                file_name="game_bundles_data.json",
                mime='application/json',
                key="json_download_bundles"
            )

def display_giveaways(giveaways_df):
    """Display game giveaways"""
    if giveaways_df.empty:
        st.info("No hay juegos gratuitos disponibles en este momento.")
        return

    filtered_giveaways_df = giveaways_df.copy()
    available_columns = filtered_giveaways_df.columns.tolist()

    title_col_actual = None
    if "title" in available_columns: title_col_actual = "title"
    elif "name" in available_columns: title_col_actual = "name"

    if not title_col_actual:
        st.error("Los datos de juegos gratuitos no tienen columna de título.")
        return

    published_date_col_actual = None
    if "published_date" in available_columns: published_date_col_actual = "published_date"
    elif "date" in available_columns: published_date_col_actual = "date" # Fallback for 'date'

    # Select columns for display
    source_columns_to_select = [title_col_actual]
    if published_date_col_actual: source_columns_to_select.append(published_date_col_actual)
    if "expires_date" in available_columns: source_columns_to_select.append("expires_date")
    if "link" in available_columns: source_columns_to_select.append("link")

    # Ensure no duplicates
    source_columns_to_select = sorted(list(set(source_columns_to_select)), key=source_columns_to_select.index)

    display_giveaways_df = filtered_giveaways_df[source_columns_to_select].copy()

    # Format dates if they exist and are datetime objects
    if published_date_col_actual and published_date_col_actual in display_giveaways_df.columns and \
       pd.api.types.is_datetime64_any_dtype(display_giveaways_df[published_date_col_actual]):
        display_giveaways_df[published_date_col_actual] = display_giveaways_df[published_date_col_actual].dt.strftime('%Y-%m-%d')

    if "expires_date" in display_giveaways_df.columns and \
       pd.api.types.is_datetime64_any_dtype(display_giveaways_df[published_date_col_actual]):
        display_giveaways_df[published_date_col_actual] = display_giveaways_df[published_date_col_actual].dt.strftime('%Y-%m-%d')

    if "expires_date" in display_giveaways_df.columns and \
       pd.api.types.is_datetime64_any_dtype(display_giveaways_df["expires_date"]):
        display_giveaways_df["expires_date"] = display_giveaways_df["expires_date"].dt.strftime('%Y-%m-%d')

    # Prepare df_for_editor
    df_for_editor_rename_map = {
        title_col_actual: "Título",
        "link": "URL_Enlace"
    }
    if published_date_col_actual: # This is the original name of the column with published date
        df_for_editor_rename_map[published_date_col_actual] = "Publicado"
    if "expires_date" in display_giveaways_df.columns: # Check if original column exists before adding to map
        df_for_editor_rename_map["expires_date"] = "Expira"

    actual_source_columns_for_rename = [col for col in df_for_editor_rename_map.keys() if col in display_giveaways_df.columns]
    df_for_editor = display_giveaways_df[actual_source_columns_for_rename].copy()
    df_for_editor.rename(columns=df_for_editor_rename_map, inplace=True)

    # Define final column order for data_editor
    final_columns_ordered = ["Título"]
    if "Publicado" in df_for_editor.columns: final_columns_ordered.append("Publicado")
    if "Expira" in df_for_editor.columns: final_columns_ordered.append("Expira")
    final_columns_ordered.append("URL_Enlace")

    columns_for_editor_display = [col for col in final_columns_ordered if col in df_for_editor.columns]
    df_for_editor = df_for_editor[columns_for_editor_display]

    st.write(f"Mostrando {len(df_for_editor)} juegos gratuitos")
    st.data_editor(
        df_for_editor,
        column_config={
            "Título": st.column_config.TextColumn(width="medium", help="Título del juego gratuito"),
            "Publicado": st.column_config.TextColumn(width="small", help="Fecha de publicación del juego gratuito"),
            "Expira": st.column_config.TextColumn(width="small", help="Fecha de expiración de la oferta"),
            "URL_Enlace": st.column_config.LinkColumn(label="Enlace", display_text="Reclamar", width="small", help="Enlace para obtener el juego")
        },
        disabled=True,
        hide_index=True,
        use_container_width=True
    )

    if not df_for_editor.empty:
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Descargar CSV (Gratuitos)",
                data=df_for_editor.to_csv(index=False).encode('utf-8'),
                file_name="game_giveaways_data.csv",
                mime='text/csv',
                key="csv_download_giveaways"
            )
        with col2:
            st.download_button(
                label="📥 Descargar JSON (Gratuitos)",
                data=df_for_editor.to_json(orient='records', indent=2).encode('utf-8'),
                file_name="game_giveaways_data.json",
                mime='application/json',
                key="json_download_giveaways"
            )

def display_trending(trending_df):
    """Display Itch.io trending games"""
    if trending_df.empty:
        st.info("No hay tendencias de Itch.io disponibles en este momento.")
        return

    filtered_trending_df = trending_df.copy()
    available_columns = filtered_trending_df.columns.tolist()

    # Determine title column
    title_col_actual = None
    if "title" in available_columns:
        title_col_actual = "title"
    elif "name" in available_columns:
        title_col_actual = "name"

    if not title_col_actual:
        st.error("Los datos de tendencias no tienen una columna de título.")
        return

    # Select columns for display
    source_columns_to_select = [title_col_actual]
    if "author" in available_columns:
        source_columns_to_select.append("author")
    if "price" in available_columns:
        source_columns_to_select.append("price")
    if "description" in available_columns:
        source_columns_to_select.append("description")
    if "link" in available_columns:
        source_columns_to_select.append("link")

    display_trending_df = filtered_trending_df[source_columns_to_select].copy()

    # Format price
    if "price" in display_trending_df.columns:
        display_trending_df["price"] = display_trending_df["price"].apply(
            lambda x: f"€{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else x
        )

    # Rename columns
    rename_map = {
        title_col_actual: "Título",
        "author": "Autor",
        "price": "Precio",
        "description": "Descripción",
        "link": "URL_Enlace"
    }

    actual_source_columns_for_rename = [col for col in rename_map.keys() if col in display_trending_df.columns]
    df_for_editor = display_trending_df[actual_source_columns_for_rename].copy()
    df_for_editor.rename(columns=rename_map, inplace=True)

    # Final column order for data_editor
    final_columns_ordered = ["Título", "Autor", "Precio", "Descripción", "URL_Enlace"]
    columns_for_editor_display = [col for col in final_columns_ordered if col in df_for_editor.columns]
    df_for_editor = df_for_editor[columns_for_editor_display]

    # Truncate description for better display
    if "Descripción" in df_for_editor.columns:
        df_for_editor["Descripción"] = df_for_editor["Descripción"].apply(
            lambda x: x[:100] + "..." if isinstance(x, str) and len(x) > 100 else x
        )

    st.write(f"Mostrando {len(df_for_editor)} juegos en tendencia de Itch.io")
    st.data_editor(
        df_for_editor,
        column_config={
            "Título": st.column_config.TextColumn(width="medium", help="Título del juego"),
            "Autor": st.column_config.TextColumn(width="small", help="Autor/Desarrollador del juego"),
            "Precio": st.column_config.TextColumn(width="small", help="Precio del juego"),
            "Descripción": st.column_config.TextColumn(width="large", help="Descripción del juego"),
            "URL_Enlace": st.column_config.LinkColumn(label="Enlace", display_text="Ver Juego", width="small", help="Enlace al juego en Itch.io")
        },
        disabled=True,
        hide_index=True,
        use_container_width=True
    )

    if not df_for_editor.empty:
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Descargar CSV (Tendencias)",
                data=df_for_editor.to_csv(index=False).encode('utf-8'),
                file_name="itchio_trending_data.csv",
                mime='text/csv',
                key="csv_download_trending"
            )
        with col2:
            st.download_button(
                label="📥 Descargar JSON (Tendencias)",
                data=df_for_editor.to_json(orient='records', indent=2).encode('utf-8'),
                file_name="itchio_trending_data.json",
                mime='application/json',
                key="json_download_trending"
            )