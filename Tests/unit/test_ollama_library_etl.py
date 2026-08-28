"""Unit tests for the T-075 Ollama library ETL.

The library HTML is exercised through a fixture page mirroring the live
ollama.com/library card markup (validated in the T-075 probe) with
monkeypatched ``requests.get`` — no network in unit tests.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest
import requests

from src.etl.ai_platforms import ollama_library_etl as etl

_NOW = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


def _card(name: str, description: str = "A model.", pulls: str = "1K", updated: str = "1 month ago", tags: list[str] | None = None, sizes: list[str] | None = None) -> str:
    """One ollama.com/library card, mirroring the live markup anchors."""
    tags = tags if tags is not None else ["tools"]
    sizes = sizes if sizes is not None else ["8b"]
    tag_spans = "".join(f'<span class="inline-flex items-center rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-600 sm:text-[13px]">{t}</span>' for t in tags)
    size_spans = "".join(f'<span class="inline-flex items-center rounded-md bg-[#ddf4ff] px-2 py-0.5 text-xs font-medium text-blue-600 sm:text-[13px]">{s}</span>' for s in sizes)
    return (
        f'<a href="/library/{name}" class="group w-full space-y-5">'
        f'<div title="{name}" class="flex flex-col">'
        '<h2 class="truncate text-xl font-medium underline-offset-2 md:text-2xl">'
        '<div class="flex space-x-2 items-center">'
        f'<span class="group-hover:underline truncate">{name}</span>'
        "</div></h2>"
        f'<p class="max-w-lg break-words text-neutral-800 text-md">{description}</p>'
        "</div>"
        '<div class="flex flex-col space-y-2">'
        f'<div class="flex flex-wrap space-x-2">{tag_spans}{size_spans}</div>'
        '<p class="my-4 flex space-x-5 text-[13px] font-medium text-neutral-500">'
        f'<span class="flex items-center"><svg></svg> <span >{pulls}</span> <span class="hidden sm:flex">&nbsp;Pulls</span> </span>'
        f'<span class="flex items-center"><svg></svg> <span class="hidden sm:flex">Updated&nbsp;</span> <span >{updated}</span> </span>'
        "</p></div></a>"
    )


def _page(cards: list[str]) -> str:
    return "<html><body><main>" + "\n".join(cards) + "</main></body></html>"


# ---------------------------------------------------------------------------
# Card parsing
# ---------------------------------------------------------------------------


def test_parse_extracts_all_card_fields():
    html = _page([_card("llama3.1", description="Meta&#39;s Llama 3.1 is state of the art.", pulls="118.9M", updated="1 year ago", tags=["tools", "vision"], sizes=["8b", "70b", "405b"])])
    records = etl.parse_library_html(html, now=_NOW)
    assert len(records) == 1
    record = records[0]
    assert record["name"] == "llama3.1" and record["title"] == "llama3.1"
    assert record["description"] == "Meta's Llama 3.1 is state of the art."  # entity unescaped
    assert record["link"] == "https://ollama.com/library/llama3.1" and record["url"] == record["link"]
    assert record["pulls"] == "118.9M" and record["pulls_count"] == 118_900_000
    assert record["tags"] == ["tools", "vision"] and record["sizes"] == ["8b", "70b", "405b"]
    assert record["updated_relative"] == "1 year ago"
    assert record["published"] == (_NOW - timedelta(days=365)).isoformat()
    assert record["source"] == "ollama_library" and record["source_category"] == "local_llm"
    assert "118.9M pulls" in record["summary"] and "8b, 70b, 405b" in record["summary"]


def test_parse_pulls_count_variants():
    assert etl.parse_pulls("6,325") == 6325
    assert etl.parse_pulls("940K") == 940_000
    assert etl.parse_pulls("118.9M") == 118_900_000
    assert etl.parse_pulls("42") == 42
    assert etl.parse_pulls("") == 0
    assert etl.parse_pulls("n/a") == 0


def test_relative_date_conversion():
    assert etl.relative_to_iso("yesterday", _NOW) == (_NOW - timedelta(days=1)).isoformat()
    assert etl.relative_to_iso("15 hours ago", _NOW) == (_NOW - timedelta(hours=15)).isoformat()
    assert etl.relative_to_iso("3 weeks ago", _NOW) == (_NOW - timedelta(weeks=3)).isoformat()
    assert etl.relative_to_iso("10 months ago", _NOW) == (_NOW - timedelta(days=300)).isoformat()
    assert etl.relative_to_iso("2 years ago", _NOW) == (_NOW - timedelta(days=730)).isoformat()
    assert etl.relative_to_iso("sometime", _NOW) == ""


def test_parse_sorts_newest_first_undated_last():
    html = _page([_card("ancient", updated="2 years ago"), _card("fresh", updated="16 hours ago"), _card("nodate", updated="")])
    names = [r["name"] for r in etl.parse_library_html(html, now=_NOW)]
    assert names == ["fresh", "ancient", "nodate"]


def test_fetch_parses_page_and_caps_at_25(monkeypatch):
    cards = [_card(f"model{i}", updated=f"{i % 30} days ago") for i in range(30)]
    monkeypatch.setattr(etl.requests, "get", lambda *a, **kw: _FakeResponse(_page(cards)))
    records = etl.fetch_ollama_library()
    assert len(records) == etl.MAX_ITEMS == 25
    assert records[0]["published"] >= records[-1]["published"]  # newest first survives the cap


def test_fetch_failure_returns_empty(monkeypatch):
    def _boom(*a, **kw):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(etl.requests, "get", _boom)
    assert etl.fetch_ollama_library() == []


def test_fetch_empty_markup_returns_empty(monkeypatch):
    monkeypatch.setattr(etl.requests, "get", lambda *a, **kw: _FakeResponse("<html>client-side app</html>"))
    assert etl.fetch_ollama_library() == []


# ---------------------------------------------------------------------------
# Persistence (last-good semantics)
# ---------------------------------------------------------------------------


@pytest.fixture()
def _records():
    return [
        {"source": "ollama_library", "title": "fresh", "name": "fresh", "link": "https://ollama.com/library/fresh", "published": "2026-08-27T20:00:00+00:00", "summary": "s"},
        {"source": "ollama_library", "title": "old", "name": "old", "link": "https://ollama.com/library/old", "published": "2026-07-01T00:00:00+00:00", "summary": "s"},
    ]


def test_save_writes_latest_and_snapshot(tmp_path, monkeypatch, _records):
    monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
    assert etl.save_ollama_library(_records) is True
    data_dir = tmp_path / "data" / "ai_platforms"
    latest = json.loads((data_dir / "ollama_library_latest.json").read_text(encoding="utf-8"))
    assert latest == _records
    snapshots = [p for p in data_dir.glob("ollama_library_*.json") if p.name != "ollama_library_latest.json"]
    assert len(snapshots) == 1


def test_save_empty_run_keeps_last_good(tmp_path, monkeypatch, _records):
    monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
    etl.save_ollama_library(_records)
    latest_path = tmp_path / "data" / "ai_platforms" / "ollama_library_latest.json"
    assert etl.save_ollama_library([]) is False  # markup change → nothing parsed
    assert json.loads(latest_path.read_text(encoding="utf-8")) == _records  # last-good untouched
