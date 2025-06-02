# test_game_aggregator.py
import unittest
from unittest import mock

import game_aggregator # Module to test
# Mock the itchio_fetcher module that game_aggregator uses
# We don't want to make real network calls in these tests.

# Sample game data (matching structure from itchio_fetcher)
mock_game_free_1 = {'title': 'Free Game Alpha', 'is_free': True, 'price_value': 0.0, 'fetch_source': 'top_rated_rss'}
mock_game_free_2 = {'title': 'Free Game Beta', 'is_free': True, 'price_value': 0.0, 'fetch_source': 'top_rated_rss'}
mock_game_paid_1 = {'title': 'Paid Game Gamma', 'is_free': False, 'price_value': 9.99, 'fetch_source': 'top_rated_rss'}
mock_game_paid_2 = {'title': 'Paid Game Delta', 'is_free': False, 'price_value': 19.99, 'fetch_source': 'top_rated_rss'}

mock_featured_game_1 = {'title': 'Featured Zeta', 'is_free': False, 'price_value': 5.00, 'fetch_source': 'featured_rss'}
mock_featured_game_2 = {'title': 'Featured Eta', 'is_free': True, 'price_value': 0.00, 'fetch_source': 'featured_rss'}

mock_dedicated_free_game_1 = {'title': 'Purely Free Kappa', 'is_free': True, 'price_value': 0.0, 'fetch_source': 'free_rss'}

class TestGameAggregator(unittest.TestCase):

    @mock.patch('game_fetchers.itchio_fetcher.fetch_top_rated_games')
    def test_get_top_rated_prioritizing_free(self, mock_fetch_top_rated):
        # Test data: mix of free and paid, already somewhat ordered by "rating"
        mock_fetch_top_rated.return_value = [
            mock_game_paid_1,   # Higher rated paid
            mock_game_free_1,   # Higher rated free
            mock_game_paid_2,   # Lower rated paid
            mock_game_free_2    # Lower rated free
        ]

        result = game_aggregator.get_top_rated_games_prioritizing_free()

        self.assertEqual(len(result), 4)
        # Free games should come first, maintaining their relative order
        self.assertEqual(result[0]['title'], 'Free Game Alpha')
        self.assertEqual(result[1]['title'], 'Free Game Beta')
        # Paid games should come after, maintaining their relative order
        self.assertEqual(result[2]['title'], 'Paid Game Gamma')
        self.assertEqual(result[3]['title'], 'Paid Game Delta')

        mock_fetch_top_rated.assert_called_once()

    @mock.patch('game_fetchers.itchio_fetcher.fetch_top_rated_games')
    def test_get_top_rated_limit(self, mock_fetch_top_rated):
        mock_fetch_top_rated.return_value = [
            mock_game_free_1, mock_game_free_2, mock_game_paid_1, mock_game_paid_2
        ]
        result = game_aggregator.get_top_rated_games_prioritizing_free(limit=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['title'], 'Free Game Alpha')
        self.assertEqual(result[1]['title'], 'Free Game Beta')

    @mock.patch('game_fetchers.itchio_fetcher.fetch_top_rated_games')
    def test_get_top_rated_empty_fetch(self, mock_fetch_top_rated):
        mock_fetch_top_rated.return_value = []
        result = game_aggregator.get_top_rated_games_prioritizing_free()
        self.assertEqual(len(result), 0)

    @mock.patch('game_fetchers.itchio_fetcher.fetch_featured_games')
    def test_get_trending_games(self, mock_fetch_featured):
        mock_fetch_featured.return_value = [mock_featured_game_1, mock_featured_game_2]
        result = game_aggregator.get_trending_games()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['title'], 'Featured Zeta')
        mock_fetch_featured.assert_called_once()

    @mock.patch('game_fetchers.itchio_fetcher.fetch_featured_games')
    def test_get_trending_games_limit(self, mock_fetch_featured):
        mock_fetch_featured.return_value = [mock_featured_game_1, mock_featured_game_2]
        result = game_aggregator.get_trending_games(limit=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], 'Featured Zeta')

    @mock.patch('game_fetchers.itchio_fetcher.fetch_free_games')
    def test_get_dedicated_free_games_list(self, mock_fetch_free):
        mock_fetch_free.return_value = [mock_dedicated_free_game_1]
        result = game_aggregator.get_dedicated_free_games_list()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], 'Purely Free Kappa')
        mock_fetch_free.assert_called_once()

if __name__ == '__main__':
    unittest.main()
