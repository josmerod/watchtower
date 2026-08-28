"""Unit tests for the HF daily papers ETL (T-040 — PWC successor, T-058 — CrossRef citations)."""

from datetime import datetime, timedelta, timezone

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
    assert module_url == hf_etl.HF_DAILY_PAPERS_URL


# --- T-058: CrossRef citation enrichment (all tests fixture-based, no network) ---


def _paper(title, upvotes=10, **extra):
    record = {
        "source": "hf_daily_papers",
        "id": f"https://arxiv.org/abs/0000.0000{upvotes}",
        "title": title,
        "upvotes": upvotes,
    }
    record.update(extra)
    return record


def _crossref_item(title, count, doi="10.1000/fake", subtitle=None):
    return {"DOI": doi, "title": [title] if title else [], "subtitle": [subtitle] if subtitle else [], "is-referenced-by-count": count}


def test_title_tokens_strips_stopwords_and_punctuation():
    tokens = hf_etl._title_tokens("VGI-Bench: Probing Visual Intelligence in Video Generation Models!")
    assert "vgi" in tokens and "bench" in tokens
    assert "the" not in tokens and "in" not in tokens and "a" not in tokens


def test_title_match_confidence_short_stored_title_scores_via_containment():
    query = "Optuna: A Next Generation Hyperparameter Optimization Framework"
    stored = "Optuna"
    assert hf_etl.title_match_confidence(query, stored) == 1.0


def test_title_match_confidence_rejects_noise_hit():
    query = "VoiceMem: Streaming Dual-Brain Memory for Real-Time Interaction"
    noise = "Real-time brain state-coupled network-targeted dual-site TMS enhances working memory"
    assert hf_etl.title_match_confidence(query, noise) < hf_etl.CITATION_TITLE_MATCH_THRESHOLD


def test_title_match_confidence_empty_titles():
    assert hf_etl.title_match_confidence("", "Something") == 0.0
    assert hf_etl.title_match_confidence("Something", "") == 0.0


