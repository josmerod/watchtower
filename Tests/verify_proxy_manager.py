"""Verification script for Proxy Manager and Microsiervos ETL."""

import logging
import os
from unittest.mock import MagicMock, patch

from src.etl.news.microsiervos_etl import MicrosiervosETL
from src.etl.proxy_manager import ProxyManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY")


def test_proxy_manager_rotation():
    logger.info("--- Testing Proxy Manager Rotation ---")

    # Mock settings to return specific proxies
    mock_proxies = ["http://proxy1:8080", "http://proxy2:8080"]

    with patch("src.etl.proxy_manager.get_settings") as mock_get_settings:
        # Also patch direct property access if used
        mock_get_settings.return_value.scraping.proxies = mock_proxies

        pm = ProxyManager(proxies=mock_proxies)

        # Test 1: Get Proxy 1
        p1 = pm.get_proxy()
        logger.info(f"Proxy 1: {p1}")
        assert p1["http"] == mock_proxies[0]

        # Test 2: Get Proxy 2
        p2 = pm.get_proxy()
        logger.info(f"Proxy 2: {p2}")
        assert p2["http"] == mock_proxies[1]

        # Test 3: Rotation (Back to Proxy 1)
        p3 = pm.get_proxy()
        logger.info(f"Proxy 3: {p3}")
        assert p3["http"] == mock_proxies[0]

    logger.info("Proxy Manager Rotation: SUCCESS")


def test_microsiervos_integration():
    logger.info("--- Testing MicrosiervosETL Integration ---")

    etl = MicrosiervosETL()

    # Verify it has http_session property from BaseETL
    assert hasattr(etl, "http_session")

    # Verify session has proxies configured (even if empty list, should be a session)
    session = etl.http_session
    logger.info(f"Session headers: {session.headers}")
    assert "User-Agent" in session.headers

    # actually run it (integration test)
    # This assumes direct connection works (empty proxy list in default settings)
    logger.info("Running ETL extract...")
    items = etl.extract()
    logger.info(f"Extracted {len(items)} items")

    if len(items) > 0:
        logger.info(f"Sample item title: {items[0]['title']}")
        logger.info("MicrosiervosETL Integration: SUCCESS")
    else:
        logger.warning("MicrosiervosETL extracted 0 items (check network/feed)")


if __name__ == "__main__":
    test_proxy_manager_rotation()
    test_microsiervos_integration()
