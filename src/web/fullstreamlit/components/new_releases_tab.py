import streamlit as st
import pandas as pd
from utils.logging import get_logger # Assuming logger is passed or fetched

# If a logger instance is not passed, you can initialize one like this:
# logger = get_logger(__name__) # Or use a more specific name

def render(new_releases_df: pd.DataFrame, logger) -> None:
    """
    Renders the new game releases tab.

    Args:
        new_releases_df: DataFrame containing new game releases.
        logger: Logger instance for logging messages.
    """
    try:
        if new_releases_df is None or new_releases_df.empty:
            st.info("No hay nuevos lanzamientos disponibles en este momento.")
            logger.info("New releases DataFrame is empty or None, displaying info message.")
            return

        st.subheader("Próximos Lanzamientos y Novedades")

        # Sort by release date if the column exists, most recent/upcoming first
        if 'released' in new_releases_df.columns:
            try:
                # Attempt to convert to datetime if not already, handle errors
                new_releases_df['released_dt'] = pd.to_datetime(new_releases_df['released'], errors='coerce')
                # Sort by the new datetime column, NaT values (errors in conversion) will be last
                sorted_df = new_releases_df.sort_values(by="released_dt", ascending=False).drop(columns=['released_dt'])
            except Exception as e:
                logger.warning(f"Could not sort by release date due to error: {e}. Displaying unsorted.")
                sorted_df = new_releases_df # Fallback to unsorted
        else:
            logger.info("No 'released' column found in new_releases_df. Displaying unsorted.")
            sorted_df = new_releases_df

        if sorted_df.empty: # Check again after potential filtering by bad dates
            st.info("No hay nuevos lanzamientos disponibles con fechas válidas.")
            return

        for game in sorted_df.itertuples():
            with st.expander(f"{getattr(game, 'name', 'Nombre no disponible')}"):
                st.markdown(f"**Título:** {getattr(game, 'name', 'N/A')}")

                release_date = getattr(game, 'released', 'Fecha no disponible')
                if pd.isna(release_date):
                    release_date = 'Fecha no disponible'
                elif isinstance(release_date, str): # Already string
                    pass
                elif hasattr(release_date, 'strftime'): # datetime object
                     release_date = release_date.strftime('%Y-%m-%d')
                else: # Other types
                    release_date = str(release_date)
                st.markdown(f"**Fecha de Lanzamiento:** {release_date}")

                platforms_list = getattr(game, 'platforms', [])
                if isinstance(platforms_list, list):
                    platforms_str = ', '.join(platforms_list) if platforms_list else "No especificadas"
                elif isinstance(platforms_list, str): # If it's already a string (e.g. from bad parsing upstream)
                    platforms_str = platforms_list if platforms_list else "No especificadas"
                else: # Other types
                    platforms_str = str(platforms_list) if platforms_list is not None else "No especificadas"
                st.markdown(f"**Plataformas:** {platforms_str}")

                metacritic_score = getattr(game, 'metacritic', 'N/A')
                st.markdown(f"**Puntuación Metacritic:** {metacritic_score if pd.notna(metacritic_score) else 'N/A'}")

                rawg_link = getattr(game, 'rawg_link', None)
                if rawg_link and pd.notna(rawg_link):
                    st.markdown(f"**Enlace RAWG:** [Ver en RAWG]({rawg_link})", unsafe_allow_html=True)
                else:
                    st.markdown("**Enlace RAWG:** No disponible")

                description = getattr(game, 'description_raw', "No hay descripción disponible.")
                st.caption(description if pd.notna(description) and description else "No hay descripción disponible.")

        logger.info(f"Successfully rendered {len(sorted_df)} new game releases.")

    except Exception as e:
        logger.error(f"Error rendering new releases tab: {e}", exc_info=True)
        st.error("Ocurrió un error al mostrar los nuevos lanzamientos.")
