# Tests/etl/test_home_server_trends_etl.py
import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import sys
from datetime import datetime
import requests # Import requests for requests.exceptions.RequestException
import json
import csv

# Add project root to sys.path to allow imports from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Now import the module to be tested
from src.etl.news import news_get_home_server_trends as etl_script
from src.models.home_server import HomeServerTrendItem

class TestHomeServerTrendsETL(unittest.TestCase):

    @patch('src.etl.news.news_get_home_server_trends.requests.Session.get')
    def test_fetch_awesome_selfhosted_readme_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """### Test Category
- [App1](http://app1.com) - Desc1."""
        mock_get.return_value = mock_response

        session = etl_script.create_session() # Use the actual session creator
        content = etl_script.fetch_awesome_selfhosted_readme(session)
        self.assertIsNotNone(content)
        self.assertEqual(content, mock_response.text)
        mock_get.assert_called_once_with(etl_script.AWESOME_SELFHOSTED_URL, timeout=30)

    @patch('src.etl.news.news_get_home_server_trends.requests.Session.get')
    def test_fetch_awesome_selfhosted_readme_failure(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Test network error")

        session = etl_script.create_session()
        content = etl_script.fetch_awesome_selfhosted_readme(session)
        self.assertIsNone(content)

    def test_parse_markdown(self):
        mock_markdown = """
# Some Title

## Some Section

### Analytics
- [Plausible Analytics](https://plausible.io/) - Simple, lightweight (< 1 KB) and privacy-friendly web analytics. `AGPL-3.0` `Elixir`
- [Matomo](https://matomo.org/) - Web analytics that protects your data. `GPL-3.0` `PHP`

### Not Interesting Category
- [NotInListApp](http://notinlist.com) - Some other app.

### Automation
- [Huginn](https://github.com/huginn/huginn) - Build agents that monitor and act on your behalf. `MIT` `Ruby`
- [changedetection.io](https://changedetection.io/) - Stay up-to-date with web-site content changes. `Apache-2.0` `Python/Docker`
        """
        # Temporarily modify CATEGORIES_OF_INTEREST for this test
        original_categories = etl_script.CATEGORIES_OF_INTEREST
        etl_script.CATEGORIES_OF_INTEREST = ["Analytics", "Automation"]

        parsed_items = etl_script.parse_markdown(mock_markdown)

        etl_script.CATEGORIES_OF_INTEREST = original_categories # Restore

        self.assertEqual(len(parsed_items), 4)

        self.assertEqual(parsed_items[0]['name'], "Plausible Analytics")
        self.assertEqual(parsed_items[0]['category'], "Analytics")
        self.assertEqual(parsed_items[0]['url'], "https://plausible.io/")
        self.assertIn("Simple, lightweight", parsed_items[0]['description'])
        self.assertListEqual(parsed_items[0]['tags'], ["AGPL-3.0", "Elixir"])

        self.assertEqual(parsed_items[1]['name'], "Matomo")
        self.assertEqual(parsed_items[1]['category'], "Analytics")

        self.assertEqual(parsed_items[2]['name'], "Huginn")
        self.assertEqual(parsed_items[2]['category'], "Automation")

        self.assertEqual(parsed_items[3]['name'], "changedetection.io")
        self.assertEqual(parsed_items[3]['description'], "Stay up-to-date with web-site content changes") # check exact description
        self.assertListEqual(parsed_items[3]['tags'], ["Apache-2.0", "Python/Docker"])


    def test_parse_markdown_item_variations(self):
        mock_markdown = """
### Personal Dashboards
- [Dashy](https://dashy.to/) - Feature-rich homepage for your homelab, with easy YAML configuration. `MIT` `Nodejs/Docker`
- [Homer](https://github.com/bastienwirtz/homer) - Dead simple static homepage. `Apache-2.0`
- [Homepage by gethomepage](https://github.com/gethomepage/homepage) - Highly customizable homepage.
- [NoTagsApp](https://notags.com) - Just a description.
        """
        original_categories = etl_script.CATEGORIES_OF_INTEREST
        etl_script.CATEGORIES_OF_INTEREST = ["Personal Dashboards"]

        parsed_items = etl_script.parse_markdown(mock_markdown)

        etl_script.CATEGORIES_OF_INTEREST = original_categories

        self.assertEqual(len(parsed_items), 4)

        # Test Dashy (all fields)
        self.assertEqual(parsed_items[0]['name'], "Dashy")
        self.assertEqual(parsed_items[0]['url'], "https://dashy.to/")
        self.assertIn("Feature-rich homepage", parsed_items[0]['description'])
        self.assertListEqual(parsed_items[0]['tags'], ["MIT", "Nodejs/Docker"])

        # Test Homer (one tag)
        self.assertEqual(parsed_items[1]['name'], "Homer")
        self.assertEqual(parsed_items[1]['url'], "https://github.com/bastienwirtz/homer")
        self.assertIn("Dead simple static homepage", parsed_items[1]['description'])
        self.assertListEqual(parsed_items[1]['tags'], ["Apache-2.0"])

        # Test Homepage by gethomepage (no tags in backticks in the main description part)
        self.assertEqual(parsed_items[2]['name'], "Homepage by gethomepage")
        self.assertEqual(parsed_items[2]['url'], "https://github.com/gethomepage/homepage")
        self.assertIn("Highly customizable homepage", parsed_items[2]['description'])
        self.assertIsNone(parsed_items[2]['tags']) # Expect None if no backticked tags

        # Test NoTagsApp (no tags)
        self.assertEqual(parsed_items[3]['name'], "NoTagsApp")
        self.assertEqual(parsed_items[3]['description'], "Just a description")
        self.assertIsNone(parsed_items[3]['tags'])


    def test_process_items(self):
        raw_data = [
            {
                "id": "1", "name": "App1", "url": "http://app1.com",
                "description": "Desc1", "category": "Cat1",
                "tags": ["Tag1"], "source": "awesome-selfhosted",
                "added_date": datetime(2023, 1, 1)
            },
            {
                "id": "2", "name": "App2", "url": "http://app2.com",
                "description": "Desc2", "category": "Cat2",
                "tags": None, "source": "awesome-selfhosted",
                "added_date": datetime(2023, 1, 2)
            }
        ]
        processed = etl_script.process_items(raw_data)
        self.assertEqual(len(processed), 2)
        self.assertIsInstance(processed[0], HomeServerTrendItem)
        self.assertEqual(processed[0].name, "App1")
        self.assertEqual(processed[1].name, "App2")
        self.assertEqual(processed[1].tags, None)

    @patch('src.etl.news.news_get_home_server_trends.ensure_directories')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.etl.news.news_get_home_server_trends.json.dump')
    @patch('src.etl.news.news_get_home_server_trends.csv.DictWriter')
    def test_save_data(self, mock_csv_writer, mock_json_dump, mock_file_open, mock_ensure_dirs):
        test_data = [
            HomeServerTrendItem(
                id="1", name="App1", url="http://app1.com", description="Desc1",
                category="Cat1", tags=["Test"], added_date=datetime.utcnow()
            )
        ]
        output_dir = "/test/output"

        etl_script.save_data(test_data, output_dir)

        mock_ensure_dirs.assert_called_once_with([output_dir])

        # Check JSON saving
        # Expect two calls to open for JSON (timestamped and latest)
        # and two calls for json.dump
        self.assertGreaterEqual(mock_file_open.call_count, 2) # At least 2 for JSON, more if CSV is written
        self.assertGreaterEqual(mock_json_dump.call_count, 2)

        # Check that open was called for the latest JSON file
        found_latest_json_open = False
        for call_args in mock_file_open.call_args_list:
            if call_args[0][0] == os.path.join(output_dir, "home_server_trends_latest.json"):
                found_latest_json_open = True
                break
        self.assertTrue(found_latest_json_open, "Latest JSON file was not opened for writing.")

        # Check CSV saving
        # Expect two calls to DictWriter.writeheader() and writerows() for CSV
        # (timestamped and latest)
        if test_data: # CSV writing happens only if data exists
             self.assertGreaterEqual(mock_csv_writer.return_value.writeheader.call_count, 2)
             self.assertGreaterEqual(mock_csv_writer.return_value.writerows.call_count, 2)


if __name__ == '__main__':
    unittest.main()
