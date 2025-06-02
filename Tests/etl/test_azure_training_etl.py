import unittest
from unittest.mock import patch, MagicMock
import os
import json
import pandas as pd
from datetime import datetime, timezone

# Add project root for imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.etl.courses.azure_training_etl import fetch_azure_training_feed, save_azure_training_entries
from src.utils.file_system import get_project_root # To be mocked

# Mock data for Azure Training feed
MOCK_AZURE_FEED_ENTRIES_RAW = [
    {
        "title": "Azure AI Fundamentals Workshop",
        "link": "https://learn.microsoft.com/en-us/blogs/azure-ai-fundamentals-workshop/",
        "published": "Thu, 26 Jul 2024 11:00:00 GMT",
        "summary": "Join our interactive workshop on Azure AI.",
        "description": "Detailed description for Azure AI workshop.",
        "tags": [{"term": "Azure AI"}, {"term": "Workshop"}, {"term": "Microsoft Learn"}],
    },
    {
        "title": "New Microsoft Certified: Azure Solutions Architect Expert Path",
        "link": "https://learn.microsoft.com/en-us/blogs/new-exam-az-305/",
        "published": "Wed, 25 Jul 2024 15:00:00 +0000",
        "summary": "Updated learning path for AZ-305 exam.",
        "tags": [{"term": "Certification"}, {"term": "Azure Architect"}],
    },
    {
        "title": "Exploring Azure DevOps Best Practices",
        "link": "https://learn.microsoft.com/en-us/blogs/azure-devops-best-practices/",
        "published": "Tue, 24 Jul 2024 08:00:00 EST", # EST is UTC-5
        "summary": "Learn how to optimize your CI/CD pipelines with Azure DevOps.",
        # Missing tags
    }
]

class TestAzureTrainingETL(unittest.TestCase):

    def setUp(self):
        self.project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        self.test_data_dir = os.path.join(self.project_root_path, "data", "courses")
        os.makedirs(self.test_data_dir, exist_ok=True)

        self.json_path = os.path.join(self.test_data_dir, "azure_training_updates.json")
        self.csv_path = os.path.join(self.test_data_dir, "azure_training_updates.csv")

    def tearDown(self):
        if os.path.exists(self.json_path):
            os.remove(self.json_path)
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    @patch('src.etl.courses.azure_training_etl.feedparser.parse')
    def test_fetch_azure_training_feed(self, mock_feedparser_parse):
        mock_feed_parsed = MagicMock()
        mock_feed_parsed.bozo = 0
        mock_feed_parsed.entries = []

        for raw_entry_data in MOCK_AZURE_FEED_ENTRIES_RAW:
            entry_mock = MagicMock()
            entry_mock.title = raw_entry_data.get("title")
            entry_mock.link = raw_entry_data.get("link")
            entry_mock.published = raw_entry_data.get("published")
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
                if key == "tags": return current_entry.tags
                return raw_data.get(key, default)

            entry_mock.get.side_effect = side_effect_for_get
            mock_feed_parsed.entries.append(entry_mock)

        mock_feedparser_parse.return_value = mock_feed_parsed

        entries = fetch_azure_training_feed()
        self.assertEqual(len(entries), len(MOCK_AZURE_FEED_ENTRIES_RAW))

        first_entry_data = entries[0]
        self.assertEqual(first_entry_data["title"], MOCK_AZURE_FEED_ENTRIES_RAW[0]["title"])
        self.assertEqual(first_entry_data["link"], MOCK_AZURE_FEED_ENTRIES_RAW[0]["link"])
        self.assertEqual(first_entry_data["summary"], MOCK_AZURE_FEED_ENTRIES_RAW[0]["summary"])
        self.assertEqual(first_entry_data["source"], "azure_microsoft_learn_blog")
        self.assertListEqual(first_entry_data["categories"], ["Azure AI", "Workshop", "Microsoft Learn"])

        dt_obj_gmt = datetime(2024, 7, 26, 11, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(first_entry_data["published"], dt_obj_gmt.isoformat())

        dt_obj_est_expected = datetime(2024, 7, 24, 13, 0, 0, tzinfo=timezone.utc) # 8 AM EST is 1 PM UTC (assuming EST is UTC-5 during standard time)
        self.assertEqual(entries[2]["published"], dt_obj_est_expected.isoformat())
        self.assertEqual(entries[2]["categories"], [])


    @patch('src.etl.courses.azure_training_etl.get_project_root')
    def test_save_azure_training_entries(self, mock_get_project_root):
        mock_get_project_root.return_value = self.project_root_path

        mock_entries_to_save = [
            {
                "source": "azure_microsoft_learn_blog", "title": "Azure Save Test 1",
                "link": "http://example.com/azuresavetest1",
                "published": datetime(2024, 7, 2, 11, 0, 0, tzinfo=timezone.utc).isoformat(),
                "summary": "Azure Summary 1", "categories": ["az_cat1", "az_cat2"]
            },
        ]
        save_azure_training_entries(mock_entries_to_save)

        self.assertTrue(os.path.exists(self.json_path))
        with open(self.json_path, 'r', encoding='utf-8') as f:
            saved_json_data = json.load(f)
        self.assertEqual(saved_json_data, mock_entries_to_save)

        self.assertTrue(os.path.exists(self.csv_path))
        saved_csv_df = pd.read_csv(self.csv_path)

        expected_df = pd.DataFrame(mock_entries_to_save)
        expected_df['categories'] = expected_df['categories'].astype(str)
        saved_csv_df['categories'] = saved_csv_df['categories'].astype(str)

        expected_columns_order = ["source", "title", "link", "published", "summary", "categories"]
        saved_csv_df = saved_csv_df[expected_columns_order]
        expected_df = expected_df[expected_columns_order]

        pd.testing.assert_frame_equal(saved_csv_df, expected_df)

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
```
