"""Unit tests for the HF daily papers ETL (T-040 — PWC successor)."""

import pytest

from src.etl.arxiv import hf_daily_papers_etl as hf_etl


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _item(paper_id="2608.25204", title="A paper", upvotes=10, repo="", stars=None, authors=None, published="2026-08-25T00:00:00.000Z"):
    return {
        "paper": {
            "id": paper_id,
            "title": title,
            "upvotes": upvotes,
            "githubRepo": repo,
            "githubStars": stars,
            "authors": authors or [{"name": "Ana"}, {"name": "Bob"}],
            "publishedAt": published,
            "summary": "abstract text",
            "ai_summary": "ai text",
            "ai_keywords": ["kw1", "kw2"],
        },
        "numComments": 3,
    }


def test_normalization_maps_renderer_fields(monkeypatch):
    monkeypatch.setattr(hf_etl.requests, "get", lambda *a, **kw: _FakeResponse([_item(repo="https://github.com/x/y", stars=42)]))
    records = hf_etl.fetch_daily_papers()
    assert len(records) == 1
    r = records[0]
    assert r["link"] == "https://huggingface.co/papers/2608.25204"
    assert r["id"] == "https://arxiv.org/abs/2608.25204"
    assert r["github_html_url"] == "https://github.com/x/y"
    assert r["github_stars"] == 42
    assert r["authors"] == ["Ana", "Bob"]
    assert r["upvotes"] == 10


def test_sorted_by_upvotes_desc(monkeypatch):
    items = [_item(paper_id="1", upvotes=5), _item(paper_id="2", upvotes=99), _item(paper_id="3", upvotes=42)]
    monkeypatch.setattr(hf_etl.requests, "get", lambda *a, **kw: _FakeResponse(items))
    records = hf_etl.fetch_daily_papers()
    assert [r["upvotes"] for r in records] == [99, 42, 5]


def test_skips_items_without_title_or_id(monkeypatch):
    monkeypatch.setattr(hf_etl.requests, "get", lambda *a, **kw: _FakeResponse([_item(paper_id="", title="x"), _item(paper_id="9", title=""), _item()]))
    assert len(hf_etl.fetch_daily_papers()) == 1


def test_summary_falls_back_to_ai_summary(monkeypatch):
    no_abstract = _item()
    no_abstract["paper"]["summary"] = ""
    monkeypatch.setattr(hf_etl.requests, "get", lambda *a, **kw: _FakeResponse([no_abstract]))
    assert hf_etl.fetch_daily_papers()[0]["summary"] == "ai text"


def test_hf_trending_registered_in_dashboard_config():
    from src.services.data_loader import ARXIV_SOURCES_CONFIG

    assert "hf_trending" in ARXIV_SOURCES_CONFIG
    assert ARXIV_SOURCES_CONFIG["hf_trending"]["name"] == "🔥 HF Trending"


@pytest.mark.parametrize("module_url", ["https://huggingface.co/api/daily_papers"])
def test_endpoint_is_keyless_get(module_url):
    # The URL must stay a plain GET endpoint — no key in the query string
    assert "?" not in module_url
    assert hf_etl.HF_DAILY_PAPERS_URL == module_url
