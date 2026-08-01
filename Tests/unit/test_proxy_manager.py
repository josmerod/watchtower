"""Unit tests for ProxyManager session caching and cleanup.

Tests that sessions are cached per (retries, backoff_factor) key, that
close() releases all connections, and that the context manager works.
"""

from unittest.mock import patch

import pytest
import requests

from src.etl.proxy_manager import ProxyManager


@pytest.fixture
def mock_settings():
    """Patch get_settings so ProxyManager doesn't require real config."""
    with patch("src.etl.proxy_manager.get_settings") as mock:
        mock.return_value.scraping.proxies = []
        yield mock


@pytest.fixture
def pm_no_proxies(mock_settings):
    """A ProxyManager with no proxies (direct connection)."""
    return ProxyManager(proxies=[])


@pytest.fixture
def pm_with_proxies(mock_settings):
    """A ProxyManager with mock proxies."""
    return ProxyManager(proxies=["http://proxy1:8080", "http://proxy2:8080"])


class TestSessionCaching:
    """Tests for session caching behavior."""

    def test_same_args_returns_same_session(self, pm_no_proxies):
        """get_session() with identical args must return the same Session object."""
        s1 = pm_no_proxies.get_session(retries=3, backoff_factor=2.0)
        s2 = pm_no_proxies.get_session(retries=3, backoff_factor=2.0)
        assert s1 is s2, "Same args should return cached session"

    def test_different_retries_returns_different_session(self, pm_no_proxies):
        """Different retry counts should produce distinct sessions."""
        s1 = pm_no_proxies.get_session(retries=3, backoff_factor=2.0)
        s2 = pm_no_proxies.get_session(retries=5, backoff_factor=2.0)
        assert s1 is not s2, "Different retries should create new session"

    def test_different_backoff_returns_different_session(self, pm_no_proxies):
        """Different backoff factors should produce distinct sessions."""
        s1 = pm_no_proxies.get_session(retries=3, backoff_factor=1.0)
        s2 = pm_no_proxies.get_session(retries=3, backoff_factor=3.0)
        assert s1 is not s2, "Different backoff should create new session"

    def test_default_args_cached(self, pm_no_proxies):
        """Default args (retries=3, backoff=2.0) should be cached."""
        s1 = pm_no_proxies.get_session()
        s2 = pm_no_proxies.get_session()
        assert s1 is s2

    def test_cached_session_count(self, pm_no_proxies):
        """cached_session_count tracks number of cached sessions."""
        assert pm_no_proxies.cached_session_count == 0
        pm_no_proxies.get_session(retries=3, backoff_factor=2.0)
        assert pm_no_proxies.cached_session_count == 1
        pm_no_proxies.get_session(retries=5, backoff_factor=2.0)
        assert pm_no_proxies.cached_session_count == 2
        # Same key, should not increase
        pm_no_proxies.get_session(retries=3, backoff_factor=2.0)
        assert pm_no_proxies.cached_session_count == 2

    def test_session_has_user_agent(self, pm_no_proxies):
        """Sessions must include the default User-Agent header."""
        session = pm_no_proxies.get_session()
        assert "User-Agent" in session.headers
        assert "Chrome" in session.headers["User-Agent"]

    def test_session_has_retries_configured(self, pm_no_proxies):
        """Sessions must have retry adapters mounted."""
        session = pm_no_proxies.get_session(retries=5, backoff_factor=2.0)
        adapter = session.get_adapter("https://example.com")
        assert adapter.max_retries.total == 5


class TestProxyRotation:
    """Tests for proxy round-robin rotation."""

    def test_rotation_cycles_through_proxies(self, pm_with_proxies):
        """get_proxy() should cycle through all proxies in round-robin."""
        p1 = pm_with_proxies.get_proxy()
        p2 = pm_with_proxies.get_proxy()
        p3 = pm_with_proxies.get_proxy()  # wraps around

        assert p1["http"] == "http://proxy1:8080"
        assert p2["http"] == "http://proxy2:8080"
        assert p3["http"] == "http://proxy1:8080"

    def test_no_proxies_returns_none(self, pm_no_proxies):
        """get_proxy() returns None when no proxies configured."""
        assert pm_no_proxies.get_proxy() is None

    def test_session_gets_proxy_assigned(self, pm_with_proxies):
        """A new session should have proxy configured."""
        session = pm_with_proxies.get_session()
        # The session should have proxies set
        assert session.proxies.get("http") or session.proxies.get("https")


class TestCloseCleanup:
    """Tests for close() and context manager."""

    def test_close_clears_cache(self, pm_no_proxies):
        """close() should empty the session cache."""
        pm_no_proxies.get_session(retries=3, backoff_factor=2.0)
        assert pm_no_proxies.cached_session_count == 1
        pm_no_proxies.close()
        assert pm_no_proxies.cached_session_count == 0

    def test_close_is_idempotent(self, pm_no_proxies):
        """close() can be called multiple times without error."""
        pm_no_proxies.get_session()
        pm_no_proxies.close()
        pm_no_proxies.close()  # should not raise
        assert pm_no_proxies.cached_session_count == 0

    def test_close_on_empty_cache(self, pm_no_proxies):
        """close() on an empty cache is a no-op."""
        pm_no_proxies.close()
        assert pm_no_proxies.cached_session_count == 0

    def test_close_actually_closes_session(self, pm_no_proxies):
        """close() must call .close() on the underlying requests.Session."""
        session = pm_no_proxies.get_session()
        closed_called = []
        original_close = session.close

        def spy_close():
            closed_called.append(True)
            original_close()

        session.close = spy_close
        pm_no_proxies.close()
        assert closed_called, "session.close() was not called"

    def test_new_session_after_close(self, pm_no_proxies):
        """After close(), get_session() creates a fresh session."""
        s1 = pm_no_proxies.get_session()
        pm_no_proxies.close()
        s2 = pm_no_proxies.get_session()
        assert s1 is not s2, "After close, a new session should be created"

    def test_context_manager_closes_on_exit(self, mock_settings):
        """Using 'with ProxyManager()' should close sessions on exit."""
        with ProxyManager(proxies=[]) as pm:
            pm.get_session()
            assert pm.cached_session_count == 1
        assert pm.cached_session_count == 0

    def test_context_manager_closes_on_exception(self, mock_settings):
        """Sessions are closed even if an exception occurs inside the with block."""
        pm_ref = None
        with pytest.raises(ValueError), ProxyManager(proxies=[]) as pm:
            pm_ref = pm
            pm.get_session()
            raise ValueError("test")
        assert pm_ref.cached_session_count == 0

    def test_del_calls_close(self, pm_no_proxies):
        """__del__ should call close() without raising."""
        pm_no_proxies.get_session()
        # __del__ should not raise
        pm_no_proxies.__del__()
        assert pm_no_proxies.cached_session_count == 0
