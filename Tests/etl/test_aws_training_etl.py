import unittest
from unittest.mock import patch, MagicMock
import os
import json
import pandas as pd
from datetime import datetime, timezone

# Add project root for imports
import sys
from src.etl.courses.aws_training_etl import fetch_aws_training_feed, save_aws_training_entries
from src.utils.file_system import get_project_root # To be mocked for controlling output

# Mock data for AWS Training feed
MOCK_AWS_FEED_ENTRIES_RAW = [
    {
        "title": "AWS Skill Builder Deep Dive",
        "link": "https://aws.amazon.com/blogs/training-and-certification/skill-builder-deep-dive/",
        "published": "Wed, 25 Jul 2024 10:00:00 GMT",
        "summary": "Explore advanced features of AWS Skill Builder.",
        "description": "This is a longer description for Skill Builder.", # Fallback if summary is missing
        "tags": [{"term": "AWS Skill Builder"}, {"term": "Digital Training"}],
    },
    {
        "title": "New Exam: AWS Certified Data Engineer - Associate",
        "link": "https://aws.amazon.com/blogs/training-and-certification/new-exam-aws-certified-data-engineer-associate/",
        "published": "Tue, 24 Jul 2024 14:30:00 +0000", # Different timezone format
        "summary": "Announcing the new AWS Certified Data Engineer - Associate exam (DEA-C01).",
        "tags": [{"term": "Certification Announcement"}, {"term": "Data Engineering"}],
    },
    {
        "title": "Preparing for re:Invent 2024",
        "link": "https://aws.amazon.com/blogs/training-and-certification/preparing-for-reinvent-2024/",
        "published": "Mon, 23 Jul 2024 09:00:00 PST", # Example with PST, dateutil should handle
        "summary": "Tips and tricks for AWS re:Invent attendees.",
        # Missing tags
    },
    {
        "title": "Malformed Date Entry",
        "link": "https://aws.amazon.com/blogs/training-and-certification/malformed-date/",
        "published": "Not a Real Date",
        "summary": "This entry has a date that cannot be parsed.",
        "tags": [{"term": "Miscellaneous"}],
    },
    {
        "title": "Entry with no published date",
        "link": "https://aws.amazon.com/blogs/training-and-certification/no-date/",
        # "published" key missing
        "summary": "This entry has no published date field.",
        "tags": [{"term": "Info"}],
    }
]

