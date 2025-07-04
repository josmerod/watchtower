import json
import os

# Add project root for imports
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd

from src.etl.courses.aws_training_etl import (
    fetch_aws_training_feed,
    save_aws_training_entries,
)

# Mock data for AWS Training feed
MOCK_AWS_FEED_ENTRIES_RAW = [
    {},
    {},
    {
        # Missing tags
    },
    {},
    {
        # "published" key missing
    },
]


class TestAWSTrainingETL(unittest.TestCase):
    def setUp(self):
        os.makedirs(self.test_data_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.json_path):
            os.remove(self.json_path)
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    @patch("src.etl.courses.aws_training_etl.feedparser.parse")
    def test_fetch_aws_training_feed(self, mock_feedparser_parse):
        mock_feed_parsed = MagicMock()
        mock_feed_parsed.bozo = 0
        mock_feed_parsed.entries = []

        for raw_entry_data in MOCK_AWS_FEED_ENTRIES_RAW:
            entry_mock = MagicMock()
            entry_mock.title = raw_entry_data.get("title")
            entry_mock.link = raw_entry_data.get("link")
            entry_mock.summary = raw_entry_data.get("summary")

            raw_tags = raw_entry_data.get("tags", [])
            entry_mock.tags = [
                MagicMock(term=t_dict.get("term")) for t_dict in raw_tags
            ]

            def side_effect_for_get(
                key, default="", current_entry=entry_mock, raw_data=raw_entry_data
            ):
                if key == "title":
                    return current_entry.title
                if key == "link":
                    return current_entry.link
                if key == "published":
                    return raw_data.get("published", default)
                if key == "summary":
                    return raw_data.get("summary", default)
                if key == "description":
                    return raw_data.get("description", default)
                # The ETL script uses `hasattr(entry, 'tags')` and `entry.tags` directly first.
                # So, this part of `get` for 'tags' is less critical if `entry.tags` is correctly set.
                if key == "tags":
                    return current_entry.tags
                return raw_data.get(key, default)

            entry_mock.get.side_effect = side_effect_for_get
            mock_feed_parsed.entries.append(entry_mock)

        mock_feedparser_parse.return_value = mock_feed_parsed

        entries = fetch_aws_training_feed()
        assert len(entries) == len(MOCK_AWS_FEED_ENTRIES_RAW)

        # Check first entry
        first_entry_data = entries[0]
        assert first_entry_data["title"] == MOCK_AWS_FEED_ENTRIES_RAW[0]["title"]
        assert first_entry_data["link"] == MOCK_AWS_FEED_ENTRIES_RAW[0]["link"]
        assert first_entry_data["summary"] == MOCK_AWS_FEED_ENTRIES_RAW[0]["summary"]
        assert first_entry_data["source"] == "aws_training_certification"
        self.assertListEqual(
            first_entry_data["categories"], ["AWS Skill Builder", "Digital Training"]
        )

        # Check date parsing for first entry (GMT)
        # "Wed, 25 Jul 2024 10:00:00 GMT"
        dt_obj_gmt = datetime(2024, 7, 25, 10, 0, 0, tzinfo=timezone.utc)
        assert first_entry_data["published"] == dt_obj_gmt.isoformat()

        # Check date parsing for second entry (+0000)
        # "Tue, 24 Jul 2024 14:30:00 +0000"
        dt_obj_offset = datetime(2024, 7, 24, 14, 30, 0, tzinfo=timezone.utc)
        assert entries[1]["published"] == dt_obj_offset.isoformat()

        # Check date parsing for PST entry (dateutil should handle it)
        # "Mon, 23 Jul 2024 09:00:00 PST" (PST is UTC-8)
        # Note: dateutil.parser.parse might make this naive if PST is not in its DB, or apply a fixed offset.
        # For consistency, ETL converts to UTC.
        # If PST is parsed as UTC-8, 09:00 PST is 17:00 UTC.
        dt_obj_pst_expected = datetime(2024, 7, 23, 17, 0, 0, tzinfo=timezone.utc)
        assert entries[2]["published"] == dt_obj_pst_expected.isoformat()
        assert entries[2]["categories"] == []  # No tags for this entry

        # Check malformed date
        assert entries[3]["published"] == MOCK_AWS_FEED_ENTRIES_RAW[3]["published"]

        # Check missing date
        assert entries[4]["published"] == ""

    @patch("src.etl.courses.aws_training_etl.get_project_root")
    def test_save_aws_training_entries(self, mock_get_project_root):
        mock_get_project_root.return_value = self.project_root_path

        mock_entries_to_save = [
            {},
        ]
        save_aws_training_entries(mock_entries_to_save)

        assert os.path.exists(self.json_path)
        with open(self.json_path, encoding="utf-8") as f:
            saved_json_data = json.load(f)
        assert saved_json_data == mock_entries_to_save

        assert os.path.exists(self.csv_path)
        saved_csv_df = pd.read_csv(self.csv_path)

        expected_df = pd.DataFrame(mock_entries_to_save)

        # Ensure columns are in the order defined by the ETL script
        expected_columns_order = [
            "source",
            "title",
            "link",
            "published",
            "summary",
            "categories",
        ]
        saved_csv_df = saved_csv_df[expected_columns_order]
        expected_df = expected_df[expected_columns_order]

        pd.testing.assert_frame_equal(saved_csv_df, expected_df)


if __name__ == "__main__":
    pass
