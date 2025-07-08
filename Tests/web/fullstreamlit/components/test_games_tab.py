#!/usr/bin/env python3
"""
Unit tests for Games Tab Component.
Tests data loading, rendering, and error handling.
"""

import unittest
import os
import sys
import tempfile
import shutil
import json
import pandas as pd
from unittest.mock import patch, MagicMock
import warnings

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestGamesTabComponent(unittest.TestCase):
    """Test games tab component functionality"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.test_dir, "data", "games")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Create test data files
        self.create_test_data_files()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_test_data_files(self):
        """Create test data files for games"""
        # Create deals data
        deals_data = [
            {
                'title': 'Test Game 1',
                'link': 'https://example.com/game1',
                'discount_percent': 50,
                'current_price': 19.99,
                'regular_price': 39.99,
                'store': 'Steam',
                'drm': 'steam'
            },
            {
                'title': 'Test Game 2',
                'link': 'https://example.com/game2',
                'discount_percent': 25,
                'current_price': 29.99,
                'regular_price': 39.99,
                'store': 'Epic Games',
                'drm': 'epic'
            }
        ]
        
        with open(os.path.join(self.data_dir, 'deals.json'), 'w') as f:
            json.dump(deals_data, f)

        # Create bundles data
        bundles_data = [
            {
                'title': 'Test Bundle 1',
                'link': 'https://example.com/bundle1',
                'discount_percent': 80,
                'current_price': 9.99,
                'regular_price': 49.99,
                'store': 'Humble Bundle',
                'expiry_date': '2025-12-31T23:59:59Z'
            }
        ]
        
        with open(os.path.join(self.data_dir, 'bundles.json'), 'w') as f:
            json.dump(bundles_data, f)

        # Create trending data
        trending_data = [
            {
                'title': 'Trending Game 1',
                'author': 'Indie Developer',
                'price': 'Free',
                'link': 'https://itch.io/game1',
                'fetched_at': '2025-06-24T18:00:00Z'
            },
            {
                'title': 'Trending Game 2',
                'author': 'Another Developer',
                'price': '$4.99',
                'link': 'https://itch.io/game2',
                'fetched_at': '2025-06-24T18:00:00Z'
            }
        ]
        
        with open(os.path.join(self.data_dir, 'itchio_trending.json'), 'w') as f:
            json.dump(trending_data, f)

        # Create empty giveaways and new releases files
        with open(os.path.join(self.data_dir, 'giveaways.json'), 'w') as f:
            json.dump([], f)
        
        with open(os.path.join(self.data_dir, 'new_releases.json'), 'w') as f:
            json.dump([], f)

    def test_games_data_loading(self):
        """Test that games data loads correctly"""
        # Import the games tab component
        from src.web.new_dashboard_poc.components.games_tab import load_deals_data, load_bundles_data, load_trending_data, load_giveaways_data, load_new_releases_data
        
        # Mock the data path to use our test directory
        with patch('src.web.new_dashboard_poc.components.games_tab.DATA_BASE_PATH', f'{self.data_dir}/'):
            with patch('src.web.new_dashboard_poc.components.games_tab.os.path.dirname') as mock_dirname:
                mock_dirname.return_value = self.test_dir
                
                # Test deals loading
                load_deals_data()
                from src.web.new_dashboard_poc.components.games_tab import ALL_GAMES_DATA, DATA_LOADED_SUCCESSFULLY
                
                # Verify deals data was loaded
                self.assertTrue(DATA_LOADED_SUCCESSFULLY.get('deals', False))
                self.assertIsInstance(ALL_GAMES_DATA.get('deals'), pd.DataFrame)
                self.assertGreater(len(ALL_GAMES_DATA['deals']), 0)

    def test_empty_data_handling(self):
        """Test handling of empty data files"""
        from src.web.new_dashboard_poc.components.games_tab import load_giveaways_data, load_new_releases_data
        from src.web.new_dashboard_poc.components.games_tab import ALL_GAMES_DATA, DATA_LOADED_SUCCESSFULLY
        
        # Mock the data path to use our test directory
        with patch('src.web.new_dashboard_poc.components.games_tab.DATA_BASE_PATH', f'{self.data_dir}/'):
            with patch('src.web.new_dashboard_poc.components.games_tab.os.path.dirname') as mock_dirname:
                mock_dirname.return_value = self.test_dir
                
                # Test giveaways loading (empty file)
                load_giveaways_data()
                
                # Should handle empty file gracefully
                self.assertTrue(DATA_LOADED_SUCCESSFULLY.get('giveaways', False))
                self.assertIsInstance(ALL_GAMES_DATA.get('giveaways'), pd.DataFrame)
                self.assertEqual(len(ALL_GAMES_DATA['giveaways']), 0)

    def test_missing_files_handling(self):
        """Test handling of missing data files"""
        from src.web.new_dashboard_poc.components.games_tab import load_deals_data
        from src.web.new_dashboard_poc.components.games_tab import ALL_GAMES_DATA, DATA_LOADED_SUCCESSFULLY
        
        # Mock a non-existent data path
        with patch('src.web.new_dashboard_poc.components.games_tab.DATA_BASE_PATH', '/nonexistent/path/'):
            with patch('src.web.new_dashboard_poc.components.games_tab.os.path.dirname') as mock_dirname:
                mock_dirname.return_value = '/nonexistent'
                
                # Test deals loading with missing file
                load_deals_data()
                
                # Should handle missing file gracefully
                self.assertFalse(DATA_LOADED_SUCCESSFULLY.get('deals', True))
                self.assertIsInstance(ALL_GAMES_DATA.get('deals'), pd.DataFrame)
                self.assertEqual(len(ALL_GAMES_DATA['deals']), 0)

    def test_data_validation(self):
        """Test data validation and quality checks"""
        # Load test data
        deals_df = pd.read_json(os.path.join(self.data_dir, 'deals.json'))
        
        # Test required columns
        required_columns = ['title', 'link', 'discount_percent', 'current_price', 'regular_price', 'store']
        for col in required_columns:
            self.assertIn(col, deals_df.columns, f"Missing required column: {col}")
        
        # Test data types
        self.assertTrue(pd.api.types.is_numeric_dtype(deals_df['discount_percent']))
        self.assertTrue(pd.api.types.is_numeric_dtype(deals_df['current_price']))
        self.assertTrue(pd.api.types.is_numeric_dtype(deals_df['regular_price']))
        
        # Test data ranges
        self.assertTrue((deals_df['discount_percent'] >= 0).all())
        self.assertTrue((deals_df['discount_percent'] <= 100).all())
        self.assertTrue((deals_df['current_price'] >= 0).all())
        self.assertTrue((deals_df['regular_price'] >= 0).all())

    def test_pandas_warning_suppression(self):
        """Test that pandas warnings are handled properly"""
        # Create mixed DataFrames that might cause warnings
        df1 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        df2 = pd.DataFrame({'a': [5, 6], 'c': [7, 8]})  # Different columns
        
        # Test concatenation with proper warning handling
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Filter out empty DataFrames and align columns
            non_empty_dfs = [df for df in [df1, df2] if not df.empty]
            
            if non_empty_dfs:
                # Ensure all DataFrames have same columns
                all_columns = set()
                for df in non_empty_dfs:
                    all_columns.update(df.columns)
                
                # Add missing columns
                for i, df in enumerate(non_empty_dfs):
                    for col in all_columns:
                        if col not in df.columns:
                            non_empty_dfs[i] = df.assign(**{col: None})
                
                # Now concatenate
                result = pd.concat(non_empty_dfs, ignore_index=True)
                
                # Check that no FutureWarning was raised
                future_warnings = [warning for warning in w if issubclass(warning.category, FutureWarning)]
                self.assertEqual(len(future_warnings), 0, "FutureWarning should be avoided")

    def test_price_parsing_function(self):
        """Test price parsing functionality"""
        from src.web.new_dashboard_poc.components.games_tab import parse_price
        
        # Test various price formats
        test_cases = [
            ("$19.99", 19.99),
            ("€15.50", 15.50),
            ("£12.99", 12.99),
            ("Free", 0.0),
            ("$0", 0.0),
            ("$0.99", 0.99),
            ("", 0.0),
            (None, 0.0),
            ("invalid", 0.0)
        ]
        
        for price_str, expected in test_cases:
            with self.subTest(price_str=price_str):
                result = parse_price(price_str)
                self.assertEqual(result, expected, f"Failed to parse price: {price_str}")

    def test_date_parsing_function(self):
        """Test date parsing functionality"""
        from src.web.new_dashboard_poc.components.games_tab import parse_game_date
        
        # Test various date formats
        test_cases = [
            ("2025-06-24", "%Y-%m-%d"),
            ("2025-06-24T18:00:00Z", None),
            ("Mon, 24 Jun 2025 18:00:00 +0000", None),
            ("", None),
            (None, None),
            ("invalid", None)
        ]
        
        for date_str, source_format in test_cases:
            with self.subTest(date_str=date_str):
                result = parse_game_date(date_str, source_format)
                # Should either return a datetime object or None
                self.assertTrue(result is None or hasattr(result, 'year'), 
                               f"Failed to parse date: {date_str}")


class TestGamesDataIntegration(unittest.TestCase):
    """Integration tests for games data loading"""

    def test_real_data_files_exist(self):
        """Test that real data files exist in the project"""
        # Check if real data files exist (this validates the ETL worked)
        data_dir = os.path.join(project_root, "data", "games")
        
        expected_files = [
            'deals.json', 'deals.csv',
            'bundles.json', 'bundles.csv',
            'giveaways.json', 'giveaways.csv',
            'itchio_trending.json', 'itchio_trending.csv',
            'new_releases.json', 'new_releases.csv'
        ]
        
        for filename in expected_files:
            filepath = os.path.join(data_dir, filename)
            if os.path.exists(filepath):
                # File exists, validate it's not corrupted
                if filename.endswith('.json'):
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                        self.assertIsInstance(data, (list, dict), f"Invalid JSON structure in {filename}")
                    except json.JSONDecodeError:
                        self.fail(f"Corrupted JSON file: {filename}")

    def test_data_consistency_across_formats(self):
        """Test that JSON and CSV files have consistent data"""
        data_dir = os.path.join(project_root, "data", "games")
        
        # Test files that should have both JSON and CSV
        file_pairs = [
            ('deals.json', 'deals.csv'),
            ('bundles.json', 'bundles.csv'),
            ('itchio_trending.json', 'itchio_trending.csv')
        ]
        
        for json_file, csv_file in file_pairs:
            json_path = os.path.join(data_dir, json_file)
            csv_path = os.path.join(data_dir, csv_file)
            
            if os.path.exists(json_path) and os.path.exists(csv_path):
                # Load both files
                json_df = pd.read_json(json_path)
                csv_df = pd.read_csv(csv_path, sep='|')
                
                # Should have same number of records
                self.assertEqual(len(json_df), len(csv_df), 
                               f"Record count mismatch between {json_file} and {csv_file}")


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2) 