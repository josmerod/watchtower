import streamlit as st
from typing import List
from src.models.anime import AnimeItem

def render_anime_item(anime: AnimeItem, col_index: int):
    """
    Renders a single anime item within a Streamlit container.
    Args:
        anime: The AnimeItem Pydantic model instance.
        col_index: An identifier for the column or item, not strictly used for layout here
                   but can be useful for unique keys if needed later.
    """
    with st.container():
        st.subheader(anime.title)

        if anime.main_picture and anime.main_picture.get('large'):
            st.image(anime.main_picture['large'], width=200)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Score", value=f"{anime.mean:.2f}" if anime.mean else "N/A")
        with col2:
            st.metric(label="Rank", value=f"#{anime.rank}" if anime.rank else "N/A")
        with col3:
            st.metric(label="Popularity", value=f"#{anime.popularity}" if anime.popularity else "N/A")

        with st.expander("Synopsis and Details"):
            if anime.synopsis:
                st.markdown(anime.synopsis)
            else:
                st.write("No synopsis available.")

            st.divider()

            details_md = f"""
            - **Episodes**: {anime.num_episodes if anime.num_episodes else 'N/A'}
            - **Media Type**: {anime.media_type.capitalize() if anime.media_type else 'N/A'}
            - **Status**: {anime.status.replace('_', ' ').capitalize() if anime.status else 'N/A'}
            - **Source**: {anime.source.capitalize() if anime.source else 'N/A'}
            - **Rating**: {anime.rating.upper().replace('_', '-') if anime.rating else 'N/A'}
            """
            st.markdown(details_md)

            if anime.genres:
                genres_str = ", ".join([genre['name'] for genre in anime.genres])
                st.markdown(f"- **Genres**: {genres_str}")

            if anime.studios:
                studios_str = ", ".join([studio['name'] for studio in anime.studios])
                st.markdown(f"- **Studios**: {studios_str}")

            if anime.start_season:
                season_str = f"{anime.start_season.get('season', '').capitalize()} {anime.start_season.get('year', '')}"
                st.markdown(f"- **Season**: {season_str.strip()}")

            if anime.broadcast:
                broadcast_str = f"{anime.broadcast.get('day_of_the_week','').capitalize()} at {anime.broadcast.get('start_time','')} JST"
                st.markdown(f"- **Broadcast**: {broadcast_str.strip()}")


def display_anime_section(title: str, anime_list: List[AnimeItem], num_columns: int = 3):
    """
    Displays a section of anime items in a grid layout.
    Args:
        title: The title for this section (e.g., "Current Season").
        anime_list: A list of AnimeItem objects to display.
        num_columns: Number of columns for the grid layout.
    """
    st.header(title)
    if not anime_list:
        st.info("No data available for this section or an error occurred while loading.")
        return

    # Create columns
    cols = st.columns(num_columns)

    for i, anime_item in enumerate(anime_list):
        with cols[i % num_columns]:
            render_anime_item(anime_item, col_index=i)
            st.markdown("---") # Visual separator between items in a column
