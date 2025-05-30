import unittest
from unittest.mock import patch, MagicMock, call
import os
import json
import pathlib
import shutil # For rmtree
from datetime import datetime
import requests # <--- Import requests

# Ensure src path is available for imports
import sys
# Assuming the script is run from the project root or Tests/
# Adjust if your test runner has a different CWD
project_root = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.etl.anime.mal_etl import MalETL, FIELDS_TO_REQUEST, API_BASE_URL
from src.models.anime import AnimeItem

class TestMalETL(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # This is run once for the entire class
        cls.original_output_dir = MalETL.output_dir if hasattr(MalETL, 'output_dir') else None


    @classmethod
    def tearDownClass(cls):
        # Restore original output_dir if it was changed
        if cls.original_output_dir and hasattr(MalETL, 'output_dir'):
             MalETL.output_dir = cls.original_output_dir


    def setUp(self):
        """Set up for each test method."""
        self.test_client_id = "test_mal_client_id_12345"
        os.environ["MAL_CLIENT_ID"] = self.test_client_id

        # Create a temporary directory for test outputs
        self.test_output_dir = pathlib.Path("Tests/temp_anime_data")
        self.test_output_dir.mkdir(parents=True, exist_ok=True)

        # Instantiate ETL and override its output directory
        # We need to ensure the class uses this path.
        # MalETL's __init__ sets self.output_dir. We'll patch that instance's output_dir.
        self.etl = MalETL()
        self.etl.output_dir = self.test_output_dir # Override instance's output_dir

        # Sample API responses
        self.sample_anime_node_1 = {
            "id": 1, "title": "Anime Title 1", "mean": 8.5, "rank": 100,
            "popularity": 150, "num_episodes": 12, "media_type": "tv",
            "main_picture": {"medium": "url_m1", "large": "url_l1"}
        }
        self.sample_anime_node_2 = {
            "id": 2, "title": "Anime Title 2", "mean": 9.0, "rank": 50,
            "popularity": 10, "num_episodes": 24, "media_type": "movie",
            "main_picture": {"medium": "url_m2", "large": "url_l2"}
        }
        self.sample_anime_node_3 = { # For a different category
            "id": 3, "title": "Anime Title 3", "mean": 7.5, "rank": 500,
            "popularity": 300, "num_episodes": 1, "media_type": "ova",
            "main_picture": {"medium": "url_m3", "large": "url_l3"}
        }

        self.seasonal_response = {
            "data": [{"node": self.sample_anime_node_1}],
            "paging": {"next": "next_url"}
        }
        self.popular_response = {
            "data": [{"node": self.sample_anime_node_2}],
            "paging": {"next": "next_url"}
        }
        self.favorite_response = {
            "data": [{"node": self.sample_anime_node_3}],
            "paging": {"next": "next_url"}
        }
        self.empty_response = {"data": [], "paging": {}}


    def tearDown(self):
        """Clean up after each test method."""
        if "MAL_CLIENT_ID" in os.environ:
            del os.environ["MAL_CLIENT_ID"]

        # Remove the temporary directory and its contents
        if self.test_output_dir.exists():
            shutil.rmtree(self.test_output_dir)

    def test_initialization_success(self):
        """Test successful initialization of MalETL."""
        self.assertIsNotNone(self.etl)
        self.assertEqual(self.etl.client_id, self.test_client_id)
        # Check if the output_dir was correctly overridden for the instance
        self.assertEqual(self.etl.output_dir, self.test_output_dir)

    def test_initialization_no_client_id(self):
        """Test MalETL initialization fails if MAL_CLIENT_ID is not set."""
        del os.environ["MAL_CLIENT_ID"]
        with self.assertRaises(ValueError) as context:
            MalETL()
        self.assertIn("MAL_CLIENT_ID environment variable not set", str(context.exception))
        # Restore for other tests if they don't run setUp again (though they should)
        os.environ["MAL_CLIENT_ID"] = self.test_client_id


    @patch('src.etl.anime.mal_etl.requests.get')
    def test_make_request_success(self, mock_requests_get):
        """Test successful API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "success"}
        mock_requests_get.return_value = mock_response

        endpoint = "/anime/season/2023/summer"
        params = {"limit": 1}
        result = self.etl._make_request(endpoint, params)

        expected_url = f"{API_BASE_URL}{endpoint}"
        mock_requests_get.assert_called_once_with(
            expected_url,
            headers={"X-MAL-CLIENT-ID": self.test_client_id, "User-Agent": "WatchtowerMALETL/1.0"},
            params=params,
            timeout=30
        )
        self.assertEqual(result, {"data": "success"})

    @patch('src.etl.anime.mal_etl.requests.get')
    def test_make_request_http_error(self, mock_requests_get):
        """Test API request failure due to HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        # Create an HTTPError instance with a 'response' attribute
        http_error = requests.exceptions.HTTPError("404 Client Error")
        error_response_mock = MagicMock()
        error_response_mock.text = "Mocked error response text"
        http_error.response = error_response_mock

        mock_response.raise_for_status.side_effect = http_error
        # mock_response.text itself is not what e.response.text refers to.
        mock_requests_get.return_value = mock_response

        # Suppress error logging during this test for cleaner output
        with patch('src.etl.anime.mal_etl.logger.error') as mock_logger_error:
            result = self.etl._make_request("/some_endpoint")
            self.assertIsNone(result)
            mock_logger_error.assert_called() # Check that an error was logged

    @patch('src.etl.anime.mal_etl.requests.get')
    def test_make_request_connection_error(self, mock_requests_get):
        """Test API request failure due to connection error."""
        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with patch('src.etl.anime.mal_etl.logger.error') as mock_logger_error:
            result = self.etl._make_request("/another_endpoint")
            self.assertIsNone(result)
            mock_logger_error.assert_called()


    def test_transform_data(self):
        """Test transformation of raw API data to AnimeItem models."""
        raw_data_input = {
            "seasonal": self.seasonal_response, # Contains node_1
            "popular": self.popular_response,   # Contains node_2
            "favorite": self.empty_response     # Contains no nodes
        }

        transformed_output = self.etl.transform(raw_data_input)

        self.assertIn("seasonal", transformed_output)
        self.assertIn("popular", transformed_output)
        self.assertIn("favorite", transformed_output)

        self.assertEqual(len(transformed_output["seasonal"]), 1)
        self.assertIsInstance(transformed_output["seasonal"][0], AnimeItem)
        self.assertEqual(transformed_output["seasonal"][0].title, self.sample_anime_node_1["title"])
        self.assertEqual(transformed_output["seasonal"][0].id, self.sample_anime_node_1["id"])

        self.assertEqual(len(transformed_output["popular"]), 1)
        self.assertIsInstance(transformed_output["popular"][0], AnimeItem)
        self.assertEqual(transformed_output["popular"][0].title, self.sample_anime_node_2["title"])

        self.assertEqual(len(transformed_output["favorite"]), 0)

    def test_transform_data_malformed_node(self):
        """Test transformation with some items having malformed/missing node data."""
        malformed_seasonal_response = {
            "data": [
                {"node": self.sample_anime_node_1},
                {"node": None}, # Missing node
                {} # Entirely empty item
            ],
            "paging": {"next": "next_url"}
        }
        raw_data_input = {"seasonal": malformed_seasonal_response}

        transformed_output = self.etl.transform(raw_data_input)
        self.assertEqual(len(transformed_output["seasonal"]), 1) # Only one valid node
        self.assertEqual(transformed_output["seasonal"][0].id, self.sample_anime_node_1["id"])


    @patch.object(MalETL, '_make_request')
    def test_extract_transform_load_flow(self, mock_make_request):
        """Test the full ETL flow: extract, transform, and load."""

        # Configure side_effect for multiple calls to _make_request
        # Order: seasonal, popular, favorite
        mock_make_request.side_effect = [
            self.seasonal_response,
            self.popular_response,
            self.favorite_response
        ]

        # Run the ETL process (which calls extract, transform, load)
        self.etl.run()

        # Assert _make_request calls
        # Get current year and season for precise call checking
        now = datetime.now()
        current_year = now.year
        month = now.month
        if 1 <= month <= 3: current_season = "winter"
        elif 4 <= month <= 6: current_season = "spring"
        elif 7 <= month <= 9: current_season = "summer"
        else: current_season = "fall"

        expected_calls = [
            call(f"/anime/season/{current_year}/{current_season}",
                 {"limit": 20, "sort": "anime_num_list_users", "fields": FIELDS_TO_REQUEST}),
            call("/anime/ranking",
                 {"ranking_type": "bypopularity", "limit": 20, "fields": FIELDS_TO_REQUEST}),
            call("/anime/ranking",
                 {"ranking_type": "favorite", "limit": 20, "fields": FIELDS_TO_REQUEST})
        ]
        mock_make_request.assert_has_calls(expected_calls, any_order=False)
        self.assertEqual(mock_make_request.call_count, 3)

        # Assert that output files were created
        seasonal_file = self.test_output_dir / "current_season_anime.json"
        popular_file = self.test_output_dir / "top_popular_anime.json"
        favorite_file = self.test_output_dir / "top_favorite_anime.json"

        self.assertTrue(seasonal_file.exists())
        self.assertTrue(popular_file.exists())
        self.assertTrue(favorite_file.exists())

        # Verify content of one file (e.g., seasonal)
        with open(seasonal_file, 'r') as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], self.sample_anime_node_1['title'])
        self.assertEqual(data[0]['id'], self.sample_anime_node_1['id'])
        self.assertEqual(data[0]['mean'], self.sample_anime_node_1['mean'])
        # Check main_picture structure
        self.assertIn('main_picture', data[0])
        self.assertEqual(data[0]['main_picture']['large'], self.sample_anime_node_1['main_picture']['large'])


    @patch.object(MalETL, '_make_request')
    def test_run_with_one_api_failure(self, mock_make_request):
        """Test ETL run when one of the API calls fails."""
        mock_make_request.side_effect = [
            self.seasonal_response,
            None,  # Popular fetch fails
            self.favorite_response
        ]

        self.etl.run()

        # Check that files for successful calls were created
        seasonal_file = self.test_output_dir / "current_season_anime.json"
        favorite_file = self.test_output_dir / "top_favorite_anime.json"
        popular_file = self.test_output_dir / "top_popular_anime.json" # Should not be created or be empty

        self.assertTrue(seasonal_file.exists())
        self.assertTrue(favorite_file.exists())

        if popular_file.exists():
            with open(popular_file, 'r') as f:
                popular_data = json.load(f)
            self.assertEqual(len(popular_data), 0) # Or file might not exist, depends on load behavior

        with open(seasonal_file, 'r') as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.sample_anime_node_1['id'])


if __name__ == '__main__':
    # Need to import requests for the side_effect in test_make_request_http_error
    import requests
    unittest.main()
