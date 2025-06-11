import streamlit as st
from typing import List, Dict, Any
import logging
from datetime import datetime

def render(logger: logging.Logger, posts_data: List[Dict[str, Any]]) -> None:
    """
    Renders the Azure Training (Microsoft Learn) blog posts tab.

    Args:
        logger: The logger instance.
        posts_data: A list of dictionaries, where each dictionary is an Azure blog post.
    """
    logger.info("Rendering Azure Training tab.")
    # TODO: Add keyword/date filters here, e.g., st.text_input for keywords, st.date_input for date range

    try:
        if not posts_data:
            st.info("No Azure training updates found or an error occurred while loading the data.")
            logger.info("No Azure training data to display.")
            return

        st.header("Azure Training & Certification Blog Updates (Microsoft Learn)") # Updated Header
        st.markdown(f"Displaying **{len(posts_data)}** latest updates.")
        st.markdown("---")

        for post in posts_data:
            title = post.get("title", "No Title Available")
            link = post.get("link", "#")
            published_str = post.get("published", "No Date Available")
            summary = post.get("summary", "No summary available.")
            categories = post.get("categories", [])

            st.subheader(f"[{title}]({link})")

            if published_str and published_str != "No Date Available":
                try:
                    dt_obj = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                    st.caption(f"Published: {dt_obj.strftime('%B %d, %Y, %H:%M %Z')}")
                except ValueError:
                    st.caption(f"Published: {published_str}")
            else:
                st.caption(f"Published: {published_str}")

            if isinstance(categories, list) and len(categories) > 0:
                st.caption(f"Categories: {', '.join(categories)}")
            elif isinstance(categories, str) and categories:
                st.caption(f"Categories: {categories}")
            else:
                st.caption("Categories: Not available")

            if summary:
                with st.expander("View Summary/Description", expanded=False):
                    st.markdown(summary, unsafe_allow_html=True)

            st.markdown("---")

        logger.info(f"Successfully rendered {len(posts_data)} Azure training posts.")

    except Exception as e:
        logger.error(f"An error occurred in the Azure Training tab: {e}", exc_info=True)
        st.error("An unexpected error occurred while rendering Azure training updates. Please check the logs for more details.")

if __name__ == '__main__':
    # Mock setup for local testing
    mock_logger_main = logging.getLogger("AzureTabTest")
    mock_logger_main.setLevel(logging.INFO)
    if not mock_logger_main.hasHandlers():
        mock_logger_main.addHandler(logging.StreamHandler())

    sample_azure_posts = [
        {
            "source": "azure_microsoft_learn_blog",
            "title": "New Azure Fundamentals Certification Path",
            "link": "https://learn.microsoft.com/en-us/blogs/new-azure-fundamentals",
            "published": "2023-10-01T09:00:00Z",
            "summary": "Explore the revamped AZ-900 certification with new learning modules and hands-on labs.",
            "categories": ["Azure Fundamentals", "Certification", "Microsoft Learn"]
        },
        {
            "source": "azure_microsoft_learn_blog",
            "title": "Advanced AI on Azure: Workshop Series",
            "link": "https://learn.microsoft.com/en-us/blogs/advanced-ai-azure",
            "published": "2023-09-25T14:30:00+01:00", # Example with different timezone
            "summary": "Join our free workshop series to dive deep into Azure AI capabilities.",
            "categories": ["Azure AI", "Workshop", "Advanced"]
        }
    ]

    st.set_page_config(layout="wide")
    render(logger=mock_logger_main, posts_data=sample_azure_posts)

    st.header("Test with No Data (Azure)")
    render(logger=mock_logger_main, posts_data=[])