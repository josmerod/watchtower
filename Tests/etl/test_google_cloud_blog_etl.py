import json
import os

# Add project root for imports if tests are run from a different directory
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from src.etl.news.news_get_media_rss import (
    fetch_media_feeds,
    save_media_entries,
)

# Mock data for Google Cloud Blog feed
MOCK_GCB_FEED_ENTRIES = [{}, {}, {}, {}, {}, {}]

MOCK_FEED_PARSER_DICT = {}


class TestGoogleCloudBlogETL(unittest.TestCase):
    def setUp(self):
        # Ensure data/news directory exists for testing save_media_entries
        os.makedirs(self.test_data_dir, exist_ok=True)

    def tearDown(self):
        # Clean up created files
        if os.path.exists(self.json_path):
            os.remove(self.json_path)
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    @patch("src.etl.news.news_get_media_rss.feedparser.parse")
    @patch(
        "src.etl.news.news_get_media_rss.RSS_FEEDS", new_callable=dict
    )  # Mock the RSS_FEEDS dict
    def test_fetch_media_feeds_google_cloud_blog_filtering(
        self, mock_rss_feeds, mock_feedparser_parse
    ):
        # Setup mock for RSS_FEEDS to only use google_cloud_blog
        mock_rss_feeds.clear()

        # Setup mock for feedparser.parse
        mock_feed_obj = MagicMock()
        mock_feed_obj.bozo = 0
        mock_feed_obj.entries = [MagicMock(**entry) for entry in MOCK_GCB_FEED_ENTRIES]
        for i, entry_mock in enumerate(mock_feed_obj.entries):
            # Mocking tags structure
            if "tags" in MOCK_GCB_FEED_ENTRIES[i]:
                entry_mock.tags = [
                    MagicMock(term=tag["term"])
                    for tag in MOCK_GCB_FEED_ENTRIES[i]["tags"]
                ]
            else:
                entry_mock.tags = []

        mock_feedparser_parse.return_value = mock_feed_obj

        # Call the function
        entries = fetch_media_feeds()

        # Assertions
        assert isinstance(entries, list)
        # Expected to find 4 relevant entries:
        # 1. "Learn BigQuery Skills" (Training and Certifications)
        # 2. "New Cloud Course Available" (training and certifications)
        # 3. "Advanced Kubernetes Training" (Advanced Training)
        # 4. "Missing Date Post" (Training and Certifications)
        # 5. "Malformed Date" (training and certifications)
        assert len(entries) == 5

        # Check content of one entry
        learn_bigquery_entry = next(
            e for e in entries if e["title"] == "Learn BigQuery Skills"
        )
        assert learn_bigquery_entry["source"] == "google_cloud_blog"
        assert learn_bigquery_entry["link"] == "https://example.com/learn-bigquery"
        assert "BigQuery" in learn_bigquery_entry["categories"]
        assert "Training and Certifications" in learn_bigquery_entry["categories"]
        # Check parsed date (example: "Tue, 20 Jul 2024 10:00:00 GMT")
        # The script converts to ISO format.
        dt_obj = datetime.strptime(
            "Tue, 20 Jul 2024 10:00:00 GMT", "%a, %d %b %Y %H:%M:%S %Z"
        )
        assert learn_bigquery_entry["published"] == dt_obj.isoformat()

        new_course_entry = next(
            e for e in entries if e["title"] == "New Cloud Course Available"
        )
        dt_obj_course = datetime.strptime(
            "Mon, 19 Jul 2024 12:00:00 +0000", "%a, %d %b %Y %H:%M:%S %z"
        )
        assert new_course_entry["published"] == dt_obj_course.isoformat()

        missing_date_entry = next(
            e for e in entries if e["title"] == "Missing Date Post"
        )
        assert missing_date_entry["published"] == ""  # Handled by get("published", "")

        malformed_date_entry = next(
            e for e in entries if e["title"] == "Malformed Date"
        )
        assert malformed_date_entry["published"] == "This is not a date"

    @patch("src.etl.news.news_get_media_rss.get_project_root")
    def test_save_media_entries_google_cloud_blog(self, mock_get_project_root):
        # Mock get_project_root to control output directory for this test
        # Here we assume the test is run from project root, so "test_output" is fine.
        # Or, more robustly, create a temporary directory.
        # For this example, we'll use the setUp-defined self.test_data_dir relative to actual project root.
        mock_get_project_root.return_value = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../..")
        )

        mock_entries_to_save = [{}, {}]

        save_media_entries(mock_entries_to_save, source_type="google_cloud_blog")

        # Check JSON file
        assert os.path.exists(self.json_path)
        with open(self.json_path, encoding="utf-8") as f:
            saved_json_data = json.load(f)
        assert saved_json_data == mock_entries_to_save

        # Check CSV file
        assert os.path.exists(self.csv_path)
        saved_csv_data = pd.read_csv(self.csv_path)

        # Convert mock entries to DataFrame for easier comparison, ensuring consistent column order
        expected_df = pd.DataFrame(mock_entries_to_save)
        # The script ensures all columns are present, fillna for comparison
        for col in ["source", "title", "link", "published", "categories"]:
            if col not in saved_csv_data.columns:
                saved_csv_data[col] = pd.NA

        # Convert categories list to string for CSV comparison as pandas does by default

        pd.testing.assert_frame_equal(
            saved_csv_data[expected_df.columns]
            .sort_values(by="title")
            .reset_index(drop=True),
            expected_df.sort_values(by="title").reset_index(drop=True),
            check_dtype=False,  # CSV read might change dtypes slightly (e.g. objects)
        )


if __name__ == "__main__":
    pass
