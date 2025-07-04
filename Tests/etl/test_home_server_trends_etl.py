# Tests/etl/test_home_server_trends_etl.py
import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import requests  # Import requests for requests.exceptions.RequestException

# Add project root to sys.path to allow imports from src
# Now import the module to be tested
from src.etl.news import news_get_home_server_trends as etl_script
from src.models.home_server import HomeServerTrendItem


class TestHomeServerTrendsETL(unittest.TestCase):
    @patch("src.etl.news.news_get_home_server_trends.requests.Session.get")
    def test_fetch_markdown_content_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """### Test Category
- [App1](http://app1.com) - Desc1."""
        mock_get.return_value = mock_response

        dummy_url = "http://dummyurl.com/README.md"
        dummy_source_name = "dummy_source"

        session = etl_script.create_session()  # Use the actual session creator
        content = etl_script.fetch_markdown_content(
            session, dummy_url, dummy_source_name
        )
        assert content is not None
        assert content == mock_response.text
        mock_get.assert_called_once_with(dummy_url, timeout=30)

    @patch("src.etl.news.news_get_home_server_trends.requests.Session.get")
    def test_fetch_markdown_content_failure(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException(
            "Test network error"
        )

        dummy_url = "http://dummyurl.com/README.md"
        dummy_source_name = "dummy_source"
        session = etl_script.create_session()
        content = etl_script.fetch_markdown_content(
            session, dummy_url, dummy_source_name
        )
        assert content is None

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

        parsed_items = etl_script.parse_markdown(
            mock_markdown, test_categories, test_source_name
        )

        assert len(parsed_items) == 4

        assert parsed_items[0]["name"] == "Plausible Analytics"
        assert parsed_items[0]["category"] == "Analytics"
        assert parsed_items[0]["url"] == "https://plausible.io/"
        assert "Simple, lightweight" in parsed_items[0]["description"]
        self.assertListEqual(parsed_items[0]["tags"], ["AGPL-3.0", "Elixir"])
        assert parsed_items[0]["source"] == test_source_name

        assert parsed_items[1]["name"] == "Matomo"
        assert parsed_items[1]["category"] == "Analytics"
        assert parsed_items[1]["source"] == test_source_name

        assert parsed_items[2]["name"] == "Huginn"
        assert parsed_items[2]["category"] == "Automation"
        assert parsed_items[2]["source"] == test_source_name

        assert parsed_items[3]["name"] == "changedetection.io"
        assert parsed_items[3]["description"] == "Stay up-to-date with web-site content changes"  # check exact description
        self.assertListEqual(parsed_items[3]["tags"], ["Apache-2.0", "Python/Docker"])
        assert parsed_items[3]["source"] == test_source_name

    def test_parse_markdown_item_variations(self):
        mock_markdown = """
### Personal Dashboards
- [Dashy](https://dashy.to/) - Feature-rich homepage for your homelab, with easy YAML configuration. `MIT` `Nodejs/Docker`
        """
        test_categories = ["Personal Dashboards"]
        test_source_name = "test_source_variations"

        parsed_items = etl_script.parse_markdown(
            mock_markdown, test_categories, test_source_name
        )

        assert len(parsed_items) == 4

        # Test Dashy (all fields)
        assert parsed_items[0]["name"] == "Dashy"
        assert parsed_items[0]["url"] == "https://dashy.to/"
        assert "Feature-rich homepage" in parsed_items[0]["description"]
        self.assertListEqual(parsed_items[0]["tags"], ["MIT", "Nodejs/Docker"])
        assert parsed_items[0]["source"] == test_source_name

        # Test Homer (one tag)
        assert parsed_items[1]["name"] == "Homer"
        assert parsed_items[1]["url"] == "https://github.com/bastienwirtz/homer"
        assert "Dead simple static homepage" in parsed_items[1]["description"]
        self.assertListEqual(parsed_items[1]["tags"], ["Apache-2.0"])
        assert parsed_items[1]["source"] == test_source_name

        # Test Homepage by gethomepage (no tags in backticks in the main description part)
        assert parsed_items[2]["name"] == "Homepage by gethomepage"
        assert parsed_items[2]["url"] == "https://github.com/gethomepage/homepage"
        assert "Highly customizable homepage" in parsed_items[2]["description"]
        assert parsed_items[2]["tags"] is None  # Expect None if no backticked tags
        assert parsed_items[2]["source"] == test_source_name

        # Test NoTagsApp (no tags)
        assert parsed_items[3]["name"] == "NoTagsApp"
        assert parsed_items[3]["description"] == "Just a description"
        assert parsed_items[3]["tags"] is None
        assert parsed_items[3]["source"] == test_source_name

    def test_process_items(self):
        raw_data = [{}, {}]
        processed = etl_script.process_items(raw_data)
        assert len(processed) == 2
        assert isinstance(processed[0], HomeServerTrendItem)
        assert processed[0].name == "App1"
        assert processed[1].name == "App2"
        assert processed[1].tags is None

    @patch("src.etl.news.news_get_home_server_trends.ensure_directories")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.etl.news.news_get_home_server_trends.json.dump")
    @patch("src.etl.news.news_get_home_server_trends.csv.DictWriter")
    def test_save_data(
        self, mock_csv_writer, mock_json_dump, mock_file_open, mock_ensure_dirs
    ):
        test_data = [
            HomeServerTrendItem(
                id="1",
                name="App1",
                url="http://app1.com",
                description="Desc1",
                category="Cat1",
                tags=["Test"],
                added_date=datetime.utcnow(),
            )
        ]
        output_dir = "/test/output"

        etl_script.save_data(test_data, output_dir)

        mock_ensure_dirs.assert_called_once_with([output_dir])

        # Check JSON saving
        # Expect two calls to open for JSON (timestamped and latest)
        # and two calls for json.dump
        assert mock_file_open.call_count >= 2  # At least 2 for JSON, more if CSV is written
        assert mock_json_dump.call_count >= 2

        # Check that open was called for the latest JSON file
        found_latest_json_open = False
        for call_args in mock_file_open.call_args_list:
            if call_args[0][0] == os.path.join(
                output_dir, "home_server_trends_latest.json"
            ):
                found_latest_json_open = True
                break
        assert found_latest_json_open, "Latest JSON file was not opened for writing."

        # Check CSV saving
        # Expect two calls to DictWriter.writeheader() and writerows() for CSV
        # (timestamped and latest)
        if test_data:  # CSV writing happens only if data exists
            assert mock_csv_writer.return_value.writeheader.call_count >= 2
            assert mock_csv_writer.return_value.writerows.call_count >= 2

    @patch("src.etl.news.news_get_home_server_trends.fetch_markdown_content")
    @patch(
        "src.etl.news.news_get_home_server_trends.process_items",
        side_effect=lambda items: items,
    )  # Pass through
    @patch("src.etl.news.news_get_home_server_trends.save_data")
    def test_main_flow_with_multiple_sources_and_deduplication(
        self, mock_save_data, mock_process_items, mock_fetch
    ):
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
        """

        def fetch_side_effect(session, url, source_name_for_log):
            if url == etl_script.AWESOME_SELFHOSTED_URL:
                return mock_md_source1
            elif (
                url == etl_script.AWESOME_HOME_AUTOMATION_URL
            ):  # Ensure this constant exists in etl_script
                return mock_md_source2
            return None

        mock_fetch.side_effect = fetch_side_effect

        # Define categories for each source for the test
        # These need to be set on the module if they are read from the module's global scope in main()

        # Call the main function
        etl_script.main()

        # Assertions:
        # 1. process_items should have been called with de-duplicated items
        assert mock_process_items.called
        processed_args = mock_process_items.call_args[0][
            0
        ]  # Get the first argument passed to process_items

        assert len(processed_args) == 3  # App1, App2, App3 (App1 from source2 should be a duplicate)

        names_in_processed = {item["name"] for item in processed_args}
        self.assertSetEqual(names_in_processed, {"App1", "App2", "App3"})

        # Check sources (App1 should ideally be from the first source encountered, or based on a chosen strategy)
        # For this test, assuming first-come-first-served for duplicates based on ID
        app1_data = next(item for item in processed_args if item["name"] == "App1")
        assert app1_data["source"] == "awesome-selfhosted"  # Assuming this is processed first

        app2_data = next(item for item in processed_args if item["name"] == "App2")
        assert app2_data["source"] == "awesome-selfhosted"

        app3_data = next(item for item in processed_args if item["name"] == "App3")
        assert app3_data["source"] == "awesome-home-automation"

        # 2. save_data should have been called
        assert mock_save_data.called

        # Restore original categories


if __name__ == "__main__":
    unittest.main()
