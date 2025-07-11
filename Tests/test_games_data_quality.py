#!/usr/bin/env python3
"""
Simple Games Data Quality Tests.
Focuses on real data validation without complex mocking.
"""

import unittest
import os
import sys
import json
import pandas as pd
from datetime import datetime

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestGamesDataQuality(unittest.TestCase):
    """Test real games data quality and structure"""

    @classmethod
    def setUpClass(cls):
        """Set up test class with data directory"""
        cls.data_dir = os.path.join(project_root, "data", "games")

    def test_data_directory_exists(self):
        """Test that games data directory exists"""
        self.assertTrue(os.path.exists(self.data_dir), "Games data directory should exist")

    def test_json_files_structure(self):
        """Test that JSON files have proper structure"""
        json_files = ['deals.json', 'bundles.json', 'giveaways.json', 'itchio_trending.json', 'new_releases.json']
        
        for filename in json_files:
            filepath = os.path.join(self.data_dir, filename)
            
            if os.path.exists(filepath):
                with self.subTest(file=filename):
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                        
                        # Should be a list
                        self.assertIsInstance(data, list, f"{filename} should contain a list")
                        
                        # If not empty, check first item structure
                        if data:
                            first_item = data[0]
                            self.assertIsInstance(first_item, dict, f"Items in {filename} should be dictionaries")
                            self.assertIn('title', first_item, f"Items in {filename} should have 'title' field")
                            
                    except json.JSONDecodeError:
                        self.fail(f"Invalid JSON in {filename}")

    def test_price_parsing_functionality(self):
        """Test price parsing utility function"""
        try:
            from src.web.new_dashboard_poc.components.games_tab import parse_price
            
            # Test cases
            test_cases = [
                ("$19.99", 19.99),
                ("€15.50", 15.50),
                ("Free", 0.0),
                ("$0", 0.0),
                ("", 0.0),
                (None, 0.0),
                ("invalid", 0.0)
            ]
            
            for price_str, expected in test_cases:
                with self.subTest(price=price_str):
                    result = parse_price(price_str)
                    self.assertEqual(result, expected, f"Failed to parse price: {price_str}")
                    
        except ImportError:
            self.skipTest("Could not import parse_price function")

    def test_deals_data_quality(self):
        """Test deals data quality if file exists"""
        deals_file = os.path.join(self.data_dir, "deals.json")
        
        if not os.path.exists(deals_file):
            self.skipTest("Deals file does not exist")
            
        with open(deals_file, 'r') as f:
            deals_data = json.load(f)
        
        if not deals_data:
            self.skipTest("Deals file is empty")
            
        # Test first deal structure
        first_deal = deals_data[0]
        
        # Should have basic fields
        expected_fields = ['title', 'link']
        for field in expected_fields:
            self.assertIn(field, first_deal, f"Deal should have {field} field")
        
        # Title should not be empty
        self.assertTrue(first_deal['title'], "Deal title should not be empty")
        
        # Link should be a valid URL format
        self.assertTrue(first_deal['link'].startswith('http'), "Deal link should be a URL")

    def test_games_tab_component_exists(self):
        """Test that games tab component exists and can be imported"""
        try:
            from src.web.new_dashboard_poc.components.games_tab import parse_price, parse_game_date
            # Basic functionality test
            self.assertEqual(parse_price("$10"), 10.0)
            self.assertEqual(parse_price("Free"), 0.0)
        except ImportError as e:
            self.fail(f"Could not import games tab component: {e}")


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2) 