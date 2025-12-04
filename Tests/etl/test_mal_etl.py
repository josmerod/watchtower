import json
import os
import pathlib
import shutil  # For rmtree

# Ensure src path is available for imports
import unittest
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import requests  # <--- Import requests

# Assuming the script is run from the project root or Tests/
# Adjust if your test runner has a different CWD
project_root = pathlib.Path(__file__).resolve().parent.parent.parent
from src.etl.anime.mal_etl import API_BASE_URL, FIELDS_TO_REQUEST, MalETL
from src.models.anime import AnimeItem


# Removed class decorator @patch('src.etl.anime.mal_etl.load_dotenv')
class TestMalETL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # This is run once for the entire class
        cls.original_output_dir = MalETL.output_dir if hasattr(MalETL, "output_dir") else None

    @classmethod
    def tearDownClass(cls):
        # Restore original output_dir if it was changed
        if cls.original_output_dir and hasattr(MalETL, "output_dir"):
            MalETL.output_dir = cls.original_output_dir

    def setUp(self):  # Original signature
        """Set up for each test method."""
        # Start patch for load_dotenv manually

        self.test_client_id = "test_mal_client_id_12345"
        os.environ["MAL_CLIENT_ID"] = self.test_client_id

        # Create a temporary directory for test outputs

        # Instantiate ETL and override its output directory
        self.etl = MalETL()
        self.etl.output_dir = self.test_output_dir

        # Sample API responses
        self.sample_anime_node_1 = {}
        self.sample_anime_node_2 = {}

        self.seasonal_response = {}
        self.popular_response = {}
        self.favorite_response = {}
        self.empty_response = {"data": [], "paging": {}}

    def tearDown(self):
        """Clean up after each test method."""
        # Stop the patcher
        self.load_dotenv_patcher.stop()

        if "MAL_CLIENT_ID" in os.environ:
            del os.environ["MAL_CLIENT_ID"]

        # Remove the temporary directory and its contents
        if self.test_output_dir.exists():
            shutil.rmtree(self.test_output_dir)

    def test_initialization_success(self):  # Removed mock_load_dotenv_arg
        """Test successful initialization of MalETL."""
        self.assertIsNotNone(self.etl)
        self.assertEqual(self.etl.client_id, self.test_client_id)
        self.assertEqual(self.etl.output_dir, self.test_output_dir)
        # self.mock_load_dotenv.assert_called_once() # Removed: This mock applies after module load.
        # The module-level load_dotenv in mal_etl.py has already run with the original by this point.
        # The purpose of this mock here is to prevent .env loading during test execution itself.

    def test_initialization_no_client_id(self):  # Removed mock_load_dotenv_arg
        """Test MalETL initialization fails if MAL_CLIENT_ID is not set."""
        del os.environ["MAL_CLIENT_ID"]
        with self.assertRaises(ValueError) as context:
            MalETL()
        self.assertIn("MAL_CLIENT_ID environment variable not set", str(context.exception))
        os.environ["MAL_CLIENT_ID"] = self.test_client_id

    @patch("src.etl.anime.mal_etl.requests.get")
    def test_make_request_success(self, mock_requests_get):  # Removed mock_load_dotenv
        """Test successful API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "success"}
        mock_requests_get.return_value = mock_response

        endpoint = "/anime/season/2023/summer"
        params = {"limit": 1}
        result = self.etl._make_request(endpoint, params)

        expected_url = f"{API_BASE_URL}{endpoint}"
        mock_requests_get.assert_called_once_with(expected_url, headers={"X-MAL-CLIENT-ID": self.test_client_id, "User-Agent": "WatchtowerMALETL/1.0"}, params=params, timeout=30)
        self.assertEqual(result, {"data": "success"})

    @patch("src.etl.anime.mal_etl.requests.get")
    def test_make_request_http_error(self, mock_requests_get):  # Removed mock_load_dotenv
        """Test API request failure due to HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        # Create an HTTPError instance with a 'response' attribute
        http_error = requests.exceptions.HTTPError("404 Client Error")
        error_response_mock = MagicMock()
        http_error.response = error_response_mock

        mock_response.raise_for_status.side_effect = http_error
        mock_requests_get.return_value = mock_response

        with patch("src.etl.anime.mal_etl.logger.error") as mock_logger_error:
            result = self.etl._make_request("/some_endpoint")
            self.assertIsNone(result)
            mock_logger_error.assert_called()

    @patch("src.etl.anime.mal_etl.requests.get")
    def test_make_request_connection_error(self, mock_requests_get):  # Removed mock_load_dotenv
        """Test API request failure due to connection error."""
        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with patch("src.etl.anime.mal_etl.logger.error") as mock_logger_error:
            result = self.etl._make_request("/another_endpoint")
            self.assertIsNone(result)
            mock_logger_error.assert_called()

    def test_transform_data(self):  # Removed mock_load_dotenv
        """Test transformation of raw API data to AnimeItem models."""
        raw_data_input = {}

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

    def test_transform_data_malformed_node(self):  # Removed mock_load_dotenv
        """Test transformation with some items having malformed/missing node data."""
        malformed_seasonal_response = {"data": [{"node": self.sample_anime_node_1}, {"node": None}, {}], "paging": {}}
        raw_data_input = {"seasonal": malformed_seasonal_response}

        transformed_output = self.etl.transform(raw_data_input)
        self.assertEqual(len(transformed_output["seasonal"]), 1)
        self.assertEqual(transformed_output["seasonal"][0].id, self.sample_anime_node_1["id"])

    @patch.object(MalETL, "_make_request")
    def test_extract_transform_load_flow(self, mock_make_request):  # Removed mock_load_dotenv
        mock_make_request.side_effect = [self.seasonal_response, self.popular_response, self.favorite_response]

        self.etl.run()

        now = datetime.now()
        current_year = now.year
        month = now.month
        if 1 <= month <= 3:
            current_season = "winter"
        elif 4 <= month <= 6:
            current_season = "spring"
        elif 7 <= month <= 9:
            current_season = "summer"
        else:
            current_season = "fall"

        expected_calls = [
            call(f"/anime/season/{current_year}/{current_season}", params=FIELDS_TO_REQUEST),
            call("/anime/ranking", params={**FIELDS_TO_REQUEST, "ranking_type": "all", "limit": 10}),
            call("/anime/ranking", params={**FIELDS_TO_REQUEST, "ranking_type": "favorite", "limit": 10}),
        ]
        mock_make_request.assert_has_calls(expected_calls, any_order=False)
        self.assertEqual(mock_make_request.call_count, 3)

        seasonal_file = self.test_output_dir / "current_season_anime.json"
        popular_file = self.test_output_dir / "top_popular_anime.json"
        favorite_file = self.test_output_dir / "top_favorite_anime.json"

        self.assertTrue(seasonal_file.exists())
        self.assertTrue(popular_file.exists())
        self.assertTrue(favorite_file.exists())

        with open(seasonal_file) as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], self.sample_anime_node_1["title"])
        self.assertEqual(data[0]["id"], self.sample_anime_node_1["id"])
        self.assertEqual(data[0]["mean"], self.sample_anime_node_1["mean"])
        self.assertIn("main_picture", data[0])
        self.assertEqual(data[0]["main_picture"]["large"], self.sample_anime_node_1["main_picture"]["large"])

    @patch.object(MalETL, "_make_request")
    def test_run_with_one_api_failure(self, mock_make_request):  # Removed mock_load_dotenv
        """Test ETL run when one of the API calls fails."""
        mock_make_request.side_effect = [self.seasonal_response, None, self.favorite_response]

        self.etl.run()

        seasonal_file = self.test_output_dir / "current_season_anime.json"
        favorite_file = self.test_output_dir / "top_favorite_anime.json"
        popular_file = self.test_output_dir / "top_popular_anime.json"

        self.assertTrue(seasonal_file.exists())
        self.assertTrue(favorite_file.exists())

        if popular_file.exists():
            with open(popular_file) as f:
                popular_data = json.load(f)
            self.assertEqual(len(popular_data), 0)

        with open(seasonal_file) as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], self.sample_anime_node_1["id"])


if __name__ == "__main__":
    unittest.main()
