
# Add project root for imports
import unittest
from unittest.mock import MagicMock, call, patch

from src.web.fullstreamlit.components.google_cloud_blog_tab import (
    render as render_google_cloud_blog_tab,
)

# Create a logger instance for passing to the render function if needed, or mock it.
# For unit tests, often a MagicMock is sufficient.
mock_logger = MagicMock()


class TestGoogleCloudBlogTab(unittest.TestCase):
    @patch("src.web.fullstreamlit.components.google_cloud_blog_tab.st")
    def test_render_with_data(self, mock_st):
        sample_posts_data = [
            {},
            {},
            {},
            {
                # "published" key missing
            },
        ]

        render_google_cloud_blog_tab(logger=mock_logger, posts_data=sample_posts_data)

        # Check main header
        mock_st.header.assert_any_call(
            "Google Cloud Blog - Training & Certification Focus"
        )

        # Check that st.subheader and st.markdown (for links) are called for each post
        # Number of posts = 4
        assert mock_st.subheader.call_count == 4
        # Each post has a title, date, categories (if any), and a divider (markdown "---")
        # Title (subheader), Date (caption), Categories (caption), Divider (markdown)
        # So, markdown calls: 4 for dividers + potentially info/success messages.
        # Let's be more specific about title links.

        expected_subheader_calls = [
            call("[Post 1: Learn Skills](http://example.com/post1)"),
            call("[Post 2: Get Certified](http://example.com/post2)"),
            call("[Post 3: No Categories](http://example.com/post3)"),
            call("[Post 4: No Date](http://example.com/post4)"),
        ]
        mock_st.subheader.assert_has_calls(expected_subheader_calls, any_order=False)

        # Check publication dates and categories (via st.caption)
        # Post 1: Date + Categories
        # Post 2: Date + Categories
        # Post 3: Date + No Categories (so one caption for date)
        # Post 4: No Date + Categories
        # Total caption calls: 2 + 2 + 1 + 1 = 6
        assert mock_st.caption.call_count == 6

        expected_caption_calls = [
            call("Published: July 20, 2024"),  # P1 Date
            call("Categories: skill, training"),  # P1 Cat
            call("Published: July 19, 2024"),  # P2 Date
            call("Categories: certification"),  # P2 Cat
            call("Published: July 18, 2024"),  # P3 Date (no cat for post 3)
            # call("Categories: ") # No, this won't be called if categories is empty
            call("Categories: learn"),  # P4 Cat (no date for post 4)
        ]
        mock_st.caption.assert_has_calls(
            expected_caption_calls, any_order=False
        )  # Order matters here relative to posts

        # Check dividers
        mock_st.markdown.assert_any_call("---")
        # Expect 1 for initial message, 1 for summary, 4 for dividers between posts
        # The "Displaying X relevant posts..." and "---" initial divider.
        assert mock_st.markdown.call_count >= 4  # At least one per post

        # Check logger calls
        mock_logger.info.assert_any_call("Rendering Google Cloud Blog tab.")
        mock_logger.info.assert_any_call(
            f"Successfully rendered {len(sample_posts_data)} Google Cloud Blog posts."
        )

    @patch("src.web.fullstreamlit.components.google_cloud_blog_tab.st")
    def test_render_no_data(self, mock_st):
        render_google_cloud_blog_tab(logger=mock_logger, posts_data=[])

        mock_st.info.assert_called_once_with(
            "No Google Cloud Blog posts found or an error occurred while loading the data. Please check the logs or try again later."
        )
        mock_logger.info.assert_any_call("No Google Cloud Blog data to display.")
        # Ensure no headers or post-related functions were called
        mock_st.header.assert_not_called()
        mock_st.subheader.assert_not_called()

    @patch("src.web.fullstreamlit.components.google_cloud_blog_tab.st")
    def test_render_data_no_relevant_filters_message(self, mock_st):
        # This test case is for when the component receives data, but after its *internal* filtering
        # (if any beyond the keywords) it finds nothing.
        # The current component design expects pre-filtered data based on the ETL stage for "training and certification".
        # The KEYWORDS filtering in the component is an additional layer.
        # Let's test if data is passed, but KEYWORDS don't match anything.

        posts_data_no_keywords_match = [{}]
        render_google_cloud_blog_tab(
            logger=mock_logger, posts_data=posts_data_no_keywords_match
        )

        # Expect a success message indicating data was loaded but no keywords matched
        mock_st.success.assert_called_once()
        assert "Successfully loaded Google Cloud Blog posts, but no articles matching your keywords" in mock_st.success.call_args[0][0]
        mock_logger.info.assert_any_call(
            f"Found {len(posts_data_no_keywords_match)} total Google Cloud Blog posts, but none matched the keywords: ['skill', 'skills', 'training', 'certification', 'learn', 'boost', 'course', 'courses', 'badge', 'prepare', 'exam']"
        )
        mock_st.header.assert_not_called()  # No main display header if no relevant posts
        mock_st.subheader.assert_not_called()

    @patch("src.web.fullstreamlit.components.google_cloud_blog_tab.st")
    def test_render_general_exception_handling(self, mock_st):
        faulty_posts_data = []

        # Mock a function that will be called during rendering to raise an exception

        render_google_cloud_blog_tab(logger=mock_logger, posts_data=faulty_posts_data)

        mock_st.error.assert_called_once_with(
            "An unexpected error occurred while rendering the Google Cloud Blog posts. Please check the logs for more details."
        )
        mock_logger.error.assert_called_once()
        # Check that the error message includes the exception info
        assert "An error occurred in the Google Cloud Blog tab" in mock_logger.error.call_args[0][0]
        assert mock_logger.error.call_args[1]["exc_info"]


if __name__ == "__main__":
    pass
