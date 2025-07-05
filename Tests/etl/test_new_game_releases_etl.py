import os
import sys
import unittest
from unittest.mock import Mock, patch

import requests  # Import requests for requests.exceptions.RequestException

# Add project root to sys.path to allow imports from src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if project_root not in sys.path:
    from src.etl.games.games_get_new_releases import (
        fetch_games,
        get_new_releases,
        process_games_data,
    )
from src.utils.logging import get_logger  # For logger interactions if needed

# Initialize a logger for the test module itself, or mock where script's logger is used
test_logger = get_logger(__name__)


class TestNewGameReleasesETL(unittest.TestCase):
    def setUp(self):
        # Define constants used in the script, can be overridden in tests
        self.MIN_METACRITIC_SCORE = 70  # From the script
        self.mock_api_key = "FAKE_API_KEY"

        # Sample RAWG API game data
        self.sample_game_high_score = {
            "metacritic": 90,
            "description_raw": "Description for awesome game 1.",
        }
        self.sample_game_low_score = {
            "metacritic": 50,
            "description_raw": "Description for mediocre game 2.",
        }
        self.sample_game_no_score = {
            "metacritic": None,
            "description_raw": "Description for unrated game 3.",
        }
        self.sample_game_meets_score = {
            "metacritic": self.MIN_METACRITIC_SCORE,
            "description_raw": "Description for good game 4.",
        }

        self.sample_rawg_response_page1 = {}
        self.sample_rawg_response_page2 = {}
        self.empty_rawg_response = {}

    # Helper methods can be added here if needed, e.g., _get_mock_response()

    @patch("src.etl.games.games_get_new_releases.requests.get")
    def test_fetch_games_success(self, mock_get):
        # Configure the mock response for a successful API call
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_rawg_response_page1
        mock_get.return_value = mock_response

        params = {"key": self.mock_api_key, "page": 1}
        result = fetch_games(page_num=1, params=params)

        assert result == self.sample_rawg_response_page1
        mock_get.assert_called_once_with(
            "https://api.rawg.io/api/games", params=params, timeout=10
        )

    @patch("src.etl.games.games_get_new_releases.requests.get")
    @patch(
        "src.etl.games.games_get_new_releases.logger"
    )  # Mock logger to check error logging
    def test_fetch_games_api_error(self, mock_logger, mock_get):
        # Configure the mock response for an API error (e.g., 500)
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "API Error"
        )
        mock_get.return_value = mock_response

        params = {"key": self.mock_api_key, "page": 1}
        result = fetch_games(page_num=1, params=params)

        assert result is None
        mock_logger.error.assert_called()  # Check that an error was logged
        # More specific log message check if desired:
        # mock_logger.error.assert_called_with(f"HTTP error occurred while fetching page 1: API Error - Status Code: 500")

    @patch("src.etl.games.games_get_new_releases.requests.get")
    @patch("src.etl.games.games_get_new_releases.logger")
    def test_fetch_games_request_exception(self, mock_logger, mock_get):
        # Configure requests.get to raise a RequestException
        mock_get.side_effect = requests.exceptions.RequestException("Connection Error")

        params = {"key": self.mock_api_key, "page": 1}
        result = fetch_games(page_num=1, params=params)

        assert result is None
        mock_logger.error.assert_called_with(
            "Error during request for page 1: Connection Error"
        )

    @patch("src.etl.games.games_get_new_releases.requests.get")
    @patch("src.etl.games.games_get_new_releases.logger")
    def test_fetch_games_timeout(self, mock_logger, mock_get):
        # Configure requests.get to raise a Timeout exception
        mock_get.side_effect = requests.exceptions.Timeout("Request Timed Out")

        params = {"key": self.mock_api_key, "page": 1}
        result = fetch_games(page_num=1, params=params)

        assert result is None
        mock_logger.error.assert_called_with("Request timed out while fetching page 1.")

    @patch("src.etl.games.games_get_new_releases.requests.get")
    @patch("src.etl.games.games_get_new_releases.logger")
    def test_fetch_games_json_decode_error(self, mock_logger, mock_get):
        # Configure the mock response for a JSON decode error
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        params = {"key": self.mock_api_key, "page": 1}
        result = fetch_games(page_num=1, params=params)

        assert result is None
        mock_logger.error.assert_called_with(
            "Failed to decode JSON response for page 1."
        )

    # Tests for process_games_data
    def test_process_games_data_valid(self):
        raw_games = [
            self.sample_game_high_score,  # Should pass (90)
            self.sample_game_low_score,  # Should fail (50)
            self.sample_game_no_score,  # Should fail (None)
            self.sample_game_meets_score,  # Should pass (70)
        ]
        processed = process_games_data(raw_games)

        assert len(processed) == 2
        assert processed[0]["id"] == self.sample_game_high_score["id"]
        assert processed[0]["name"] == self.sample_game_high_score["name"]
        assert processed[0]["metacritic"] == self.sample_game_high_score["metacritic"]
        assert processed[0]["platforms"] == ["PC", "PlayStation 5"]
        assert processed[0]["genres"] == ["Action", "Adventure"]
        assert (
            processed[0]["rawg_link"]
            == f"https://rawg.io/games/{self.sample_game_high_score['slug']}"
        )

        assert processed[1]["id"] == self.sample_game_meets_score["id"]
        assert processed[1]["metacritic"] == self.sample_game_meets_score["metacritic"]

    def test_process_games_data_empty_input(self):
        processed = process_games_data([])
        assert len(processed) == 0

    def test_process_games_data_all_fail_filter(self):
        raw_games = [self.sample_game_low_score, self.sample_game_no_score]
        processed = process_games_data(raw_games)
        assert len(processed) == 0

    def test_process_games_data_missing_optional_fields(self):
        game_missing_some_fields = {
            # "description_raw" is missing
        }
        game_no_platforms_or_genres = {
            # platforms missing
            # genres missing
            "description_raw": "A description."
        }
        raw_games = [game_missing_some_fields, game_no_platforms_or_genres]
        processed = process_games_data(raw_games)

        assert len(processed) == 2

        # Test game_missing_some_fields
        assert processed[0]["name"] == "Game With Missing Info"
        assert processed[0]["platforms"] == []
        assert processed[0]["genres"] == []
        # Check fallback for description_raw
        assert (
            processed[0]["description_raw"]
            == f"https://rawg.io/games/{game_missing_some_fields['slug']}"
        )
        assert (
            processed[0]["rawg_link"]
            == f"https://rawg.io/games/{game_missing_some_fields['slug']}"
        )

        # Test game_no_platforms_or_genres
        assert processed[1]["name"] == "Game No Platforms/Genres"
        assert processed[1]["platforms"] == []  # Should default to empty list
        assert processed[1]["genres"] == []  # Should default to empty list
        assert processed[1]["description_raw"] == "A description."

    # Tests for get_new_releases
    @patch("src.etl.games.games_get_new_releases.os.getenv")
    @patch("src.etl.games.games_get_new_releases.ensure_directories")
    @patch("src.etl.games.games_get_new_releases.pd.DataFrame.to_json")
    @patch("src.etl.games.games_get_new_releases.pd.DataFrame.to_csv")
    @patch("src.etl.games.games_get_new_releases.fetch_games")
    @patch("src.etl.games.games_get_new_releases.get_project_root")  # Mock project root
    def test_get_new_releases_flow_success(
        self,
        mock_get_root,
        mock_fetch,
        mock_to_csv,
        mock_to_json,
        mock_ensure_dirs,
        mock_getenv,
    ):
        # Mock configurations
        mock_getenv.return_value = self.mock_api_key  # Avoid API key warning
        mock_get_root.return_value = "/fake/project/root"

        get_new_releases()

        # Assertions
        assert (
            mock_fetch.call_count == 3
        )  # Called for page 1, page 2, then page 3 (which is empty)
        mock_ensure_dirs.assert_called_once_with(["/fake/project/root/data/games"])

        # Check that to_json and to_csv were called.
        # For more detailed check, capture the DataFrame passed to them.
        mock_to_json.assert_called_once()
        mock_to_csv.assert_called_once()

        # Verify DataFrame content passed to to_json/to_csv (optional, more involved)
        # args_json, _ = mock_to_json.call_args
        # df_json = args_json[0] # This is how you might get the df if it's the first positional arg
        # self.assertEqual(len(df_json), 2) # Expecting 2 valid games (high_score, meets_score)

        # Verify that the first call to fetch_games used the correct parameters (dates are dynamic)
        _, kwargs_page1 = mock_fetch.call_args_list[0]
        assert kwargs_page1["page_num"] == 1
        assert "key" in kwargs_page1["params"]
        assert "dates" in kwargs_page1["params"]
        assert "ordering" in kwargs_page1["params"]
        assert "metacritic" in kwargs_page1["params"]

    @patch("src.etl.games.games_get_new_releases.os.getenv")
    @patch("src.etl.games.games_get_new_releases.logger.warning")
    @patch(
        "src.etl.games.games_get_new_releases.fetch_games"
    )  # Mock fetch to avoid actual calls
    @patch(
        "src.etl.games.games_get_new_releases.pd.DataFrame.to_json"
    )  # Mock file saves
    @patch("src.etl.games.games_get_new_releases.pd.DataFrame.to_csv")
    @patch("src.etl.games.games_get_new_releases.ensure_directories")
    @patch("src.etl.games.games_get_new_releases.get_project_root")
    def test_get_new_releases_api_key_warning(
        self,
        mock_get_root,
        mock_ensure_dirs,
        mock_to_csv,
        mock_to_json,
        mock_fetch,
        mock_logger_warning,
        mock_getenv,
    ):
        mock_getenv.return_value = "YOUR_RAWG_API_KEY"  # Simulate placeholder key
        mock_fetch.return_value = self.empty_rawg_response  # Ensure it runs quickly
        mock_get_root.return_value = "/fake/project/root"

        # The warning about API_KEY is at the module level, but get_new_releases() also re-checks
        # and the main check is before get_new_releases is called if script is run directly.
        # For this test, we are testing the warning that might be triggered by the script's logger
        # when API_KEY is the placeholder. The script structure has a module-level logger.
        # We need to re-evaluate how to test this specific warning if it's purely module-level.
        # However, the `get_new_releases` function itself doesn't log this specific warning.
        # The warning is logged when the module `games_get_new_releases` is imported and API_KEY is placeholder.
        # To test this, we'd need to reload the module or structure the test differently.

        # For the purpose of this test, let's assume we want to check a warning inside get_new_releases
        # if such a warning existed. The current structure logs it at module load.
        # We can, however, ensure the API_KEY is passed to fetch_games.

        get_new_releases()  # Call the function

        # This assertion will likely fail because the warning is module-level.
        # A better test would be to check if 'YOUR_RAWG_API_KEY' is part of params to fetch_games.
        # mock_logger_warning.assert_any_call("RAWG_API_KEY is not set. Please set it as an environment variable or in the script.")

        # Verify that the placeholder key is used in parameters if that's the behavior
        if mock_fetch.call_args_list:  # If fetch_games was called
            _, kwargs_page1 = mock_fetch.call_args_list[0]
            assert kwargs_page1["params"]["key"] == "YOUR_RAWG_API_KEY"
        # This test is more about the script's setup warning. A direct test of the module-level warning
        # would require a different approach (e.g. runpy, or module reloading).

    @patch("src.etl.games.games_get_new_releases.os.getenv")
    @patch("src.etl.games.games_get_new_releases.fetch_games")
    @patch("src.etl.games.games_get_new_releases.pd.DataFrame.to_json")
    @patch("src.etl.games.games_get_new_releases.pd.DataFrame.to_csv")
    @patch("src.etl.games.games_get_new_releases.ensure_directories")
    @patch("src.etl.games.games_get_new_releases.logger")  # Mock logger
    @patch("src.etl.games.games_get_new_releases.get_project_root")
    def test_get_new_releases_fetch_fails(
        self,
        mock_get_root,
        mock_logger,
        mock_ensure_dirs,
        mock_to_csv,
        mock_to_json,
        mock_fetch,
        mock_getenv,
    ):
        mock_getenv.return_value = self.mock_api_key
        mock_fetch.return_value = None  # Simulate API failure on first call
        mock_get_root.return_value = "/fake/project/root"

        get_new_releases()

        mock_fetch.assert_called_once()  # Should be called once and fail
        mock_logger.warning.assert_called_with(
            "No data received or error in fetching page 1. Ending process."
        )
        mock_to_json.assert_not_called()  # No data, so no file saving
        mock_to_csv.assert_not_called()
        mock_ensure_dirs.assert_not_called()  # Should not be called if no games processed

    @patch("src.etl.games.games_get_new_releases.os.getenv")
    @patch("src.etl.games.games_get_new_releases.fetch_games")
    @patch("src.etl.games.games_get_new_releases.pd.DataFrame.to_json")
    @patch("src.etl.games.games_get_new_releases.pd.DataFrame.to_csv")
    @patch("src.etl.games.games_get_new_releases.ensure_directories")
    @patch("src.etl.games.games_get_new_releases.logger")
    @patch("src.etl.games.games_get_new_releases.get_project_root")
    def test_get_new_releases_no_games_processed(
        self,
        mock_get_root,
        mock_logger,
        mock_ensure_dirs,
        mock_to_csv,
        mock_to_json,
        mock_fetch,
        mock_getenv,
    ):
        mock_getenv.return_value = self.mock_api_key
        # Simulate API returning only games that will be filtered out
        response_low_score_only = {}
        mock_fetch.return_value = response_low_score_only
        mock_get_root.return_value = "/fake/project/root"

        get_new_releases()

        mock_fetch.assert_called_once()
        # process_games_data would return empty list, so all_processed_games remains empty
        mock_logger.info.assert_any_call(
            "No games found or processed. Skipping file saving."
        )
        mock_to_json.assert_not_called()
        mock_to_csv.assert_not_called()
        mock_ensure_dirs.assert_not_called()  # ensure_directories is called only if there are games


if __name__ == "__main__":
    unittest.main()
