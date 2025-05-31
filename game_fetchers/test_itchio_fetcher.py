# game_fetchers/test_itchio_fetcher.py
import unittest
from unittest import mock
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

# Assuming itchio_fetcher is in the same directory or PYTHONPATH is set up
from game_fetchers import itchio_fetcher # Relative import if run as module, or direct if path is set

# Sample XML data for a single item
SAMPLE_RSS_ITEM_FREE_GAME = """
<item>
    <title>Awesome Free Game</title>
    <link>https://example.com/awesome-free-game</link>
    <description><![CDATA[<p>This is a <b>great game</b> and it's $0.00USD!</p><img src="https://example.com/image.png"/>]]></description>
    <pubDate>Fri, 07 Jun 2019 23:47:57 GMT</pubDate>
</item>
"""

SAMPLE_RSS_ITEM_PAID_GAME = """
<item>
    <title>Amazing Paid Game $9.99</title>
    <link>https://example.com/amazing-paid-game</link>
    <description><![CDATA[<p>So much value for only $9.99 USD.</p><img src="https://example.com/paid_image.jpg"/>]]></description>
    <pubDate>Sat, 08 Jun 2019 10:00:00 GMT</pubDate>
</item>
"""

SAMPLE_RSS_ITEM_NO_PRICE_INFO = """
<item>
    <title>Mysterious Game</title>
    <link>https://example.com/mysterious-game</link>
    <description><![CDATA[<p>No price mentioned here.</p>]]></description>
    <pubDate>Sun, 09 Jun 2019 12:00:00 GMT</pubDate>
</item>
"""

EMPTY_RSS_FEED = """<rss><channel></channel></rss>"""

MALFORMED_RSS_FEED = """<rss><channel><item>No title</item></channel></rss>"""

class TestItchioFetcher(unittest.TestCase):

    def _build_rss_xml(self, item_xml_list):
        items_str = "".join(item_xml_list)
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>itch.io RSS</title>
    <link>https://itch.io</link>
    <description>Games from itch.io</description>
    {items_str}
  </channel>
</rss>"""

    @mock.patch('urllib.request.urlopen')
    def test_parse_single_free_game(self, mock_urlopen):
        xml_data = self._build_rss_xml([SAMPLE_RSS_ITEM_FREE_GAME]).encode('utf-8')
        mock_response = mock.MagicMock()
        mock_response.read.return_value = xml_data
        mock_response.__enter__.return_value = mock_response # For context manager
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        games = itchio_fetcher.parse_itchio_rss_feed("http://fake.url/rss", "test_source")

        self.assertEqual(len(games), 1)
        game = games[0]
        self.assertEqual(game['title'], "Awesome Free Game")
        self.assertEqual(game['url'], "https://example.com/awesome-free-game")
        self.assertIn("$0.00USD", game['description_short'])
        self.assertTrue(game['is_free'])
        self.assertEqual(game['price_value'], 0.0)
        self.assertEqual(game['cover_image_url'], "https://example.com/image.png")
        self.assertEqual(game['published_date'], datetime(2019, 6, 7, 23, 47, 57))
        self.assertEqual(game['fetch_source'], "test_source")

    @mock.patch('urllib.request.urlopen')
    def test_parse_single_paid_game(self, mock_urlopen):
        xml_data = self._build_rss_xml([SAMPLE_RSS_ITEM_PAID_GAME]).encode('utf-8')
        mock_response = mock.MagicMock()
        mock_response.read.return_value = xml_data
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        games = itchio_fetcher.parse_itchio_rss_feed("http://fake.url/rss", "test_source_paid")

        self.assertEqual(len(games), 1)
        game = games[0]
        self.assertEqual(game['title'], "Amazing Paid Game $9.99")
        self.assertFalse(game['is_free'])
        self.assertEqual(game['price_value'], 9.99)
        self.assertEqual(game['cover_image_url'], "https://example.com/paid_image.jpg")
        self.assertEqual(game['fetch_source'], "test_source_paid")

    @mock.patch('urllib.request.urlopen')
    def test_parse_game_no_price_info(self, mock_urlopen):
        # This tests the fallback where if no price is clear, it's assumed free
        xml_data = self._build_rss_xml([SAMPLE_RSS_ITEM_NO_PRICE_INFO]).encode('utf-8')
        mock_response = mock.MagicMock()
        mock_response.read.return_value = xml_data
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        games = itchio_fetcher.parse_itchio_rss_feed("http://fake.url/rss", "test_source_no_price")

        self.assertEqual(len(games), 1)
        game = games[0]
        self.assertEqual(game['title'], "Mysterious Game")
        self.assertTrue(game['is_free'], "Game should default to free if no price info found by heuristic")
        self.assertEqual(game['price_value'], 0.0)
        self.assertIsNone(game['cover_image_url']) # No img tag in this sample

    @mock.patch('urllib.request.urlopen')
    def test_parse_multiple_items(self, mock_urlopen):
        xml_data = self._build_rss_xml([SAMPLE_RSS_ITEM_FREE_GAME, SAMPLE_RSS_ITEM_PAID_GAME]).encode('utf-8')
        mock_response = mock.MagicMock()
        mock_response.read.return_value = xml_data
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        games = itchio_fetcher.parse_itchio_rss_feed("http://fake.url/rss", "test_source_multi")
        self.assertEqual(len(games), 2)

    @mock.patch('urllib.request.urlopen')
    def test_empty_feed(self, mock_urlopen):
        xml_data = EMPTY_RSS_FEED.encode('utf-8')
        mock_response = mock.MagicMock()
        mock_response.read.return_value = xml_data
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        games = itchio_fetcher.parse_itchio_rss_feed("http://fake.url/empty", "test_empty")
        self.assertEqual(len(games), 0)

    @mock.patch('urllib.request.urlopen')
    def test_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Network down")
        games = itchio_fetcher.parse_itchio_rss_feed("http://fake.url/network_error", "test_network_error")
        self.assertEqual(len(games), 0)
        # Add assertion for logging if implemented, for now, just check empty list

    @mock.patch('urllib.request.urlopen')
    def test_xml_parse_error(self, mock_urlopen):
        mock_response = mock.MagicMock()
        mock_response.read.return_value = b"<rss><channel><item>unterminated" # Malformed XML
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        games = itchio_fetcher.parse_itchio_rss_feed("http://fake.url/parse_error", "test_parse_error")
        self.assertEqual(len(games), 0)

    # Test helper functions briefly
    @mock.patch('game_fetchers.itchio_fetcher.parse_itchio_rss_feed')
    def test_fetch_top_rated_games_calls_parser(self, mock_parse):
        itchio_fetcher.fetch_top_rated_games()
        mock_parse.assert_called_once_with(itchio_fetcher.RSS_FEEDS['top_rated'], "top_rated_rss")

    @mock.patch('game_fetchers.itchio_fetcher.parse_itchio_rss_feed')
    def test_fetch_featured_games_calls_parser(self, mock_parse):
        itchio_fetcher.fetch_featured_games()
        mock_parse.assert_called_once_with(itchio_fetcher.RSS_FEEDS['featured'], "featured_rss")

    @mock.patch('game_fetchers.itchio_fetcher.parse_itchio_rss_feed')
    def test_fetch_free_games_calls_parser(self, mock_parse):
        itchio_fetcher.fetch_free_games()
        mock_parse.assert_called_once_with(itchio_fetcher.RSS_FEEDS['free'], "free_rss")

if __name__ == '__main__':
    unittest.main()
