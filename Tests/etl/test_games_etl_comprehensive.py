#!/usr/bin/env python3
"""
Comprehensive unit tests for Games ETL scripts.
Tests data quality, ETL functionality, and error handling.
"""

import unittest
import os
import sys
import tempfile
import shutil
import json
import pandas as pd
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timezone, timedelta
import feedparser

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.etl.games.games_get_deals import get_deals, get_bundles, get_giveaways
from src.etl.games.games_get_itchio_trending import get_itchio_trending
from src.etl.games.games_get_new_releases import get_new_releases
from src.utils.logging import get_logger


class TestGamesETLComprehensive(unittest.TestCase):
    """Comprehensive tests for Games ETL functionality"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.test_dir, "data", "games")
        os.makedirs(self.data_dir, exist_ok=True)

        # Mock the project root to use our test directory
        self.project_root_patcher = patch("src.utils.file_system.get_project_root")
        self.mock_project_root = self.project_root_patcher.start()
        self.mock_project_root.return_value = self.test_dir

    def tearDown(self):
        """Clean up test environment"""
        self.project_root_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_deals_etl_data_quality(self):
        """Test deals ETL produces quality data"""
        # Mock successful API response
        mock_response = {
            "data": {
                "list": [
                    {
                        "title": "Test Game 1",
                        "urls": {"buy": "https://example.com/game1"},
                        "price": {"cut": 50, "price": 19.99, "regular": 39.99},
                        "shop": {"name": "Test Store"},
                        "drm": ["steam"],
                    }
                ]
            }
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.status_code = 200

            # Run the ETL
            get_deals()

            # Check files were created
            deals_json = os.path.join(self.data_dir, "deals.json")
            deals_csv = os.path.join(self.data_dir, "deals.csv")

            self.assertTrue(os.path.exists(deals_json))
            self.assertTrue(os.path.exists(deals_csv))

            # Validate JSON data quality
            with open(deals_json, "r") as f:
                data = json.load(f)

            self.assertEqual(len(data), 1)

            # Check required fields exist
            deal = data[0]
            required_fields = [
                "title",
                "link",
                "discount_percent",
                "current_price",
                "regular_price",
                "store",
                "drm",
            ]
            for field in required_fields:
                self.assertIn(field, deal, f"Missing field: {field}")

    def test_deals_etl_handles_empty_response(self):
        """Test deals ETL handles empty API response gracefully"""
        mock_response = {"data": {"list": []}}

        with patch("requests.get") as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.status_code = 200

            # Run the ETL
            get_deals()

            # Check empty files were created
            deals_json = os.path.join(self.data_dir, "deals.json")
            self.assertTrue(os.path.exists(deals_json))

            with open(deals_json, "r") as f:
                data = json.load(f)

            self.assertEqual(len(data), 0)

    def test_bundles_etl_data_quality(self):
        """Test bundles ETL produces quality data"""
        mock_response = {
            "data": {
                "list": [
                    {
                        "title": "Test Bundle 1",
                        "urls": {"buy": "https://example.com/bundle1"},
                        "price": {"cut": 75, "price": 9.99, "regular": 39.99},
                        "shop": {"name": "Bundle Store"},
                        "expiry": int((datetime.now() + timedelta(days=7)).timestamp()),
                    }
                ]
            }
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.status_code = 200

            # Run the ETL
            get_bundles()

            # Check files were created
            bundles_json = os.path.join(self.data_dir, "bundles.json")
            self.assertTrue(os.path.exists(bundles_json))

            # Validate data quality
            with open(bundles_json, "r") as f:
                data = json.load(f)

            self.assertEqual(len(data), 1)
            bundle = data[0]

            # Check required fields
            required_fields = [
                "title",
                "link",
                "discount_percent",
                "current_price",
                "regular_price",
                "store",
            ]
            for field in required_fields:
                self.assertIn(field, bundle, f"Missing field: {field}")

    def test_giveaways_etl_handles_malformed_rss(self):
        """Test giveaways ETL handles malformed RSS gracefully"""
        # Mock malformed RSS feed
        mock_feed = MagicMock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Invalid token")
        mock_feed.entries = []

        with patch("feedparser.parse") as mock_parse:
            mock_parse.return_value = mock_feed

            # Run the ETL
            get_giveaways()

            # Check empty files were created
            giveaways_json = os.path.join(self.data_dir, "giveaways.json")
            giveaways_csv = os.path.join(self.data_dir, "giveaways.csv")

            self.assertTrue(os.path.exists(giveaways_json))
            self.assertTrue(os.path.exists(giveaways_csv))

            # Validate empty structure
            with open(giveaways_json, "r") as f:
                data = json.load(f)

            self.assertEqual(data, [])

            # Check CSV has header
            with open(giveaways_csv, "r") as f:
                content = f.read()

            self.assertIn("title|link|published|expires", content)

    def test_giveaways_etl_with_valid_data(self):
        """Test giveaways ETL with valid RSS data"""
        # Create mock RSS entry
        mock_entry = MagicMock()
        mock_entry.title = "Free Game Giveaway"
        mock_entry.link = "https://example.com/giveaway"
        mock_entry.published = "Mon, 24 Jun 2025 12:00:00 +0000"
        mock_entry.description = "Free game expires on Wed, 01 Jul 2025 23:59:59 +0000"
        mock_entry.get.return_value = "Mon, 24 Jun 2025 12:00:00 +0000"

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [mock_entry]

        with patch("feedparser.parse") as mock_parse:
            mock_parse.return_value = mock_feed

            # Run the ETL
            get_giveaways()

            # Check files were created with data
            giveaways_json = os.path.join(self.data_dir, "giveaways.json")
            self.assertTrue(os.path.exists(giveaways_json))

            # Validate data structure
            with open(giveaways_json, "r") as f:
                data = json.load(f)

            self.assertEqual(len(data), 1)
            giveaway = data[0]

            required_fields = ["title", "link", "published", "expires"]
            for field in required_fields:
                self.assertIn(field, giveaway, f"Missing field: {field}")

    def test_itchio_trending_etl_data_quality(self):
        """Test itch.io trending ETL produces quality data"""
        # Mock HTML response
        mock_html = """
        <div class="game_cell">
            <a href="/game1" class="title">Test Game 1</a>
            <div class="game_author">by <a href="/user1">Test Developer</a></div>
            <div class="price_value">$5.99</div>
        </div>
        <div class="game_cell">
            <a href="/game2" class="title">Free Game</a>
            <div class="game_author">by <a href="/user2">Free Developer</a></div>
            <div class="price_value">Free</div>
        </div>
        """

        with patch("requests.get") as mock_get:
            mock_get.return_value.text = mock_html
            mock_get.return_value.status_code = 200

            # Run the ETL
            get_itchio_trending()

            # Check files were created
            trending_json = os.path.join(self.data_dir, "itchio_trending.json")
            trending_csv = os.path.join(self.data_dir, "itchio_trending.csv")

            self.assertTrue(os.path.exists(trending_json))
            self.assertTrue(os.path.exists(trending_csv))

            # Validate data structure
            with open(trending_json, "r") as f:
                data = json.load(f)

            self.assertGreater(len(data), 0)

            # Check required fields
            for game in data:
                required_fields = ["title", "author", "price", "link", "fetched_at"]
                for field in required_fields:
                    self.assertIn(field, game, f"Missing field: {field}")

    def test_itchio_trending_handles_scraping_failure(self):
        """Test itch.io trending ETL handles scraping failure"""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection error")

            # Run the ETL
            get_itchio_trending()

            # Check empty files were created
            trending_json = os.path.join(self.data_dir, "itchio_trending.json")
            self.assertTrue(os.path.exists(trending_json))

            with open(trending_json, "r") as f:
                data = json.load(f)

            self.assertEqual(data, [])

    def test_new_releases_etl_without_api_key(self):
        """Test new releases ETL creates empty files without API key"""
        # Run the ETL (will use default "YOUR_RAWG_API_KEY")
        get_new_releases()

        # Check empty files were created
        releases_json = os.path.join(self.data_dir, "new_releases.json")
        releases_csv = os.path.join(self.data_dir, "new_releases.csv")

        self.assertTrue(os.path.exists(releases_json))
        self.assertTrue(os.path.exists(releases_csv))

        # Validate empty structure
        with open(releases_json, "r") as f:
            data = json.load(f)

        self.assertEqual(data, [])

        # Check CSV has header
        with open(releases_csv, "r") as f:
            content = f.read()

        self.assertIn(
            "id|name|released|platforms|genres|metacritic|description_raw|rawg_link",
            content,
        )

    def test_new_releases_etl_with_api_key(self):
        """Test new releases ETL with valid API key"""
        mock_response = {
            "results": [
                {
                    "id": 1,
                    "name": "New Game 2025",
                    "released": "2025-07-15",
                    "platforms": [{"platform": {"name": "PC"}}],
                    "genres": [{"name": "Action"}, {"name": "Adventure"}],
                    "metacritic": 85,
                    "description_raw": "An exciting new game",
                    "slug": "new-game-2025",
                }
            ],
            "next": None,
        }

        with patch("src.etl.games.games_get_new_releases.API_KEY", "test_api_key"):
            with patch("requests.get") as mock_get:
                mock_get.return_value.json.return_value = mock_response
                mock_get.return_value.status_code = 200

                # Run the ETL
                get_new_releases()

                # Check files were created with data
                releases_json = os.path.join(self.data_dir, "new_releases.json")
                self.assertTrue(os.path.exists(releases_json))

                # Validate data structure
                with open(releases_json, "r") as f:
                    data = json.load(f)

                self.assertEqual(len(data), 1)
                game = data[0]

                required_fields = [
                    "id",
                    "name",
                    "released",
                    "platforms",
                    "genres",
                    "metacritic",
                    "description_raw",
                    "rawg_link",
                ]
                for field in required_fields:
                    self.assertIn(field, game, f"Missing field: {field}")


class TestGamesDataQuality(unittest.TestCase):
    """Test data quality validation for games data"""

    def setUp(self):
        """Set up test data files"""
        self.test_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.test_dir, "data", "games")
        os.makedirs(self.data_dir, exist_ok=True)

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_test_deals_file(self, deals_data):
        """Create test deals JSON file"""
        deals_file = os.path.join(self.data_dir, "deals.json")
        with open(deals_file, "w") as f:
            json.dump(deals_data, f)
        return deals_file

    def test_deals_data_schema_validation(self):
        """Validate deals data follows expected schema"""
        test_deals = [
            {
                "title": "Test Game",
                "link": "https://example.com",
                "discount_percent": 50,
                "current_price": 19.99,
                "regular_price": 39.99,
                "store": "Test Store",
                "drm": "steam",
            }
        ]

        deals_file = self.create_test_deals_file(test_deals)

        # Load and validate
        df = pd.read_json(deals_file)

        # Schema validation
        required_columns = [
            "title",
            "link",
            "discount_percent",
            "current_price",
            "regular_price",
            "store",
            "drm",
        ]
        for col in required_columns:
            self.assertIn(col, df.columns, f"Missing required column: {col}")

        # Data type validation
        self.assertTrue(pd.api.types.is_numeric_dtype(df["discount_percent"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(df["current_price"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(df["regular_price"]))

        # Business logic validation
        self.assertTrue((df["discount_percent"] >= 0).all())
        self.assertTrue((df["discount_percent"] <= 100).all())
        self.assertTrue((df["current_price"] >= 0).all())
        self.assertTrue((df["regular_price"] >= 0).all())

    def test_deals_data_consistency(self):
        """Test consistency between discount percent and prices"""
        test_deals = [
            {
                "title": "Test Game",
                "link": "https://example.com",
                "discount_percent": 50,
                "current_price": 20.0,
                "regular_price": 40.0,
                "store": "Test Store",
                "drm": "steam",
            }
        ]

        deals_file = self.create_test_deals_file(test_deals)
        df = pd.read_json(deals_file)

        # Validate discount calculation consistency
        for _, row in df.iterrows():
            if row["regular_price"] > 0:
                expected_discount = round(
                    (1 - row["current_price"] / row["regular_price"]) * 100
                )
                actual_discount = row["discount_percent"]
                self.assertAlmostEqual(
                    expected_discount,
                    actual_discount,
                    delta=5,
                    msg=f"Discount calculation inconsistent for {row['title']}",
                )

    def test_empty_files_structure(self):
        """Test that empty files maintain proper structure"""
        # Test empty JSON files
        empty_files = [
            "deals.json",
            "bundles.json",
            "giveaways.json",
            "itchio_trending.json",
            "new_releases.json",
        ]

        for filename in empty_files:
            filepath = os.path.join(self.data_dir, filename)
            with open(filepath, "w") as f:
                json.dump([], f)

            # Validate empty structure
            with open(filepath, "r") as f:
                data = json.load(f)

            self.assertIsInstance(data, list, f"{filename} should contain a list")
            self.assertEqual(len(data), 0, f"{filename} should be empty")


class TestGamesETLIntegration(unittest.TestCase):
    """Integration tests for Games ETL pipeline"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.test_dir, "data", "games")
        os.makedirs(self.data_dir, exist_ok=True)

        # Mock the project root
        self.project_root_patcher = patch("src.utils.file_system.get_project_root")
        self.mock_project_root = self.project_root_patcher.start()
        self.mock_project_root.return_value = self.test_dir

    def tearDown(self):
        """Clean up test environment"""
        self.project_root_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_full_games_etl_pipeline(self):
        """Test the complete games ETL pipeline"""
        # Mock all external dependencies
        with patch("requests.get") as mock_get, patch("feedparser.parse") as mock_parse:

            # Mock deals response
            mock_get.return_value.json.return_value = {
                "data": {
                    "list": [
                        {
                            "title": "Pipeline Test Game",
                            "urls": {"buy": "https://example.com/game"},
                            "price": {"cut": 30, "price": 14.99, "regular": 19.99},
                            "shop": {"name": "Test Store"},
                            "drm": ["steam"],
                        }
                    ]
                }
            }
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = '<div class="game_cell"><a href="/game" class="title">Test Game</a></div>'

            # Mock giveaways RSS
            mock_feed = MagicMock()
            mock_feed.bozo = False
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            # Run all ETL functions
            get_deals()
            get_bundles()
            get_giveaways()
            get_itchio_trending()
            get_new_releases()

            # Verify all files were created
            expected_files = [
                "deals.json",
                "deals.csv",
                "bundles.json",
                "bundles.csv",
                "giveaways.json",
                "giveaways.csv",
                "itchio_trending.json",
                "itchio_trending.csv",
                "new_releases.json",
                "new_releases.csv",
            ]

            for filename in expected_files:
                filepath = os.path.join(self.data_dir, filename)
                self.assertTrue(
                    os.path.exists(filepath), f"File not created: {filename}"
                )

                # Verify files are not empty (size > 0)
                self.assertGreater(
                    os.path.getsize(filepath), 0, f"File is empty: {filename}"
                )

    def test_concurrent_etl_execution(self):
        """Test ETL scripts can run concurrently without conflicts"""
        import threading

        results = {}
        errors = {}

        def run_etl_function(name, func):
            try:
                func()
                results[name] = True
            except Exception as e:
                errors[name] = str(e)

        # Mock external dependencies
        with patch("requests.get") as mock_get, patch("feedparser.parse") as mock_parse:

            mock_get.return_value.json.return_value = {"data": {"list": []}}
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = "<html></html>"

            mock_feed = MagicMock()
            mock_feed.bozo = False
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            # Create threads for each ETL function
            threads = [
                threading.Thread(target=run_etl_function, args=("deals", get_deals)),
                threading.Thread(
                    target=run_etl_function, args=("bundles", get_bundles)
                ),
                threading.Thread(
                    target=run_etl_function, args=("giveaways", get_giveaways)
                ),
                threading.Thread(
                    target=run_etl_function, args=("trending", get_itchio_trending)
                ),
                threading.Thread(
                    target=run_etl_function, args=("releases", get_new_releases)
                ),
            ]

            # Start all threads
            for thread in threads:
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Verify no errors occurred
            self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
            self.assertEqual(len(results), 5, "Not all ETL functions completed")


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
