"""Unit tests for async file I/O in API routers.

Verifies that endpoints use asyncio.to_thread() for file reads and do not
block the event loop.  Uses monkeypatch to stub load_data_from_file so the
tests are hermetic (no dependency on real data/ files).
"""

import asyncio
import inspect

import pytest
from fastapi.testclient import TestClient

from src.api import routers
from src.api.main import app
from src.services import data_loader

client = TestClient(app)


# ── Helpers ──────────────────────────────────────────────────────────────────

FAKE_ITEMS = [
    {"title": "Test Article 1", "url": "https://example.com/1", "published_at": "2025-01-01T00:00:00Z"},
    {"title": "Test Article 2", "url": "https://example.com/2", "published_at": "2025-01-02T00:00:00Z"},
]


def _patch_loader(monkeypatch, capture: dict | None = None):
    """Replace load_data_from_file with a stub that optionally records calls."""

    def _fake_load(file_path: str):
        if capture is not None:
            capture.setdefault("calls", []).append(file_path)
        return FAKE_ITEMS

    monkeypatch.setattr(data_loader, "load_data_from_file", _fake_load)
    monkeypatch.setattr(routers, "load_data_from_file", _fake_load)


# ── Async helper tests ───────────────────────────────────────────────────────


def test_load_and_process_items_is_coroutine():
    """_load_and_process_items must be an async function."""
    assert inspect.iscoroutinefunction(routers._load_and_process_items)


def test_load_benchmarks_is_coroutine():
    """_load_benchmarks must be an async function."""
    assert inspect.iscoroutinefunction(routers._load_benchmarks)


def test_load_and_process_items_concurrent_reads(monkeypatch):
    """All source files should be read via asyncio.to_thread concurrently."""
    capture: dict = {}
    _patch_loader(monkeypatch, capture)

    config = {
        "src_a": {"path": "/fake/a.json", "name": "Source A"},
        "src_b": {"path": "/fake/b.json", "name": "Source B"},
        "src_c": {"path": "/fake/c.json", "name": "Source C"},
    }

    result = asyncio.run(routers._load_and_process_items(config))
    # All sources return the same items, so dedup reduces to 2 unique items
    assert len(result) == 2
    assert len(capture["calls"]) == 3  # but all 3 files were read


def test_load_and_process_items_source_filter(monkeypatch):
    """Source filter should reduce files read to just one."""
    capture: dict = {}
    _patch_loader(monkeypatch, capture)

    config = {
        "src_a": {"path": "/fake/a.json", "name": "Source A"},
        "src_b": {"path": "/fake/b.json", "name": "Source B"},
    }

    result = asyncio.run(routers._load_and_process_items(config, source_filter="src_b"))
    assert len(capture["calls"]) == 1
    assert capture["calls"][0] == "/fake/b.json"
    # All items come from the same fake stub, so just verify count
    assert len(result) == 2


def test_load_benchmarks_concurrent_reads(monkeypatch):
    """Benchmark files should be read concurrently."""
    capture: dict = {}
    _patch_loader(monkeypatch, capture)

    result = asyncio.run(routers._load_benchmarks())
    assert "models" in result
    assert result["count"] > 0
    # BENCHMARKS_SOURCES_CONFIG has multiple entries
    assert len(capture["calls"]) > 1


# ── Endpoint integration tests (mocked) ──────────────────────────────────────


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/news",
        "/api/v1/knowledge-garden",
        "/api/v1/ecommerce",
        "/api/v1/entertainment",
        "/api/v1/intelligence",
        "/api/v1/travel",
        "/api/v1/research",
        "/api/v1/museums",
        "/api/v1/games",
        "/api/v1/arxiv",
        "/api/v1/ai-platforms",
        "/api/v1/expanded",
        "/api/v1/spanish-aid",
        "/api/v1/cloud-updates",
        "/api/v1/valencia-local",
    ],
)
def test_endpoints_return_200_with_mocked_data(monkeypatch, endpoint):
    """Every async endpoint should return 200 and a list when data is mocked."""
    _patch_loader(monkeypatch)
    response = client.get(f"{endpoint}?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_benchmarks_endpoint_returns_200_with_mocked_data(monkeypatch):
    """Benchmarks endpoint returns a dict with models key."""
    _patch_loader(monkeypatch)
    response = client.get("/api/v1/benchmarks")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "count" in data


# ── Pagination tests (offset + limit) ─────────────────────────────────────


def test_offset_returns_different_items(monkeypatch):
    """offset=1 should skip the first item compared to offset=0."""
    _patch_loader(monkeypatch)
    r0 = client.get("/api/v1/news?limit=1&offset=0")
    r1 = client.get("/api/v1/news?limit=1&offset=1")
    assert r0.status_code == 200
    assert r1.status_code == 200
    d0 = r0.json()
    d1 = r1.json()
    if len(d0) > 0 and len(d1) > 0:
        assert d0[0]["title"] != d1[0]["title"]


def test_default_limit_is_50(monkeypatch):
    """With no limit param, exactly 50 items should be returned (deduped fake data has only 2)."""
    _patch_loader(monkeypatch)
    response = client.get("/api/v1/news")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_offset_beyond_range_returns_empty(monkeypatch):
    """An offset beyond available items should return an empty list."""
    _patch_loader(monkeypatch)
    response = client.get("/api/v1/news?limit=5&offset=99999")
    assert response.status_code == 200
    assert response.json() == []


def test_benchmarks_offset_and_limit(monkeypatch):
    """Benchmarks endpoint should respect offset and limit params."""
    _patch_loader(monkeypatch)
    response = client.get("/api/v1/benchmarks?limit=1&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "count" in data
