"""Unit tests for the Security intelligence ETL + tab (T-050)."""

import json

from src.etl.security import security_feeds_etl as etl
from src.web.dashboard.components import security_tab


class _FakeResponse:
    def __init__(self, payload, content=None):
        self._payload = payload
        self.content = content or b""
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


_KEV = {
    "cveID": "CVE-2026-1234",
    "product": "SuperSoftware",
    "vendor": "Acme",
    "dateAdded": "2026-08-26",
    "description": "RCE in component",
    "knownRansomwareCampaignUse": "Known",
    "dueDate": "2026-09-15",
    "requiredAction": "Apply updates",
}


def test_kev_normalization(monkeypatch):
    monkeypatch.setattr(etl.requests, "get", lambda *a, **kw: _FakeResponse({"vulnerabilities": [_KEV]}))
    records = etl.fetch_kev()
    r = records[0]
    assert r["source"] == "cisa_kev" and r["severity"] == "known-exploited"
    assert r["link"] == "https://nvd.nist.gov/vuln/detail/CVE-2026-1234"
    assert "ransomware use: Known" in r["summary"] and "Acme" in r["summary"]


def test_kev_sorted_newest_first_and_capped(monkeypatch):
    vulns = [{**_KEV, "cveID": f"CVE-2026-{i:04d}", "dateAdded": f"2026-08-{i % 28 + 1:02d}"} for i in range(80)]
    monkeypatch.setattr(etl.requests, "get", lambda *a, **kw: _FakeResponse({"vulnerabilities": vulns}))
    records = etl.fetch_kev()
    assert len(records) == etl.KEV_ITEMS_KEPT
    dates = [r["published"] for r in records]
    assert dates == sorted(dates, reverse=True)


RSS = """<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>News A</title><link>https://x/a</link><pubDate>Tue, 26 Aug 2026 10:00:00 +0000</pubDate><description>&lt;p&gt;desc&lt;/p&gt;</description></item>
</channel></rss>"""


def test_rss_feed_normalization(monkeypatch):
    feed = {"url": "https://x/feed", "source": "thehackernews", "platform": "thehackernews"}
    monkeypatch.setattr(etl.requests, "get", lambda *a, **kw: _FakeResponse(None, content=RSS.encode()))
    entries = etl._fetch_rss_feed(feed)
    e = entries[0]
    assert e["title"] == "News A" and e["summary"] == "desc" and e["severity"] == "news"
    assert e["published"].startswith("2026-08-26T10:00:00")


def test_tab_renders_sections_with_data(tmp_path, monkeypatch):
    data_dir = tmp_path / "data" / "security"
    data_dir.mkdir(parents=True)
    payload = [
        {"source": "cisa_kev", "title": "🔴 CVE-1 — X", "link": "https://nvd/1", "published": "2026-08-26", "summary": "RCE — vendor: v · ransomware use: Known"},
        {"source": "krebs", "title": "News", "link": "https://k/1", "published": "2026-08-26T00:00:00Z", "summary": "s"},
    ]
    (data_dir / "security_latest.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(security_tab, "get_project_root", lambda: str(tmp_path))
    layout = str(security_tab.render_security_tab())
    assert "Vulnerabilidades explotadas" in layout and "Noticias de seguridad" in layout
    assert "CVE-1" in layout and "News" in layout


def test_tab_registered_in_app():
    from src.web.dashboard.app import _TAB_RENDERERS

    assert _TAB_RENDERERS.get("tab-security") is security_tab.render_security_tab
