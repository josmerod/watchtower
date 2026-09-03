"""Unit tests for the KEV-vs-self-hosted-stack cross (T-081).

Covers the pure matcher (``src/etl/security/stack_cves.py``), the
``security_latest.json`` envelope round-trip, the Security tab's "🧰 Tu stack"
card/match list, and the ETL's best-effort alert wiring. Fixtures only — no
network, and every rule-store assertion runs against ``tmp_path`` files.
"""

import json

from src.etl.security import security_feeds_etl as etl
from src.etl.security.stack_cves import VENDOR_ALIASES, match_stack_to_kev, total_stack_matches
from src.web.dashboard.components import security_tab


def _kev(cve: str, product: str, date: str = "2026-08-26", ransomware: str = "Known", vendor: str = "Acme") -> dict:
    """Build one normalized ``cisa_kev`` record as persisted by the ETL."""
    return {
        "source": "cisa_kev",
        "title": f"🔴 {cve} — {product}",
        "link": f"https://nvd.nist.gov/vuln/detail/{cve}",
        "published": date,
        "summary": f"RCE — vendor: {vendor} · ransomware use: {ransomware}",
        "severity": "known-exploited",
        "cve": cve,
        "vendor": vendor,
        "product": product,
        "ransomware_use": ransomware,
    }


class TestMatcherAliases:
    """Every stack repo matches its KEV product aliases (case-insensitive)."""

    def test_home_assistant_aliases(self):
        records = [_kev("CVE-2026-0001", "HASSIO"), _kev("CVE-2026-0002", "Home Assistant")]
        matches = match_stack_to_kev(records)
        assert [g["repo"] for g in matches] == ["home-assistant/core"]
        assert [c["cve"] for c in matches[0]["cves"]] == ["CVE-2026-0001", "CVE-2026-0002"]
        assert matches[0]["service_label"] == "home-assistant"

    def test_each_service_matches_its_product(self):
        cases = [
            ("n8n-io/n8n", "n8n"),
            ("immich-app/immich", "Immich"),
            ("jellyfin/jellyfin", "JellyFin Media Server"),
            ("justarchinet/archisteamfarm", "ArchiSteamFarm"),
            ("haveagitgat/tdarr", "Tdarr"),
        ]
        for repo, product in cases:
            matches = match_stack_to_kev([_kev("CVE-2026-0009", product)])
            assert [g["repo"] for g in matches] == [repo], product

    def test_case_insensitive_and_multitoken_products(self):
        matches = match_stack_to_kev([_kev("CVE-2026-0010", "N8N WORKFLOW AUTOMATION")])
        assert [g["repo"] for g in matches] == ["n8n-io/n8n"]

    def test_match_entry_shape(self):
        matches = match_stack_to_kev([_kev("CVE-2026-0011", "n8n", date="2026-09-01", ransomware="Unknown")])
        entry = matches[0]["cves"][0]
        assert entry == {
            "cve": "CVE-2026-0011",
            "product": "n8n",
            "dateAdded": "2026-09-01",
            "title": "🔴 CVE-2026-0011 — n8n",
            "ransomware": "Unknown",
        }


class TestMatcherNoFalsePositives:
    """Similar-but-unrelated product names must never match."""

    def test_n8n_enterprise_unrelated_does_not_match(self):
        matches = match_stack_to_kev([_kev("CVE-2026-0100", "n8nenterprise-unrelated")])
        assert matches == []

    def test_generic_words_do_not_match(self):
        records = [
            _kev("CVE-2026-0101", "Virtual Assistant Pro"),
            _kev("CVE-2026-0102", "Steam Farm Simulator"),
            _kev("CVE-2026-0103", "Immicharts Navigation Suite"),
            _kev("CVE-2026-0104", "Jellyfish Server"),
        ]
        assert match_stack_to_kev(records) == []

    def test_unrelated_products_yield_empty(self):
        records = [_kev("CVE-2026-0105", "FortiOS"), _kev("CVE-2026-0106", "Windows SMB"), _kev("CVE-2026-0107", "")]
        assert match_stack_to_kev(records) == []

    def test_news_records_are_ignored_by_caller_contract(self):
        # Non-KEV records lack product/cve and cannot match even if passed in.
        assert match_stack_to_kev([{"source": "krebs", "title": "n8n breach news"}]) == []


