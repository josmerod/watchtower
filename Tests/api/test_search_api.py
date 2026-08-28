"""Hermetic unit tests for the keyless global search endpoint (T-057).

All tests inject a :class:`ContentSearchIndex` bound to a ``tmp_path`` data
directory by monkeypatching ``src.api.search._get_index`` — the real ``data/``
dir and the network are never touched.
"""

import json
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import src.api.search as search_api
from src.api.main import app
from src.services.content_search import ContentSearchIndex

client = TestClient(app)


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Bind the endpoint's index to a temp data directory."""
    monkeypatch.setattr(search_api, "_get_index", lambda: ContentSearchIndex(data_dir=tmp_path))
    return tmp_path


def _write(root: Path, rel_path: str, payload) -> None:
    """Write a JSON payload under the temp data dir."""
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")


def test_search_ok(data_dir: Path):
    """200 with the {query, count, items} envelope and no-store cache."""
    _write(
        data_dir,
        "news/techcrunch_latest.json",
        [{"title": "Kubernetes at the edge", "link": "https://tc/1", "published": "2026-08-28T08:00:00Z"}, {"title": "Unrelated", "link": "https://tc/2", "published": "2026-08-28T07:00:00Z"}],
    )
    response = client.get("/api/v1/search", params={"q": "kubernetes"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert set(body) == {"query", "count", "items"}
    assert body["query"] == "kubernetes"
    assert body["count"] == 1
    assert body["items"] == [{"title": "Kubernetes at the edge", "url": "https://tc/1", "source": "TechCrunch", "kind": "news", "published": "2026-08-28T08:00:00Z"}]


def test_search_ranked_newest_first(data_dir: Path):
    """Within a match tier, newer items come first."""
    _write(
        data_dir,
        "markets/coingecko_latest.json",
        [
            {"id": "eth", "name": "Ethereum", "symbol": "eth", "fetched_at": "2026-08-28T10:00:00Z"},
            {"id": "btc", "name": "Bitcoin", "symbol": "btc", "fetched_at": "2026-08-27T10:00:00Z"},
        ],
    )
    body = client.get("/api/v1/search", params={"q": "coin"}).json()  # source match: "CoinGecko"
    assert [i["title"] for i in body["items"]] == ["Ethereum (ETH)", "Bitcoin (BTC)"]


def test_search_limit(data_dir: Path):
    """?limit= truncates; out-of-range limits are rejected with 422."""
    _write(data_dir, "news/wired_latest.json", [{"title": f"Docker story {i}", "link": f"https://w/{i}", "published": f"2026-08-{20 + i:02d}T00:00:00Z"} for i in range(5)])
    body = client.get("/api/v1/search", params={"q": "docker", "limit": 2}).json()
    assert body["count"] == 2
    assert client.get("/api/v1/search", params={"q": "docker", "limit": 0}).status_code == 422
    assert client.get("/api/v1/search", params={"q": "docker", "limit": 101}).status_code == 422


def test_search_empty_query_is_400(data_dir: Path):
    """Empty or whitespace-only q returns 400 with {"error": ...} (documented choice)."""
    for q in ("", "   "):
        response = client.get("/api/v1/search", params={"q": q})
        assert response.status_code == 400
        assert "error" in response.json()
        assert response.headers["cache-control"] == "no-store"
    # Missing q entirely is a FastAPI validation error (422).
    assert client.get("/api/v1/search").status_code == 422


def test_search_empty_corpus_is_200(data_dir: Path):
    """No indexed files at all yields 200 with count 0 (not 404)."""
    response = client.get("/api/v1/search", params={"q": "anything"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["items"] == []


def test_search_malformed_file_degrades(data_dir: Path):
    """An unparsable collection file is skipped; other files still serve."""
    bad = data_dir / "news" / "techcrunch_latest.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("{broken", encoding="utf-8")
    _write(data_dir, "news/wired_latest.json", [{"title": "Wired ok", "link": "https://w/1", "published": "2026-08-28T00:00:00Z"}])
    body = client.get("/api/v1/search", params={"q": "wired"}).json()
    assert body["count"] == 1


def test_get_index_builds_singleton_once(monkeypatch: pytest.MonkeyPatch):
    """The process-wide index is built lazily and reused (thread-safe)."""
    built = []

    class FakeIndex:
        """Minimal stand-in counting instantiations."""

        def search(self, query: str, limit: int = 25) -> list[dict]:
            """Return one deterministic hit."""
            return [{"title": f"hit:{query}", "url": None, "source": "s", "kind": "news", "published": ""}]

    def _builder() -> FakeIndex:
        built.append(1)
        return FakeIndex()

    monkeypatch.setattr(search_api, "_build_index", _builder)
    search_api._index = None
    try:
        first = search_api._get_index()
        results = []
        threads = [threading.Thread(target=lambda: results.append(search_api._get_index())) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(built) == 1
        assert all(r is first for r in results)
        body = client.get("/api/v1/search", params={"q": "x"}).json()
        assert body["items"][0]["title"] == "hit:x"
    finally:
        search_api._index = None


def test_openapi_includes_search_endpoint():
    """The new endpoint shows up in the generated OpenAPI schema."""
    schema = client.get("/openapi.json").json()
    assert "/api/v1/search" in schema["paths"]
    assert "get" in schema["paths"]["/api/v1/search"]
