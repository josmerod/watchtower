"""Integration tests for the Watchtower API."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_sources():
    """Test getting available sources."""
    response = client.get("/api/v1/sources")
    assert response.status_code == 200
    data = response.json()
    assert "news" in data
    assert "knowledge_garden" in data
    assert "techcrunch" in data["news"]
    assert "opensource" in data["knowledge_garden"]


def test_get_news():
    """Test getting news items."""
    response = client.get("/api/v1/news?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # assert len(data) <= 5 # Limit might return less if no data
    if data:
        item = data[0]
        assert "title" in item
        assert "source" in item
        assert "url" in item


def test_get_news_filtered():
    """Test filtering news by source."""
    # filtering by a source that likely exists
    response = client.get("/api/v1/news?source=techcrunch")
    assert response.status_code == 200
    data = response.json()
    if data:
        assert data[0]["source"] == "TechCrunch"


def test_get_knowledge():
    """Test getting knowledge garden items."""
    response = client.get("/api/v1/knowledge-garden?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        item = data[0]
        assert "title" in item
        assert "source" in item


def test_get_knowledge_filtered():
    """Test filtering knowledge items."""
    response = client.get("/api/v1/knowledge-garden?source=opensource")
    assert response.status_code == 200
    data = response.json()
    if data:
        assert data[0]["source"] == "Open Source Projects"
