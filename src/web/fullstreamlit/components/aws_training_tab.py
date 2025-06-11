import streamlit as st
from typing import List, Dict, Any
import logging
from datetime import datetime

def render(logger: logging.Logger, posts_data: List[Dict[str, Any]]) -> None:
    """
    Renders the AWS Training and Certification blog posts tab.

    Args:
        logger: The logger instance.
        posts_data: A list of dictionaries, where each dictionary is an AWS blog post.
    """
    logger.info("Rendering AWS Training tab.")
    # TODO: Add keyword/date filters here, e.g., st.text_input for keywords, st.date_input for date range

    try:
        if not posts_data:
            st.info("No AWS training updates found or an error occurred while loading the data.")
            logger.info("No AWS training data to display.")
            return

        st.header("AWS Training & Certification Blog Updates")
        st.markdown(f"Displaying **{len(posts_data)}** latest updates.")
        st.markdown("---")

        for post in posts_data:
            title = post.get("title", "No Title Available")
            link = post.get("link", "#")
            published_str = post.get("published", "No Date Available")
            summary = post.get("summary", "No summary available.")
            categories = post.get("categories", [])

            st.subheader(f"[{title}]({link})")

            # Display publication date (formatted)
            if published_str and published_str != "No Date Available":
                try:
                    # Assuming published_str is ISO format (potentially with Z or offset)
                    dt_obj = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                    st.caption(f"Published: {dt_obj.strftime('%B %d, %Y, %H:%M %Z')}")
                except ValueError:
                    st.caption(f"Published: {published_str}") # Fallback to raw string
            else:
                st.caption(f"Published: {published_str}")

            # Display categories
            if isinstance(categories, list) and len(categories) > 0:
                st.caption(f"Categories: {', '.join(categories)}")
            elif isinstance(categories, str) and categories: # Handle if categories is a single string
                st.caption(f"Categories: {categories}")
            else:
                st.caption("Categories: Not available")

            # Display summary (using expander for potentially long content)
            if summary:
                with st.expander("View Summary/Description", expanded=False):
                    st.markdown(summary, unsafe_allow_html=True) # Allow HTML if summary contains it

            st.markdown("---")

        logger.info(f"Successfully rendered {len(posts_data)} AWS training posts.")

    except Exception as e:
        logger.error(f"An error occurred in the AWS Training tab: {e}", exc_info=True)
        st.error("An unexpected error occurred while rendering AWS training updates. Please check the logs for more details.")

if __name__ == '__main__':
    # Mock setup for local testing
    mock_logger_main = logging.getLogger("AWSTabTest")
    mock_logger_main.setLevel(logging.INFO)
    if not mock_logger_main.hasHandlers():
        mock_logger_main.addHandler(logging.StreamHandler())

    sample_aws_posts = [
        {
            "source": "aws_training_certification",
            "title": "New AWS Certified Cloud Practitioner Exam Version",
            "link": "https://aws.amazon.com/blogs/training-and-certification/new-aws-certified-cloud-practitioner-exam-version/",
            "published": "2023-09-19T15:56:18Z",
            "summary": "We will be launching a new version of the AWS Certified Cloud Practitioner exam on September 19, 2023. The new exam (CLF-C02) will feature updated content...",
            "categories": ["AWS Certified Cloud Practitioner", "Certification Announcement"]
        },
        {
            "source": "aws_training_certification",
            "title": "Unlock new skills with AWS Skill Builder",
            "link": "https://aws.amazon.com/blogs/training-and-certification/unlock-new-skills-with-aws-skill-builder/",
            "published": "2023-09-18T10:00:00+00:00",
            "summary": "AWS Skill Builder offers over 500 free digital courses. Learn about our new features...",
            "categories": ["AWS Skill Builder", "Digital Training"]
        },
        {
            "source": "aws_training_certification",
            "title": "Post with no categories",
            "link": "https://aws.amazon.com/blogs/training-and-certification/post-no-categories/",
            "published": "2023-09-17T10:00:00+00:00",
            "summary": "This post has no categories field or it is empty.",
            "categories": []
        },
         {
            "source": "aws_training_certification",
            "title": "Post with string category",
            "link": "https://aws.amazon.com/blogs/training-and-certification/post-string-category/",
            "published": "2023-09-16T10:00:00+00:00",
            "summary": "This post has categories as a string.",
            "categories": "SingleCategory"
        }
    ]

    st.set_page_config(layout="wide")
    render(logger=mock_logger_main, posts_data=sample_aws_posts)

    st.header("Test with No Data")
    render(logger=mock_logger_main, posts_data=[])