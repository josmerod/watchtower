import pandas as pd
import streamlit as st


def render(logger, museum_data: pd.DataFrame):
    st.title("🏛️ Directorio de Museos Virtuales")

    if museum_data is None or museum_data.empty:
        st.info("No hay datos de museos virtuales disponibles en este momento.")
        logger.info("Render de museos: No hay datos disponibles.")
        return

    logger.info(f"Renderizando datos de {len(museum_data)} museos virtuales.")

    # --- Search and Filters ---
    st.sidebar.header("Filtros para Museos")
    search_query = st.sidebar.text_input("Buscar por nombre o descripción", key="museum_search")

    # Filter by country (if 'country_label' column exists and has data)
    if 'country_label' in museum_data.columns and museum_data['country_label'].nunique() > 0:
        unique_countries = sorted(museum_data['country_label'].dropna().unique().astype(str))
        selected_country = st.sidebar.selectbox("Filtrar por País", ["Todos", *unique_countries], index=0, key="museum_country_filter")
    else:
        selected_country = "Todos"
        if 'country_label' not in museum_data.columns:
            logger.debug("Columna 'country_label' no encontrada para el filtro de país.")
        else:
            logger.debug("No hay valores únicos en 'country_label' para el filtro de país.")


    # Filter by main subject (if 'main_subject_label' column exists and has data)
    if 'main_subject_label' in museum_data.columns and museum_data['main_subject_label'].nunique() > 0:
        unique_subjects = sorted(museum_data['main_subject_label'].dropna().unique().astype(str))
        selected_subject = st.sidebar.selectbox("Filtrar por Temática Principal", ["Todos", *unique_subjects], index=0, key="museum_subject_filter")
    else:
        selected_subject = "Todos"
        if 'main_subject_label' not in museum_data.columns:
            logger.debug("Columna 'main_subject_label' no encontrada para el filtro de temática.")
        else:
            logger.debug("No hay valores únicos en 'main_subject_label' para el filtro de temática.")


    # Apply filters
    filtered_data = museum_data.copy()
    if search_query:
        # Search in name and description (case-insensitive)
        # Ensure description is string type for .str accessor
        description_series = pd.Series([False]*len(filtered_data))
        if 'description' in filtered_data.columns:
             filtered_data['description_str'] = filtered_data['description'].astype(str) # Use a new column to avoid type issues
             description_series = filtered_data['description_str'].str.contains(search_query, case=False, na=False)

        name_series = pd.Series([False]*len(filtered_data))
        if 'name' in filtered_data.columns:
            name_series = filtered_data['name'].astype(str).str.contains(search_query, case=False, na=False)

        filtered_data = filtered_data[name_series | description_series]
        if 'description_str' in filtered_data.columns: # Clean up temporary column
            filtered_data = filtered_data.drop(columns=['description_str'])

    if selected_country != "Todos" and 'country_label' in filtered_data.columns:
        filtered_data = filtered_data[filtered_data['country_label'] == selected_country]
    if selected_subject != "Todos" and 'main_subject_label' in filtered_data.columns:
        filtered_data = filtered_data[filtered_data['main_subject_label'] == selected_subject]

    st.metric("Total de Museos Encontrados", len(filtered_data))

    if filtered_data.empty:
        st.warning("No se encontraron museos que coincidan con los filtros aplicados.")
        return

    # --- Display Data ---
    # Define number of columns for layout
    cols_per_row = 3 # Define how many columns per row

    # Calculate how many items per column, approximately
    # This is a simple way, could be improved for more balanced columns
    len(filtered_data)

    # Create columns
    cols = st.columns(cols_per_row)
    col_idx = 0

    for _index, museum in filtered_data.iterrows():
        current_col = cols[col_idx % cols_per_row]
        with current_col:
            with st.container(border=True): # Added border=True for better visual separation
                st.subheader(museum.get('name', 'Nombre no disponible'))

                if pd.notna(museum.get('image_url')):
                    st.image(museum['image_url'], use_column_width='always') # Changed to 'always'

                details_expander = st.expander("Más Detalles", expanded=False)
                with details_expander:
                    if pd.notna(museum.get('description')) and museum.get('description'):
                        st.markdown(f"**Descripción:** {museum['description']}")

                    if pd.notna(museum.get('country_label')) and museum.get('country_label'):
                        st.markdown(f"**País:** {museum['country_label']}")
                    if pd.notna(museum.get('city_label')) and museum.get('city_label'):
                        st.markdown(f"**Ciudad:** {museum['city_label']}")
                    if pd.notna(museum.get('main_subject_label')) and museum.get('main_subject_label'):
                        st.markdown(f"**Temática Principal:** {museum['main_subject_label']}")

                    links_html = []
                    if pd.notna(museum.get('website_url')) and museum.get('website_url'):
                        links_html.append(f"<a href='{museum['website_url']}' target='_blank'>Sitio Web</a>")
                    if pd.notna(museum.get('virtual_tour_url')) and museum.get('virtual_tour_url'):
                        links_html.append(f"<a href='{museum['virtual_tour_url']}' target='_blank'>Tour Virtual</a>")
                    if pd.notna(museum.get('wikidata_url')) and museum.get('wikidata_url'):
                        links_html.append(f"<a href='{museum['wikidata_url']}' target='_blank'>Wikidata</a>")

                    if links_html:
                        st.markdown(" | ".join(links_html), unsafe_allow_html=True)

                    st.caption(f"ID: {museum.get('id', 'N/A')} | Fuente: {museum.get('data_source', 'N/A')}")
        col_idx +=1

    # Add some padding at the bottom if needed
    st.markdown("---")
    logger.info(f"Mostrando {len(filtered_data)} museos después de aplicar filtros.")
