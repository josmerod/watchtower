import unittest
from unittest.mock import patch, MagicMock, call
import logging

# Add project root for imports
import sys
import os
from src.web.fullstreamlit.components.aws_training_tab import render as render_aws_training_tab

mock_logger = MagicMock()

class TestAWSTrainingTab(unittest.TestCase):

    @patch('src.web.fullstreamlit.components.aws_training_tab.st')
    def test_render_with_aws_data(self, mock_st):
        sample_posts_data = [
            {





            },
            {





            }
        ]

        render_aws_training_tab(logger=mock_logger, posts_data=sample_posts_data)

        mock_st.header.assert_called_once_with("AWS Training & Certification Blog Updates")

        self.assertEqual(mock_st.subheader.call_count, 2)
        expected_subheader_calls = [
            call("[AWS Post 1: Lambda Basics](http://example.com/aws_post1)"),
            call("[AWS Post 2: S3 Storage Classes](http://example.com/aws_post2)")
        ]
        mock_st.subheader.assert_has_calls(expected_subheader_calls, any_order=False)

        # Expected caption calls: 2 for date, 2 for categories = 4
        self.assertEqual(mock_st.caption.call_count, 4)
        expected_caption_calls = [
            call("Published: July 20, 2024, 10:00 UTC"), # Formatted date
            call("Categories: Serverless, Lambda, AWS"),
            call("Published: July 19, 2024, 12:30 UTC"),
            call("Categories: Storage, S3")
        ]
        mock_st.caption.assert_has_calls(expected_caption_calls, any_order=False)

        # Check expanders for summary
        self.assertEqual(mock_st.expander.call_count, 2)
        mock_st.expander.assert_any_call("View Summary/Description", expanded=False)

        # Check that markdown was called for summaries inside expanders and for dividers
        # Each expander context manager will call st.markdown for the summary.
        # Plus 1 for initial message, and 2 for dividers.
        self.assertTrue(mock_st.markdown.call_count >= (1 + 2 + 2))
        mock_st.markdown.assert_any_call("Summary for AWS Lambda post.", unsafe_allow_html=True)
        mock_st.markdown.assert_any_call("Deep dive into S3.", unsafe_allow_html=True)
        mock_st.markdown.assert_any_call("---")

        mock_logger.info.assert_any_call("Rendering AWS Training tab.")
        mock_logger.info.assert_any_call(f"Successfully rendered {len(sample_posts_data)} AWS training posts.")


    @patch('src.web.fullstreamlit.components.aws_training_tab.st')
    def test_render_no_aws_data(self, mock_st):
        render_aws_training_tab(logger=mock_logger, posts_data=[])

        mock_st.info.assert_called_once_with(
            "No AWS training updates found or an error occurred while loading the data."
        )
        mock_logger.info.assert_any_call("No AWS training data to display.")
        mock_st.header.assert_not_called()
        mock_st.subheader.assert_not_called()

    @patch('src.web.fullstreamlit.components.aws_training_tab.st')
    def test_render_aws_error_handling(self, mock_st):
        # Simulate an error during rendering by providing faulty data
        faulty_data = [None]

        # If st.subheader is called with None, it might raise an error internally,
        # or the .get method on None would.
        # Let's make a specific st call fail:

        render_aws_training_tab(logger=mock_logger, posts_data=faulty_data)

        mock_st.error.assert_called_once_with(
            "An unexpected error occurred while rendering AWS training updates. Please check the logs for more details."
        )
        mock_logger.error.assert_called_once()
        self.assertIn("An error occurred in the AWS Training tab", mock_logger.error.call_args[0][0])
        self.assertTrue(mock_logger.error.call_args[1]['exc_info'])

if __name__ == '__main__':

