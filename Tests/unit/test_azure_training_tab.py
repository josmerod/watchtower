import unittest
from unittest.mock import patch, MagicMock, call
import logging

# Add project root for imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.web.fullstreamlit.components.azure_training_tab import render as render_azure_training_tab

mock_logger = MagicMock()

class TestAzureTrainingTab(unittest.TestCase):

    @patch('src.web.fullstreamlit.components.azure_training_tab.st')
    def test_render_with_azure_data(self, mock_st):
        sample_posts_data = [
            {
                "title": "Azure Post 1: AI Services",
                "link": "http://example.com/azure_post1",
                "published": "2024-07-22T09:00:00Z",
                "summary": "Overview of Azure AI.",
                "categories": ["AI", "Azure Cognitive Services"]
            },
            {
                "title": "Azure Post 2: DevOps Solutions",
                "link": "http://example.com/azure_post2",
                "published": "2024-07-21T11:45:00+00:00",
                "summary": "Azure DevOps features.",
                "categories": ["DevOps", "Azure Repos", "Pipelines"]
            }
        ]

        render_azure_training_tab(logger=mock_logger, posts_data=sample_posts_data)

        mock_st.header.assert_called_once_with("Azure Training & Certification Blog Updates (Microsoft Learn)")

        self.assertEqual(mock_st.subheader.call_count, 2)
        expected_subheader_calls = [
            call("[Azure Post 1: AI Services](http://example.com/azure_post1)"),
            call("[Azure Post 2: DevOps Solutions](http://example.com/azure_post2)")
        ]
        mock_st.subheader.assert_has_calls(expected_subheader_calls, any_order=False)

        self.assertEqual(mock_st.caption.call_count, 4)
        expected_caption_calls = [
            call("Published: July 22, 2024, 09:00 UTC"),
            call("Categories: AI, Azure Cognitive Services"),
            call("Published: July 21, 2024, 11:45 UTC"),
            call("Categories: DevOps, Azure Repos, Pipelines")
        ]
        mock_st.caption.assert_has_calls(expected_caption_calls, any_order=False)

        self.assertEqual(mock_st.expander.call_count, 2)
        mock_st.expander.assert_any_call("View Summary/Description", expanded=False)

        self.assertTrue(mock_st.markdown.call_count >= (1 + 2 + 2))
        mock_st.markdown.assert_any_call("Overview of Azure AI.", unsafe_allow_html=True)
        mock_st.markdown.assert_any_call("Azure DevOps features.", unsafe_allow_html=True)
        mock_st.markdown.assert_any_call("---")

        mock_logger.info.assert_any_call("Rendering Azure Training tab.")
        mock_logger.info.assert_any_call(f"Successfully rendered {len(sample_posts_data)} Azure training posts.")


    @patch('src.web.fullstreamlit.components.azure_training_tab.st')
    def test_render_no_azure_data(self, mock_st):
        render_azure_training_tab(logger=mock_logger, posts_data=[])

        mock_st.info.assert_called_once_with(
            "No Azure training updates found or an error occurred while loading the data."
        )
        mock_logger.info.assert_any_call("No Azure training data to display.")
        mock_st.header.assert_not_called()
        mock_st.subheader.assert_not_called()

    @patch('src.web.fullstreamlit.components.azure_training_tab.st')
    def test_render_azure_error_handling(self, mock_st):
        faulty_data = [{"title": "Bad Post"}] # Missing other fields might cause issues or get default values
        mock_st.expander.side_effect = Exception("Simulated Azure Tab Error")

        render_azure_training_tab(logger=mock_logger, posts_data=faulty_data)

        mock_st.error.assert_called_once_with(
            "An unexpected error occurred while rendering Azure training updates. Please check the logs for more details."
        )
        mock_logger.error.assert_called_once()
        self.assertIn("An error occurred in the Azure Training tab", mock_logger.error.call_args[0][0])
        self.assertTrue(mock_logger.error.call_args[1]['exc_info'])

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
```