class TestMatcherGrouping:
    """Grouping, ordering and dedupe semantics."""

    def test_only_repos_with_matches_are_returned_in_registry_order(self):
        records = [_kev("CVE-2026-0200", "Tdarr"), _kev("CVE-2026-0201", "n8n")]
        repos = [g["repo"] for g in match_stack_to_kev(records)]
        assert repos == ["n8n-io/n8n", "haveagitgat/tdarr"]  # STACK_REPOS order

    def test_duplicate_cve_deduped_per_repo(self):
        records = [_kev("CVE-2026-0202", "n8n"), _kev("CVE-2026-0202", "n8n automation")]
        matches = match_stack_to_kev(records)
        assert [c["cve"] for c in matches[0]["cves"]] == ["CVE-2026-0202"]

    def test_kev_order_preserved_newest_first(self):
        records = [_kev("CVE-2026-0203", "n8n", date="2026-09-01"), _kev("CVE-2026-0204", "n8n", date="2026-09-02")]
        cves = match_stack_to_kev(records)[0]["cves"]
        assert [c["dateAdded"] for c in cves] == ["2026-09-01", "2026-09-02"]

    def test_custom_stack_repos_override(self):
        custom = [{"owner": "acme", "repo": "widget", "label": "Widget"}]
        assert match_stack_to_kev([_kev("CVE-2026-0205", "n8n")], stack_repos=custom) == []
        assert match_stack_to_kev([_kev("CVE-2026-0206", "n8n")], stack_repos=custom + [{"owner": "n8n-io", "repo": "n8n", "label": "n8n"}])[0]["repo"] == "n8n-io/n8n"

    def test_total_stack_matches_counts_across_groups(self):
        records = [_kev("CVE-2026-0207", "n8n"), _kev("CVE-2026-0208", "jellyfin"), _kev("CVE-2026-0209", "jellyfin")]
        assert total_stack_matches(match_stack_to_kev(records)) == 3
        assert total_stack_matches([]) == 0

    def test_vendor_aliases_cover_every_stack_repo(self):
        from src.etl.github.stack_releases_etl import STACK_REPOS

        keys = {f"{r['owner']}/{r['repo']}".lower() for r in STACK_REPOS}
        assert keys == set(VENDOR_ALIASES)


class TestEnvelopeRoundTrip:
    """save_security_entries writes the envelope the tab loader expects."""

    def test_save_writes_envelope_with_stack_matches(self, tmp_path, monkeypatch):
        monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
        entries = [_kev("CVE-2026-0300", "n8n"), {"source": "krebs", "title": "News"}]
        matches = match_stack_to_kev([entries[0]])
        etl.save_security_entries(entries, matches)

        payload = json.loads((tmp_path / "data" / "security" / "security_latest.json").read_text(encoding="utf-8"))
        assert set(payload) == {"generated_at", "items", "stack_matches"}
        assert payload["items"] == entries
        assert payload["stack_matches"] == matches
        assert payload["generated_at"]

    def test_save_without_matches_defaults_to_empty_list(self, tmp_path, monkeypatch):
        monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
        etl.save_security_entries([{"source": "krebs", "title": "News"}])
        payload = json.loads((tmp_path / "data" / "security" / "security_latest.json").read_text(encoding="utf-8"))
        assert payload["stack_matches"] == []

    def test_empty_entries_skip_write(self, tmp_path, monkeypatch):
        monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
        etl.save_security_entries([])
        assert not (tmp_path / "data" / "security" / "security_latest.json").exists()

    def test_tab_loader_reads_envelope_written_by_etl(self, tmp_path, monkeypatch):
        monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
        entries = [_kev("CVE-2026-0301", "n8n")]
        etl.save_security_entries(entries, match_stack_to_kev(entries))
        monkeypatch.setattr(security_tab, "get_project_root", lambda: str(tmp_path))
        loaded_entries, loaded_matches = security_tab._load_feed()
        assert loaded_entries == entries
        assert loaded_matches[0]["repo"] == "n8n-io/n8n"

    def test_tab_loader_still_reads_legacy_flat_list(self, tmp_path, monkeypatch):
        data_dir = tmp_path / "data" / "security"
        data_dir.mkdir(parents=True)
        (data_dir / "security_latest.json").write_text(json.dumps([{"source": "cisa_kev", "title": "old"}]), encoding="utf-8")
        monkeypatch.setattr(security_tab, "get_project_root", lambda: str(tmp_path))
        entries, matches = security_tab._load_feed()
        assert entries == [{"source": "cisa_kev", "title": "old"}]
        assert matches == []

    def test_tab_loader_missing_or_broken_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(security_tab, "get_project_root", lambda: str(tmp_path))
        assert security_tab._load_feed() == ([], [])
        data_dir = tmp_path / "data" / "security"
        data_dir.mkdir(parents=True)
        (data_dir / "security_latest.json").write_text("{not json", encoding="utf-8")
        assert security_tab._load_feed() == ([], [])