class TestAWSTrainingETL(unittest.TestCase):

    def setUp(self):
        self.project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        self.test_data_dir = os.path.join(self.project_root_path, "data", "courses")
        os.makedirs(self.test_data_dir, exist_ok=True)

        self.json_path = os.path.join(self.test_data_dir, "aws_training_updates.json")
        self.csv_path = os.path.join(self.test_data_dir, "aws_training_updates.csv")

    def tearDown(self):
        if os.path.exists(self.json_path):
            os.remove(self.json_path)
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    @patch('src.etl.courses.aws_training_etl.feedparser.parse')
    def test_fetch_aws_training_feed(self, mock_feedparser_parse):
        mock_feed_parsed = MagicMock()
        mock_feed_parsed.bozo = 0
        mock_feed_parsed.entries = []

        for raw_entry_data in MOCK_AWS_FEED_ENTRIES_RAW:
            entry_mock = MagicMock()
            entry_mock.title = raw_entry_data.get("title")
            entry_mock.link = raw_entry_data.get("link")
            entry_mock.published = raw_entry_data.get("published") # Store raw published string
            entry_mock.summary = raw_entry_data.get("summary")
            entry_mock.description = raw_entry_data.get("description")

            raw_tags = raw_entry_data.get("tags", [])
            entry_mock.tags = [MagicMock(term=t_dict.get("term")) for t_dict in raw_tags]

            def side_effect_for_get(key, default="", current_entry=entry_mock, raw_data=raw_entry_data):
                if key == "title": return current_entry.title
                if key == "link": return current_entry.link
                if key == "published": return raw_data.get("published", default)
                if key == "summary": return raw_data.get("summary", default)
                if key == "description": return raw_data.get("description", default)
                # The ETL script uses `hasattr(entry, 'tags')` and `entry.tags` directly first.
                # So, this part of `get` for 'tags' is less critical if `entry.tags` is correctly set.
                if key == "tags": return current_entry.tags
                return raw_data.get(key, default)

            entry_mock.get.side_effect = side_effect_for_get
            mock_feed_parsed.entries.append(entry_mock)

        mock_feedparser_parse.return_value = mock_feed_parsed

        entries = fetch_aws_training_feed()
        self.assertEqual(len(entries), len(MOCK_AWS_FEED_ENTRIES_RAW))

        # Check first entry
        first_entry_data = entries[0]
        self.assertEqual(first_entry_data["title"], MOCK_AWS_FEED_ENTRIES_RAW[0]["title"])
        self.assertEqual(first_entry_data["link"], MOCK_AWS_FEED_ENTRIES_RAW[0]["link"])
        self.assertEqual(first_entry_data["summary"], MOCK_AWS_FEED_ENTRIES_RAW[0]["summary"])
        self.assertEqual(first_entry_data["source"], "aws_training_certification")
        self.assertListEqual(first_entry_data["categories"], ["AWS Skill Builder", "Digital Training"])

        # Check date parsing for first entry (GMT)
        # "Wed, 25 Jul 2024 10:00:00 GMT"
        dt_obj_gmt = datetime(2024, 7, 25, 10, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(first_entry_data["published"], dt_obj_gmt.isoformat())

        # Check date parsing for second entry (+0000)
        # "Tue, 24 Jul 2024 14:30:00 +0000"
        dt_obj_offset = datetime(2024, 7, 24, 14, 30, 0, tzinfo=timezone.utc)
        self.assertEqual(entries[1]["published"], dt_obj_offset.isoformat())

        # Check date parsing for PST entry (dateutil should handle it)
        # "Mon, 23 Jul 2024 09:00:00 PST" (PST is UTC-8)
        # Note: dateutil.parser.parse might make this naive if PST is not in its DB, or apply a fixed offset.
        # For consistency, ETL converts to UTC.
        # If PST is parsed as UTC-8, 09:00 PST is 17:00 UTC.
        dt_obj_pst_expected = datetime(2024, 7, 23, 17, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(entries[2]["published"], dt_obj_pst_expected.isoformat())
        self.assertEqual(entries[2]["categories"], []) # No tags for this entry

        # Check malformed date
        self.assertEqual(entries[3]["published"], MOCK_AWS_FEED_ENTRIES_RAW[3]["published"])

        # Check missing date
        self.assertEqual(entries[4]["published"], "")


    @patch('src.etl.courses.aws_training_etl.get_project_root')
    def test_save_aws_training_entries(self, mock_get_project_root):
        mock_get_project_root.return_value = self.project_root_path

        mock_entries_to_save = [
            {
                "source": "aws_training_certification", "title": "Save Test Post 1",
                "link": "http://example.com/savetest1",
                "published": datetime(2024, 7, 1, 10, 0, 0, tzinfo=timezone.utc).isoformat(),
                "summary": "Summary 1", "categories": ["cat1", "cat2"]
            },
        ]
        save_aws_training_entries(mock_entries_to_save)

        self.assertTrue(os.path.exists(self.json_path))
        with open(self.json_path, 'r', encoding='utf-8') as f:
            saved_json_data = json.load(f)
        self.assertEqual(saved_json_data, mock_entries_to_save)

        self.assertTrue(os.path.exists(self.csv_path))
        saved_csv_df = pd.read_csv(self.csv_path)

        expected_df = pd.DataFrame(mock_entries_to_save)
        expected_df['categories'] = expected_df['categories'].astype(str)
        saved_csv_df['categories'] = saved_csv_df['categories'].astype(str)

        # Ensure columns are in the order defined by the ETL script
        expected_columns_order = ["source", "title", "link", "published", "summary", "categories"]
        saved_csv_df = saved_csv_df[expected_columns_order]
        expected_df = expected_df[expected_columns_order]

        pd.testing.assert_frame_equal(saved_csv_df, expected_df)

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
```
