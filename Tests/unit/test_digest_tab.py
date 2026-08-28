"""Render smoke tests for the 📅 Digest tab (T-054)."""

import json

from src.web.dashboard.components import digest_tab


def _digest_payload():
    return {
        "generated_at": "2026-08-28T10:00:00",
        "date": "2026-08-28",
        "period": {"start": "2026-08-21T10:00:00", "end": "2026-08-28T10:00:00", "days": 7},
        "top_terms": [{"term": "docker", "mentions": 12, "sources": 4}],
        "radar_best": [{"title": "Docker ships a big release", "url": "https://x/1", "source": "Hacker News", "source_key": "hn_frontpage", "published": "2026-08-27", "trending_terms": ["docker"]}],
        "market_movers": {"gainers": [{"name": "Bitcoin", "symbol": "BTC", "change_24h_pct": 5.0}], "losers": [{"name": "Doge", "symbol": "DOGE", "change_24h_pct": -9.9}]},
        "courses_watcher": {"events_last_week": 2, "total_events": 5, "last_check": "2026-08-28T09:00:00"},
        "freshness": {"checked_at": "2026-08-28T09:00:00", "counts": {"fresh": 8, "stale": 2, "critical": 1}},
    }


def _write_digest(tmp_path, payload):
    data_dir = tmp_path / "data" / "insights"
    data_dir.mkdir(parents=True)
    (data_dir / "digest_latest.json").write_text(json.dumps(payload), encoding="utf-8")


def test_tab_renders_with_data(tmp_path, monkeypatch):
    _write_digest(tmp_path, _digest_payload())
    monkeypatch.setattr(digest_tab, "get_project_root", lambda: str(tmp_path))
    layout = digest_tab.render_digest_tab()
    text = str(layout)
    assert "digest-content" in text
    for needle in ("Términos 🔥", "Mejores del Radar", "Movers 📈", "docker", "Docker ships a big release", "Bitcoin", "Doge", "Cursos", "Frescura", "Generado"):
        assert needle in text


def test_tab_renders_empty_state_without_file(tmp_path, monkeypatch):
    monkeypatch.setattr(digest_tab, "get_project_root", lambda: str(tmp_path))
    layout = digest_tab.render_digest_tab()
    text = str(layout)
    assert "digest-content" in text
    assert "Aún no hay digest" in text


def test_partial_digest_renders_without_crash(tmp_path, monkeypatch):
    payload = _digest_payload()
    payload["courses_watcher"] = None
    payload["freshness"] = None
    _write_digest(tmp_path, payload)
    monkeypatch.setattr(digest_tab, "get_project_root", lambda: str(tmp_path))
    text = str(digest_tab.render_digest_tab())
    assert "Bitcoin" in text
    assert "sin datos" in text


def test_refresh_content_rebuilds_from_disk(tmp_path, monkeypatch):
    _write_digest(tmp_path, _digest_payload())
    monkeypatch.setattr(digest_tab, "get_project_root", lambda: str(tmp_path))
    children = digest_tab._render_content(digest_tab._load_digest())
    assert "docker" in str(children)


def test_tab_registered_in_app():
    from src.web.dashboard.app import _TAB_RENDERERS

    assert _TAB_RENDERERS.get("tab-digest") is digest_tab.render_digest_tab
