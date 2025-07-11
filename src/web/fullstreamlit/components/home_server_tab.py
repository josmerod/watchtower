# src/web/fullstreamlit/components/home_server_tab.py
import streamlit as st
import pandas as pd # Optional, if using dataframes

def render(logger, data_service):
    st.header("Home Server Trends & Applications")
    st.markdown("Discover popular and interesting self-hosted applications and trends relevant to home server enthusiasts, primarily sourced from the [awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted) list.")

    try:
        trends_data = data_service.get_home_server_trends_data()

        if not trends_data:
            st.info("No home server trend data is currently available. Please run the ETL process.")
            return

        # Convert list of dicts to DataFrame for easier display, if desired
        # df = pd.DataFrame(trends_data)
        # st.dataframe(df)
        # For more customized display:

        categories = sorted(list(set(item['category'] for item in trends_data)))
        selected_category = st.selectbox("Filter by Category:", ["All"] + categories)

        filtered_data = trends_data
        if selected_category != "All":
            filtered_data = [item for item in trends_data if item['category'] == selected_category]

        if not filtered_data:
            st.info(f"No items found for category: {selected_category}")
            return

        for item in filtered_data:
            with st.expander(f"{item['name']} ({item['category']})"):
                st.markdown(f"**Description:** {item['description']}")
                st.markdown(f"**URL:** [{item['url']}]({item['url']})")
                if item.get('tags'):
                    st.markdown(f"**Tags:** `{'`, `'.join(item['tags'])}`")
                st.markdown(f"<small>Source: {item['source']} | Added: {item['added_date']}</small>", unsafe_allow_html=True)

        logger.info(f"Rendered home_server_tab with {len(filtered_data)} items for category '{selected_category}'.")

    except Exception as e:
        logger.error(f"Error rendering home_server_tab: {e}")
        st.error("Could not load home server trends data.")