class TestTabStackSection:
    """The 🧰 Tu stack card: calm state and highlighted match list."""

    def _write_feed(self, tmp_path, monkeypatch, payload):
        data_dir = tmp_path / "data" / "security"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "security_latest.json").write_text(json.dumps(payload), encoding="utf-8")
        monkeypatch.setattr(security_tab, "get_project_root", lambda: str(tmp_path))

    def test_calm_state_when_no_matches(self, tmp_path, monkeypatch):
        self._write_feed(tmp_path, monkeypatch, {"items": [], "stack_matches": []})
        layout = str(security_tab.render_security_tab())
        assert "0 CVEs explotados afectan a tu stack" in layout
        assert "CVEs que afectan a TU stack" not in layout

    def test_matches_render_with_badge_link_product_date_ransomware(self, tmp_path, monkeypatch):
        matches = [
            {
                "repo": "home-assistant/core",
                "service_label": "home-assistant",
                "cves": [
                    {
                        "cve": "CVE-2026-0400",
                        "product": "HASSIO",
                        "dateAdded": "2026-08-20",
                        "title": "🔴 CVE-2026-0400 — HASSIO",
                        "ransomware": "Known",
                    }
                ],
            }
        ]
        self._write_feed(tmp_path, monkeypatch, {"items": [_kev("CVE-2026-0400", "HASSIO")], "stack_matches": matches})
        layout = str(security_tab.render_security_tab())
        assert "🧰 Tu stack" in layout
        assert "1" in layout and "CVEs explotados activamente afectan a tu stack" in layout
        assert "CVEs que afectan a TU stack" in layout
        assert "home-assistant" in layout and "HASSIO" in layout
        assert "https://nvd.nist.gov/vuln/detail/CVE-2026-0400" in layout
        assert "2026-08-20" in layout and "Ransomware" in layout
        # Existing sections stay intact.
        assert "Vulnerabilidades explotadas" in layout and "Noticias de seguridad" in layout

    def test_unknown_ransomware_omits_badge(self, tmp_path, monkeypatch):
        matches = [{"repo": "tdarr", "service_label": "Tdarr", "cves": [{"cve": "CVE-2026-0401", "product": "Tdarr", "dateAdded": "2026-08-01", "title": "t", "ransomware": "Unknown"}]}]
        self._write_feed(tmp_path, monkeypatch, {"items": [], "stack_matches": matches})
        layout = str(security_tab.render_security_tab())
        assert "CVE-2026-0401" in layout
        assert "Ransomware" not in layout

    def test_legacy_flat_list_renders_calm_stack_card(self, tmp_path, monkeypatch):
        self._write_feed(tmp_path, monkeypatch, [{"source": "cisa_kev", "title": "🔴 CVE-1 — X", "link": "https://nvd/1", "published": "2026-08-26"}])
        layout = str(security_tab.render_security_tab())
        assert "0 CVEs explotados afectan a tu stack" in layout
        assert "CVE-1" in layout


class TestEtlAlertWiring:
    """main() computes matches and never breaks on alert-store failures."""

    def test_main_computes_matches_and_calls_alert_sync(self, tmp_path, monkeypatch):
        monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
        monkeypatch.setattr(etl, "fetch_security_feed", lambda: [_kev("CVE-2026-0500", "n8n")])
        calls: list[list[dict]] = []
        monkeypatch.setattr(etl, "sync_stack_cve_rules", lambda matches: calls.append(matches) or {"created": 1, "updated": 0, "unchanged": 0, "resolved": 0})
        etl.main()

        payload = json.loads((tmp_path / "data" / "security" / "security_latest.json").read_text(encoding="utf-8"))
        assert payload["stack_matches"][0]["repo"] == "n8n-io/n8n"
        assert calls and calls[0][0]["repo"] == "n8n-io/n8n"

    def test_alert_store_failure_does_not_break_etl(self, tmp_path, monkeypatch):
        monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
        monkeypatch.setattr(etl, "fetch_security_feed", lambda: [_kev("CVE-2026-0501", "jellyfin")])

        def boom(_matches):
            raise RuntimeError("rules store down")

        monkeypatch.setattr(etl, "sync_stack_cve_rules", boom)
        etl.main()  # must not raise; envelope still written
        payload = json.loads((tmp_path / "data" / "security" / "security_latest.json").read_text(encoding="utf-8"))
        assert payload["items"][0]["cve"] == "CVE-2026-0501"

    def test_kev_records_carry_matcher_fields(self, monkeypatch):
        class _FakeResponse:
            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        kev_json = {"cveID": "CVE-2026-0502", "product": "n8n", "vendor": "n8n-io", "dateAdded": "2026-08-30", "description": "RCE", "knownRansomwareCampaignUse": "Known"}
        monkeypatch.setattr(etl.requests, "get", lambda *a, **kw: _FakeResponse({"vulnerabilities": [kev_json]}))
        records = etl.fetch_kev()
        assert records[0]["cve"] == "CVE-2026-0502" and records[0]["product"] == "n8n" and records[0]["vendor"] == "n8n-io"
        assert match_stack_to_kev(records)[0]["repo"] == "n8n-io/n8n"
