import logging  # For logger type hint
from datetime import datetime
from typing import Any

import streamlit as st

# Assuming data_service_ultra_optimized has UltraOptimizedDataService
# This is for type hinting and would typically be imported if it's a separate module
# from web.fullstreamlit.utils.data_service_ultra_optimized import UltraOptimizedDataService

# Define keywords for filtering (case-insensitive)
KEYWORDS = [
    "skill",
    "skills",
    "training",
    "certification",
    "learn",
    "boost",
    "course",
    "courses",
    "badge",
    "prepare",
    "exam",
]


def render(logger: logging.Logger, posts_data: list[dict[str, Any]]) -> None:
    """Renders the Google Cloud Blog tab, displaying filtered blog posts
    related to training and certifications.

    Args:
        logger: The logger instance.
        posts_data: A list of dictionaries, where each dictionary is a blog post.
    """
    logger.info("Rendering Google Cloud Blog tab.")

    try:
        if not posts_data:
            st.info(
                "No Google Cloud Blog posts found or an error occurred while loading the data. Please check the logs or try again later."
            )
            logger.info("No Google Cloud Blog data to display.")
            return

        relevant_posts: list[dict[str, Any]] = []
        for post in posts_data:  # Iterate over posts_data directly
            title = post.get("title", "").lower()

            # Check categories if they exist and are a list of strings
            categories = post.get("categories", [])
            category_text = ""
            if isinstance(categories, list):
                category_text = " ".join(
                    str(cat).lower() for cat in categories if isinstance(cat, str)
                )
            elif isinstance(categories, str):  # Handle if categories is a single string
                category_text = categories.lower()

            post_is_relevant = False
            for keyword in KEYWORDS:
                if keyword in title or keyword in category_text:
                    post_is_relevant = True
                    break

            if post_is_relevant:
                relevant_posts.append(post)

        if not relevant_posts:
            st.success(
                "Successfully loaded Google Cloud Blog posts, but no articles matching your keywords (e.g., 'training', 'certification', 'learn') were found in the 'Training and Certifications' feed section."
            )
            logger.info(
                f"Found {len(posts_data)} total Google Cloud Blog posts, but none matched the keywords: {KEYWORDS}"
            )
            # Optionally, display a few unfiltered posts if needed for context, or just the message.
            # st.write("Here are some of the latest posts (unfiltered):")
            # for i, post in enumerate(posts_data[:3]): # Show top 3
            #     st.markdown(f"**[{post.get('title', 'No Title')}]({post.get('link', '#')})**")
            #     st.caption(f"Published: {post.get('published', 'N/A')}")
            #     if post.get('categories'):
            #         st.caption(f"Categories: {', '.join(post.get('categories'))}")
            #     st.divider()
            return

        st.header("Google Cloud Blog - Training & Certification Focus")
        st.markdown(
            f"Displaying **{len(relevant_posts)}** relevant posts based on keywords: `{', '.join(KEYWORDS)}`."
        )
        st.markdown("---")

        for post in relevant_posts:
            title = post.get("title", "No Title Available")
            link = post.get("link", "#")
            published_str = post.get("published", "No Date Available")
            categories = post.get("categories")  # This should be a list of strings

            st.subheader(f"[{title}]({link})")

            # Display publication date
            if published_str != "No Date Available":
                try:
                    # Attempt to parse if it's a full ISO string, otherwise display as is
                    pub_date = datetime.fromisoformat(
                        published_str.replace("Z", "+00:00")
                    )
                    st.caption(f"Published: {pub_date.strftime('%B %d, %Y')}")
                except ValueError:
                    st.caption(
                        f"Published: {published_str}"
                    )  # Display raw if parsing fails
            else:
                st.caption(published_str)

            # Display categories
            if categories and isinstance(categories, list) and len(categories) > 0:
                st.caption(f"Categories: {', '.join(categories)}")

            st.markdown("---")

        logger.info(
            f"Successfully rendered {len(relevant_posts)} Google Cloud Blog posts."
        )

    except Exception as e:
        logger.error(
            f"An error occurred in the Google Cloud Blog tab: {e}", exc_info=True
        )
        st.error(
            "An unexpected error occurred while rendering the Google Cloud Blog posts. Please check the logs for more details."
        )


if __name__ == "__main__":
    # This is a mock setup for local testing if needed
    # You would need to mock logger and the posts_data

    class MockLogger:
        def info(self, msg):
            print(f"INFO: {msg}")

        def error(self, msg, exc_info=False):
            print(f"ERROR: {msg}")

        def warning(self, msg):
            print(f"WARNING: {msg}")

    # Sample data for local testing
    sample_posts_data = [
        {
            "source": "google_cloud_blog",
            "title": "Learn new skills with Google Cloud Training",
            "link": "https://example.com/learn-skills",
            "published": "2023-10-26T10:00:00Z",
            "categories": ["training", "google cloud", "new skills"],
        },
        {
            "source": "google_cloud_blog",
            "title": "Get Google Cloud Certified in 2024!",
            "link": "https://example.com/get-certified",
            "published": "2023-10-25T11:00:00Z",
            "categories": ["certification", "google cloud", "career"],
        },
        {
            "source": "google_cloud_blog",
            "title": "An interesting post about BigQuery",
            "link": "https://example.com/bigquery-post",
            "published": "2023-10-24T12:00:00Z",
            "categories": ["bigquery", "data analytics"],
        },
        {
            "source": "google_cloud_blog",
            "title": "Boost your career with our new course on AI",
            "link": "https://example.com/ai-course",
            "published": "2023-10-23T14:00:00Z",
            "categories": ["AI", "Machine Learning", "course"],
        },
    ]

    mock_logger = MockLogger()

    st.set_page_config(layout="wide")
    render(logger=mock_logger, posts_data=sample_posts_data)

    # Test with no data
    # render(logger=mock_logger, posts_data=[])

    # Test with no relevant posts
    # no_relevant_data = [{
    #     "source": "google_cloud_blog",
    #     "title": "An interesting post about BigQuery",
    #     "link": "https://example.com/bigquery-post",
    #     "published": "2023-10-24T12:00:00Z",
    #     "categories": ["bigquery", "data analytics"]
    # }]
    # render(logger=mock_logger, posts_data=no_relevant_data)