def test_fetch_citation_by_doi_extracts_count(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        return _FakeResponse({"status": "ok", "message": {"is-referenced-by-count": 8021, "DOI": "10.1145/3292500.3330701"}})

    monkeypatch.setattr(hf_etl.requests, "get", fake_get)
    result = hf_etl.fetch_citation_by_doi("10.1145/3292500.3330701")
    assert result == {"citation_count": 8021, "citation_source": "doi", "citation_doi": "10.1145/3292500.3330701"}
    assert "10.1145%2F3292500.3330701" in captured["url"]
    assert "mailto=" in captured["url"]  # polite pool


def test_fetch_citation_by_title_accepts_strong_match(monkeypatch):
    payload = {
        "status": "ok",
        "message": {
            "items": [
                _crossref_item("Totally unrelated brain paper", 3),
                _crossref_item("Optuna", 8021, doi="10.1145/3292500.3330701"),
            ]
        },
    }
    monkeypatch.setattr(hf_etl.requests, "get", lambda *a, **kw: _FakeResponse(payload))
    result = hf_etl.fetch_citation_by_title("Optuna: A Next Generation Hyperparameter Optimization Framework")
    assert result is not None
    assert result["citation_count"] == 8021
    assert result["citation_source"] == "title"
    assert result["citation_doi"] == "10.1145/3292500.3330701"


def test_fetch_citation_by_title_uses_subtitle_for_matching(monkeypatch):
    # Stored title alone ("VGI-Bench") does not match the query; the subtitle does.
    payload = {"status": "ok", "message": {"items": [_crossref_item("VGI-Bench", 7, subtitle="Probing Visual Intelligence in Video Generation Models")]}}
    monkeypatch.setattr(hf_etl.requests, "get", lambda *a, **kw: _FakeResponse(payload))
    result = hf_etl.fetch_citation_by_title("Probing Visual Intelligence in Video Generation Models")
    assert result == {"citation_count": 7, "citation_source": "title", "citation_doi": "10.1000/fake"}


def test_fetch_citation_by_title_rejects_weak_matches(monkeypatch):
    payload = {"status": "ok", "message": {"items": [_crossref_item("Real-time brain state-coupled network-targeted dual-site TMS enhances working memory", 0)]}}
    monkeypatch.setattr(hf_etl.requests, "get", lambda *a, **kw: _FakeResponse(payload))
    assert hf_etl.fetch_citation_by_title("VoiceMem: Streaming Dual-Brain Memory for Real-Time Interaction") is None


def test_fetch_citation_by_title_handles_bad_payloads(monkeypatch):
    monkeypatch.setattr(hf_etl.requests, "get", lambda *a, **kw: _FakeResponse({"message": {"items": []}}))
    assert hf_etl.fetch_citation_by_title("Whatever") is None
    monkeypatch.setattr(hf_etl.requests, "get", lambda *a, **kw: _FakeResponse({"message": {"items": [_crossref_item("Whatever", "not-an-int")]}}))
    assert hf_etl.fetch_citation_by_title("Whatever") is None


def test_fetch_citation_survives_request_error(monkeypatch):
    def boom(*a, **kw):
        raise hf_etl.requests.RequestException("down")

    monkeypatch.setattr(hf_etl.requests, "get", boom)
    assert hf_etl.fetch_citation_by_doi("10.1/x") is None
    assert hf_etl.fetch_citation_by_title("Whatever") is None


# --- sidecar cache ---


def test_cache_entry_freshness_by_ttl():
    now = datetime.now(timezone.utc).timestamp()
    fresh = {"citation_count": 5, "checked_at": datetime.now(timezone.utc).isoformat()}
    stale = {"citation_count": 5, "checked_at": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()}
    assert hf_etl._cache_entry_is_fresh(fresh, now) is True
    assert hf_etl._cache_entry_is_fresh(stale, now) is False
    assert hf_etl._cache_entry_is_fresh({"citation_count": "x", "checked_at": "nope"}, now) is False
    assert hf_etl._cache_entry_is_fresh("garbage", now) is False
    assert hf_etl._cache_entry_is_fresh(None, now) is False


def test_citation_cache_roundtrip(monkeypatch, tmp_path):
    path = tmp_path / "hf_paper_citations.json"
    monkeypatch.setattr(hf_etl, "citations_cache_path", lambda: str(path))
    assert hf_etl.load_citation_cache() == {}  # missing file

    hf_etl.save_citation_cache({"title:optuna": {"citation_count": 8021, "citation_source": "title", "checked_at": "2026-08-28T00:00:00+00:00"}})
    loaded = hf_etl.load_citation_cache()
    assert loaded["title:optuna"]["citation_count"] == 8021


def test_load_citation_cache_corrupt_file(monkeypatch, tmp_path):
    path = tmp_path / "hf_paper_citations.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(hf_etl, "citations_cache_path", lambda: str(path))
    assert hf_etl.load_citation_cache() == {}


def test_save_citation_cache_creates_missing_dir(monkeypatch, tmp_path):
    path = tmp_path / "no" / "dir" / "f.json"
    monkeypatch.setattr(hf_etl, "citations_cache_path", lambda: str(path))
    hf_etl.save_citation_cache({"k": {"citation_count": 1}})
    assert path.exists()


def test_save_citation_cache_swallows_os_error(monkeypatch, tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file", encoding="utf-8")
    monkeypatch.setattr(hf_etl, "citations_cache_path", lambda: str(blocker / "sub" / "f.json"))  # parent is a file -> OSError
    hf_etl.save_citation_cache({"k": {"citation_count": 1}})  # must not raise


# --- enrichment merge ---


def test_enrich_uses_fresh_cache_hit_without_network(monkeypatch):
    record = _paper("Optuna: A Next Generation Hyperparameter Optimization Framework")
    key = hf_etl._citation_cache_key(record)
    now = datetime.now(timezone.utc).timestamp()
    cache = {key: {"citation_count": 8021, "citation_source": "title", "citation_doi": "10.1145/x", "checked_at": datetime.now(timezone.utc).isoformat()}}
    sleeps = []

    def fail_fetch(*a, **kw):
        raise AssertionError("network must not be touched on a cache hit")

    result = hf_etl.enrich_with_citations([record], cache, doi_fetcher=fail_fetch, title_fetcher=fail_fetch, sleep_fn=sleeps.append, now_ts=now)
    assert record["citation_count"] == 8021
    assert record["citation_source"] == "title"
    assert record["citation_doi"] == "10.1145/x"
    assert result is cache
    assert sleeps == []


def test_enrich_queries_on_miss_and_caches(monkeypatch):
    record = _paper("Optuna: A Next Generation Hyperparameter Optimization Framework", upvotes=5)
    key = hf_etl._citation_cache_key(record)  # capture before enrichment adds a citation_doi
    now = datetime.now(timezone.utc).timestamp()
    sleeps = []

    def fake_title_fetcher(title):
        assert title == record["title"]
        return {"citation_count": 42, "citation_source": "title", "citation_doi": "10.1/abc"}

    cache = hf_etl.enrich_with_citations([record], {}, doi_fetcher=None, title_fetcher=fake_title_fetcher, sleep_fn=sleeps.append, now_ts=now)
    assert record["citation_count"] == 42
    assert cache[key]["citation_count"] == 42
    assert cache[key]["checked_at"]
    assert sleeps == []  # single lookup -> no pacing sleep


def test_enrich_paces_between_lookups():
    records = [_paper("Paper One", upvotes=9), _paper("Paper Two", upvotes=8)]
    sleeps = []
    cache = hf_etl.enrich_with_citations(records, {}, doi_fetcher=None, title_fetcher=lambda t: None, sleep_fn=sleeps.append)
    assert len(sleeps) == 1  # one sleep before the second lookup
    assert cache == {}


def test_enrich_failure_leaves_field_absent():
    records = [_paper("Paper One", upvotes=9)]
    cache = hf_etl.enrich_with_citations(records, {}, doi_fetcher=None, title_fetcher=lambda t: None, sleep_fn=lambda s: None)
    assert "citation_count" not in records[0]
    assert "citation_source" not in records[0]
    assert cache == {}


def test_enrich_stale_entry_is_requeried():
    record = _paper("Paper One", upvotes=9)
    key = hf_etl._citation_cache_key(record)
    now = datetime.now(timezone.utc).timestamp()
    stale = {"citation_count": 1, "citation_source": "title", "checked_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()}
    calls = []

    def fake_title_fetcher(title):
        calls.append(title)
        return {"citation_count": 99, "citation_source": "title", "citation_doi": "10.1/z"}

    cache = hf_etl.enrich_with_citations([record], {key: stale}, doi_fetcher=None, title_fetcher=fake_title_fetcher, sleep_fn=lambda s: None, now_ts=now)
    assert calls == [record["title"]]
    assert record["citation_count"] == 99
    assert cache[key]["citation_count"] == 99


def test_enrich_respects_max_papers_and_skips_records_without_key():
    top = _paper("Top Paper", upvotes=100)
    second = _paper("Second Paper", upvotes=90)
    tail = _paper("Tail Paper", upvotes=1)
    calls = []

    cache = hf_etl.enrich_with_citations([top, second, tail], {}, max_papers=2, doi_fetcher=None, title_fetcher=lambda t: (calls.append(t), None)[1], sleep_fn=lambda s: None)
    assert calls == [top["title"], second["title"]]  # tail beyond cap is untouched
    assert "citation_count" not in tail
    assert cache == {}


def test_enrich_prefers_doi_when_present():
    record = _paper("Some Title", upvotes=50, doi="10.1234/doi-path")

    def title_must_not_run(title):
        raise AssertionError("title fetcher must not run when a DOI is present")

    cache = hf_etl.enrich_with_citations([record], {}, doi_fetcher=lambda d: {"citation_count": 7, "citation_source": "doi", "citation_doi": d}, title_fetcher=title_must_not_run, sleep_fn=lambda s: None)
    assert record["citation_count"] == 7
    assert record["citation_source"] == "doi"
    assert "10.1234/doi-path" in cache


def test_main_merges_citations_into_saved_records(monkeypatch, tmp_path):
    saved = {}
    record = _paper("Optuna: A Next Generation Hyperparameter Optimization Framework", upvotes=10)

    monkeypatch.setattr(hf_etl, "fetch_daily_papers", lambda: [record])
    monkeypatch.setattr(hf_etl, "save_citation_cache", lambda cache: saved.update(cache))
    monkeypatch.setattr(hf_etl, "save_daily_papers", lambda recs: saved.setdefault("records", [dict(r) for r in recs]))
    monkeypatch.setattr(hf_etl, "enrich_with_citations", lambda recs, *a, **kw: recs[0].update(citation_count=15, citation_source="title", citation_doi="10.1/q") or {})

    hf_etl.main()
    assert saved["records"][0]["citation_count"] == 15


def test_main_survives_enrichment_failure(monkeypatch):
    saved = {}

    def broken_enrich(recs, *a, **kw):
        raise RuntimeError("crossref down")

    monkeypatch.setattr(hf_etl, "fetch_daily_papers", lambda: [_paper("X", upvotes=1)])
    monkeypatch.setattr(hf_etl, "enrich_with_citations", broken_enrich)
    monkeypatch.setattr(hf_etl, "save_citation_cache", lambda cache: None)
    monkeypatch.setattr(hf_etl, "save_daily_papers", lambda recs: saved.update(n=len(recs)))

    hf_etl.main()  # must not raise — papers still saved without counts
    assert saved["n"] == 1
