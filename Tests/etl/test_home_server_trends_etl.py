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
# Now import the module to be tested
from src.etl.news import news_get_home_server_trends as etl_script
from src.models.home_server import HomeServerTrendItem

class TestHomeServerTrendsETL(unittest.TestCase):

    @patch('src.etl.news.news_get_home_server_trends.requests.Session.get')
    def test_fetch_markdown_content_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """### Test Category
- [App1](http://app1.com) - Desc1."""
        mock_get.return_value = mock_response

        dummy_url = "http://dummyurl.com/README.md"
        dummy_source_name = "dummy_source"

        session = etl_script.create_session() # Use the actual session creator
        content = etl_script.fetch_markdown_content(session, dummy_url, dummy_source_name)
        self.assertIsNotNone(content)
        self.assertEqual(content, mock_response.text)
        mock_get.assert_called_once_with(dummy_url, timeout=30)

    @patch('src.etl.news.news_get_home_server_trends.requests.Session.get')
    def test_fetch_markdown_content_failure(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Test network error")

        dummy_url = "http://dummyurl.com/README.md"
        dummy_source_name = "dummy_source"
        session = etl_script.create_session()
        content = etl_script.fetch_markdown_content(session, dummy_url, dummy_source_name)
        self.assertIsNone(content)

    def test_parse_markdown(self):
        mock_markdown = """
# Some Title

## Some Section

### Analytics

### Not Interesting Category

### Automation
- [changedetection.io](https://changedetection.io/) - Stay up-to-date with web-site content changes. `Apache-2.0` `Python/Docker`
        """
        test_categories = ["Analytics", "Automation"]
        test_source_name = "test_source_markdown"

        parsed_items = etl_script.parse_markdown(mock_markdown, test_categories, test_source_name)

        self.assertEqual(len(parsed_items), 4)

        self.assertEqual(parsed_items[0]['name'], "Plausible Analytics")
        self.assertEqual(parsed_items[0]['category'], "Analytics")
        self.assertEqual(parsed_items[0]['url'], "https://plausible.io/")
        self.assertIn("Simple, lightweight", parsed_items[0]['description'])
        self.assertListEqual(parsed_items[0]['tags'], ["AGPL-3.0", "Elixir"])
        self.assertEqual(parsed_items[0]['source'], test_source_name)

        self.assertEqual(parsed_items[1]['name'], "Matomo")
        self.assertEqual(parsed_items[1]['category'], "Analytics")
        self.assertEqual(parsed_items[1]['source'], test_source_name)

        self.assertEqual(parsed_items[2]['name'], "Huginn")
        self.assertEqual(parsed_items[2]['category'], "Automation")
        self.assertEqual(parsed_items[2]['source'], test_source_name)

        self.assertEqual(parsed_items[3]['name'], "changedetection.io")
        self.assertEqual(parsed_items[3]['description'], "Stay up-to-date with web-site content changes") # check exact description
        self.assertListEqual(parsed_items[3]['tags'], ["Apache-2.0", "Python/Docker"])
        self.assertEqual(parsed_items[3]['source'], test_source_name)


    def test_parse_markdown_item_variations(self):
        mock_markdown = """
### Personal Dashboards
- [Dashy](https://dashy.to/) - Feature-rich homepage for your homelab, with easy YAML configuration. `MIT` `Nodejs/Docker`
        """
        test_categories = ["Personal Dashboards"]
        test_source_name = "test_source_variations"

        parsed_items = etl_script.parse_markdown(mock_markdown, test_categories, test_source_name)

        self.assertEqual(len(parsed_items), 4)

        # Test Dashy (all fields)
        self.assertEqual(parsed_items[0]['name'], "Dashy")
        self.assertEqual(parsed_items[0]['url'], "https://dashy.to/")
        self.assertIn("Feature-rich homepage", parsed_items[0]['description'])
        self.assertListEqual(parsed_items[0]['tags'], ["MIT", "Nodejs/Docker"])
        self.assertEqual(parsed_items[0]['source'], test_source_name)

        # Test Homer (one tag)
        self.assertEqual(parsed_items[1]['name'], "Homer")
        self.assertEqual(parsed_items[1]['url'], "https://github.com/bastienwirtz/homer")
        self.assertIn("Dead simple static homepage", parsed_items[1]['description'])
        self.assertListEqual(parsed_items[1]['tags'], ["Apache-2.0"])
        self.assertEqual(parsed_items[1]['source'], test_source_name)

        # Test Homepage by gethomepage (no tags in backticks in the main description part)
        self.assertEqual(parsed_items[2]['name'], "Homepage by gethomepage")
        self.assertEqual(parsed_items[2]['url'], "https://github.com/gethomepage/homepage")
        self.assertIn("Highly customizable homepage", parsed_items[2]['description'])
        self.assertIsNone(parsed_items[2]['tags']) # Expect None if no backticked tags
        self.assertEqual(parsed_items[2]['source'], test_source_name)

        # Test NoTagsApp (no tags)
        self.assertEqual(parsed_items[3]['name'], "NoTagsApp")
        self.assertEqual(parsed_items[3]['description'], "Just a description")
        self.assertIsNone(parsed_items[3]['tags'])
        self.assertEqual(parsed_items[3]['source'], test_source_name)


    def test_process_items(self):
        raw_data = [
            {




            },
            {




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

    @patch('src.etl.news.news_get_home_server_trends.fetch_markdown_content')
    @patch('src.etl.news.news_get_home_server_trends.process_items', side_effect=lambda items: items) # Pass through
    @patch('src.etl.news.news_get_home_server_trends.save_data')
    def test_main_flow_with_multiple_sources_and_deduplication(self, mock_save_data, mock_process_items, mock_fetch):
        # Mock return values for fetch_markdown_content
        # Source 1: awesome-selfhosted
        mock_md_source1 = """
### Analytics
- [App1](http://app1.com) - Desc1. `MIT`
- [App2](http://app2.com) - Desc2. `GPL`
        """
        # Source 2: awesome-home-automation (hypothetical)
        mock_md_source2 = """
## Software Platforms
- [App1](http://app1.com) - Desc1 from HA list. `MIT`
- [App3](http://app3.com) - Desc3 for HA. `Apache-2.0`

        def fetch_side_effect(session, url, source_name_for_log):
            if url == etl_script.AWESOME_SELFHOSTED_URL:
                return mock_md_source1
            elif url == etl_script.AWESOME_HOME_AUTOMATION_URL: # Ensure this constant exists in etl_script
                return mock_md_source2
            return None

        mock_fetch.side_effect = fetch_side_effect

        # Define categories for each source for the test
        # These need to be set on the module if they are read from the module's global scope in main()
        original_as_categories = etl_script.AWESOME_SELFHOSTED_CATEGORIES
        original_ha_categories = etl_script.HOME_AUTOMATION_CATEGORIES


        # Call the main function
        etl_script.main()

        # Assertions:
        # 1. process_items should have been called with de-duplicated items
        self.assertTrue(mock_process_items.called)
        processed_args = mock_process_items.call_args[0][0] # Get the first argument passed to process_items

        self.assertEqual(len(processed_args), 3) # App1, App2, App3 (App1 from source2 should be a duplicate)

        names_in_processed = {item['name'] for item in processed_args}
        self.assertSetEqual(names_in_processed, {"App1", "App2", "App3"})

        # Check sources (App1 should ideally be from the first source encountered, or based on a chosen strategy)
        # For this test, assuming first-come-first-served for duplicates based on ID
        app1_data = next(item for item in processed_args if item['name'] == 'App1')
        self.assertEqual(app1_data['source'], 'awesome-selfhosted') # Assuming this is processed first

        app2_data = next(item for item in processed_args if item['name'] == 'App2')
        self.assertEqual(app2_data['source'], 'awesome-selfhosted')

        app3_data = next(item for item in processed_args if item['name'] == 'App3')
        self.assertEqual(app3_data['source'], 'awesome-home-automation')


        # 2. save_data should have been called
        self.assertTrue(mock_save_data.called)

        # Restore original categories


if __name__ == '__main__':
    unittest.main()
