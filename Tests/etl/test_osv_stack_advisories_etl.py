"""Unit tests for the OSV stack advisories ETL + Security tab section (T-091).

Covers the CVSS scoring helpers, the >=HIGH severity filter, fixed-version
extraction (SEMVER/ECOSYSTEM/GIT ranges), GHSA/PYSEC dedupe, pagination and
per-service resilience (one failing service never kills the run), the saved
envelope shape and the tab's OSV companion card (calm state, hits, absent
file). Fixtures only — no live network; every file assertion runs against
``tmp_path``.
"""

import json

import requests

from src.etl.security import osv_stack_advisories_etl as etl
from src.web.dashboard.components import security_tab

# first.org specification examples / NVD-published base scores.
_V3_KNOWN = [
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", 9.8),
    ("CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:H/I:H/A:H", 7.2),
    ("CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:C/C:H/I:H/A:H", 9.1),
    ("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N", 6.5),
    ("CVSS:3.1/AV:L/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N", 1.8),
]


def _advisory(
    advisory_id: str,
    severity: str = "HIGH",
    cvss: str | None = None,
    cvss_type: str = "CVSS_V3",
    fixed: str | None = "2.28.1",
    range_type: str = "SEMVER",
    published: str = "2026-07-22T22:23:29Z",
    aliases: list[str] | None = None,
    summary: str = "RCE in workflow node",
) -> dict:
    """Build one raw OSV advisory shaped like the query API response."""
    raw: dict = {
        "id": advisory_id,
        "summary": summary,
        "published": published,
        "database_specific": {"severity": severity} if severity else {},
    }
    if cvss:
        raw["severity"] = [{"type": cvss_type, "score": cvss}]
    if aliases is not None:
        raw["aliases"] = aliases
    if fixed is not None:
        raw["affected"] = [{"ranges": [{"type": range_type, "events": [{"introduced": "0"}, {"fixed": fixed}]}]}]
    return raw


class TestCvssScoring:
    """The CVSS v3.1 calculator reproduces published scores."""

    def test_known_vectors(self):
        for vector, expected in _V3_KNOWN:
            assert etl._cvss_v3_base_score(vector) == expected, vector

    def test_malformed_vectors_return_none(self):
        assert etl._cvss_v3_base_score("") is None
        assert etl._cvss_v3_base_score("CVSS:3.1/AV:N") is None
        assert etl._cvss_v3_base_score("CVSS:3.1/AV:X/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H") is None

    def test_band_thresholds(self):
        assert etl._band_from_score(9.8) == "CRITICAL"
        assert etl._band_from_score(9.0) == "CRITICAL"
        assert etl._band_from_score(8.9) == "HIGH"
        assert etl._band_from_score(7.0) == "HIGH"
        assert etl._band_from_score(6.9) == "MODERATE"
        assert etl._band_from_score(3.1) == "LOW"

    def test_v4_approximation_band_only(self):
        # immich CVE-2025-43856 vector (NVD: High) — approximated onto the v3 formula.
        score = etl._cvss_v4_approx_score("CVSS:4.0/AV:N/AC:L/AT:P/PR:L/UI:A/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N")
        assert score is not None and 7.0 <= score < 9.0
        assert etl._cvss_v4_approx_score("CVSS:4.0/AV:N/AC:L/PR:N/UI:N/VC:L/VI:N/VA:N") is not None
        assert etl._cvss_v4_approx_score("CVSS:4.0/PR:N") is None


class TestSeverityFilter:
    """advisory_severity precedence and the >=HIGH floor in normalize_advisory."""

    def test_exact_cvss_vector_wins_over_database_specific(self):
        band, score, source = etl.advisory_severity(_advisory("GHSA-1", severity="HIGH", cvss="CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N"))
        assert (band, score, source) == ("MODERATE", 6.5, "cvss_v3")

    def test_database_specific_string_when_no_vector(self):
        band, score, source = etl.advisory_severity(_advisory("GHSA-2", severity="CRITICAL"))
        assert (band, score, source) == ("CRITICAL", None, "database_specific")

    def test_medium_normalizes_to_moderate(self):
        band, _, _ = etl.advisory_severity(_advisory("GHSA-3", severity="MEDIUM"))
        assert band == "MODERATE"

    def test_v4_only_falls_back_to_approximation(self):
        band, score, source = etl.advisory_severity(_advisory("CVE-1", severity="", cvss="CVSS:4.0/AV:N/AC:L/AT:P/PR:L/UI:A/VC:H/VI:H/VA:H", cvss_type="CVSS_V4"))
        assert (band, source) == ("HIGH", "cvss_v4_approx")
        assert score is None

    def test_normalize_keeps_high_and_critical_drops_below(self):
        assert etl.normalize_advisory(_advisory("GHSA-4", severity="HIGH")) is not None
        assert etl.normalize_advisory(_advisory("GHSA-5", severity="CRITICAL")) is not None
        assert etl.normalize_advisory(_advisory("GHSA-6", severity="MODERATE")) is None
        assert etl.normalize_advisory(_advisory("GHSA-7", severity="LOW")) is None
        assert etl.normalize_advisory({"id": "GHSA-8"}) is None  # ungradeable
        assert etl.normalize_advisory({"summary": "no id"}) is None

    def test_normalize_record_shape(self):
        advisory = etl.normalize_advisory(_advisory("GHSA-9", severity="HIGH", fixed="2.28.1", published="2026-07-22T22:23:29Z"))
        assert advisory == {
            "id": "GHSA-9",
            "summary": "RCE in workflow node",
            "severity": "HIGH",
            "cvss_score": None,
            "severity_source": "database_specific",
            "fixed_in": "2.28.1",
            "published": "2026-07-22",
            "url": "https://osv.dev/vulnerability/GHSA-9",
        }

    def test_empty_summary_falls_back_to_details_snippet(self):
        raw = _advisory("CVE-9", severity="HIGH", summary="")
        raw["details"] = "Jellyfin  allows  remote\n\nattackers to read arbitrary files."
        advisory = etl.normalize_advisory(raw)
        assert advisory is not None and advisory["summary"] == "Jellyfin allows remote attackers to read arbitrary files."


class TestFixedVersionExtraction:
    """Fixed-version extraction across SEMVER/ECOSYSTEM/GIT range shapes."""

    def test_ecosystem_range_plain_version(self):
        raw = {"affected": [{"ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "2025.02"}, {"fixed": "2026.01"}]}]}]}
        assert etl.extract_fixed_version(raw) == "2026.01"

    def test_git_range_prefers_extracted_events_over_shas(self):
        sha = "f659ef4b7aeb20f2fe433abb7fc6f7b4d95bb0ea"  # pragma: allowlist secret - public immich commit SHA fixture
        raw = {"affected": [{"ranges": [{"type": "GIT", "events": [{"introduced": "0"}, {"fixed": sha}], "database_specific": {"extracted_events": [{"introduced": "0"}, {"fixed": "2.5.0"}]}}]}]}
        assert etl.extract_fixed_version(raw) == "2.5.0"

    def test_latest_version_wins(self):
        raw = {"affected": [{"ranges": [{"type": "SEMVER", "events": [{"fixed": "2.28.9"}, {"fixed": "2.28.10"}, {"fixed": "2.9.0"}]}]}]}
        assert etl.extract_fixed_version(raw) == "2.28.10"

    def test_no_ranges_or_only_shas_yield_empty(self):
        assert etl.extract_fixed_version({}) == ""
        assert etl.extract_fixed_version({"affected": [{"ranges": [{"type": "GIT", "events": [{"fixed": "f659ef4b7aeb20f2fe433abb7fc6f7b4d95bb0ea"}]}]}]}) == ""  # pragma: allowlist secret - fixture SHA


class TestNormalizeAdvisories:
    """Dedupe, ordering and the per-service cap."""

    def test_duplicate_ghsa_pysec_records_collapse_on_cve_alias(self):
        ghsa = _advisory("GHSA-aa", severity="HIGH", fixed="2.28.1", aliases=["CVE-2026-1111"])
        pysec = _advisory("PYSEC-2026-1", severity="HIGH", fixed=None, aliases=["CVE-2026-1111"])
        assert len(etl.normalize_advisories([ghsa, pysec])) == 1
        assert len(etl.normalize_advisories([pysec, ghsa])) == 1

    def test_cap_at_limit_newest_first(self):
        raws = [_advisory(f"GHSA-{i:03d}", severity="HIGH", published=f"2026-{(i % 12) + 1:02d}-01T00:00:00Z") for i in range(15)]
        kept = etl.normalize_advisories(raws)
        assert len(kept) == etl.ADVISORIES_PER_SERVICE
        dates = [a["published"] for a in kept]
        assert dates == sorted(dates, reverse=True)

    def test_below_floor_records_are_dropped(self):
        kept = etl.normalize_advisories([_advisory("GHSA-100", severity="MODERATE"), _advisory("GHSA-101", severity="HIGH")])
        assert [a["id"] for a in kept] == ["GHSA-101"]


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class TestFetchAndCollect:
    """OSV query pagination + per-service resilience with stubbed transport."""

    def test_pagination_follows_next_page_token(self, monkeypatch):
        pages = [
            {"vulns": [_advisory("GHSA-a", severity="HIGH")], "next_page_token": "p2"},
            {"vulns": [_advisory("GHSA-b", severity="HIGH")], "next_page_token": "p3"},
            {"vulns": [_advisory("GHSA-c", severity="HIGH")]},  # MAX_PAGES stops after page 3 even with a token
        ]
        seen_tokens: list[str] = []

        def fake_post(url, json=None, headers=None, timeout=None):
            token = (json or {}).get("page_token", "")
            seen_tokens.append(token)
            return _FakeResponse(pages[len(seen_tokens) - 1])

        monkeypatch.setattr(etl.requests, "post", fake_post)
        vulns = etl.fetch_raw_advisories({"name": "n8n", "ecosystem": "npm"})
        assert [v["id"] for v in vulns] == ["GHSA-a", "GHSA-b", "GHSA-c"]
        assert seen_tokens == ["", "p2", "p3"]

    def test_one_service_failing_does_not_kill_the_run(self, monkeypatch, tmp_path):
        monkeypatch.setattr(etl, "SERVICE_DELAY_SECONDS", 0)

        def flaky_fetch_raw(package):
            if package["name"] == "n8n":
                raise requests.ConnectionError("OSV down")
            return [_advisory(f"GHSA-{package['ecosystem']}", severity="HIGH")]

        monkeypatch.setattr(etl, "fetch_raw_advisories", flaky_fetch_raw)
        services, ok_count = etl.collect_stack_advisories()
        assert ok_count == 3  # HA, immich, jellyfin answered; n8n failed
        n8n_group = next(s for s in services if s["repo"] == "n8n-io/n8n")
        assert n8n_group["advisories"] == [] and n8n_group["fetch_error"] is True
        assert etl.total_advisories(services) == 3

    def test_only_wired_services_are_queried(self, monkeypatch):
        queried: list[str] = []
        original = etl.fetch_service_advisories

        def spy(repo_cfg):
            queried.append(etl.repo_key(repo_cfg))
            return original(repo_cfg)

        monkeypatch.setattr(etl, "fetch_service_advisories", spy)
        monkeypatch.setattr(etl, "SERVICE_DELAY_SECONDS", 0)
        monkeypatch.setattr(etl, "_osv_query_page", lambda package, page_token="": {"vulns": []})
        services, ok_count = etl.collect_stack_advisories()
        assert queried == ["n8n-io/n8n", "home-assistant/core", "immich-app/immich", "jellyfin/jellyfin"]
        assert ok_count == 4
        assert all(set(s) == {"repo", "service_label", "advisories"} for s in services)


class TestSaveEnvelope:
    """save_stack_advisories writes the envelope the tab loader expects."""

    def test_save_writes_envelope_and_snapshot(self, tmp_path, monkeypatch):
        monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
        services = [{"repo": "n8n-io/n8n", "service_label": "n8n", "advisories": [{"id": "GHSA-1"}, {"id": "GHSA-2"}]}, {"repo": "jellyfin/jellyfin", "service_label": "jellyfin", "advisories": []}]
        assert etl.save_stack_advisories(services) is True

        data_dir = tmp_path / "data" / "security"
        payload = json.loads((data_dir / "osv_stack_latest.json").read_text(encoding="utf-8"))
        assert set(payload) == {"generated_at", "services", "total_advisories"}
        assert payload["services"] == services
        assert payload["total_advisories"] == 2
        assert payload["generated_at"]
        snapshots = [p for p in data_dir.iterdir() if p.name.startswith("osv_stack_") and p.name != "osv_stack_latest.json"]
        assert len(snapshots) == 1

    def test_all_services_failed_keeps_previous_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
        data_dir = tmp_path / "data" / "security"
        data_dir.mkdir(parents=True)
        (data_dir / "osv_stack_latest.json").write_text('{"generated_at": "old", "services": [], "total_advisories": 0}', encoding="utf-8")

        failed = [{"repo": "n8n-io/n8n", "service_label": "n8n", "advisories": [], "fetch_error": True}]
        assert etl.save_stack_advisories(failed) is False
        assert '"old"' in (data_dir / "osv_stack_latest.json").read_text(encoding="utf-8")

    def test_main_saves_and_survives_fetch_failure(self, tmp_path, monkeypatch):
        monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
        monkeypatch.setattr(etl, "SERVICE_DELAY_SECONDS", 0)

        def fake_collect():
            return [{"repo": "n8n-io/n8n", "service_label": "n8n", "advisories": [etl.normalize_advisory(_advisory("GHSA-z", severity="CRITICAL"))]}], 1

        monkeypatch.setattr(etl, "collect_stack_advisories", fake_collect)
        etl.main()
        payload = json.loads((tmp_path / "data" / "security" / "osv_stack_latest.json").read_text(encoding="utf-8"))
        assert payload["total_advisories"] == 1
        assert payload["services"][0]["advisories"][0]["id"] == "GHSA-z"


class TestTabOsvSection:
    """The OSV companion card: absent, calm and hit states — KEV UI intact."""

    def _write_osv(self, tmp_path, monkeypatch, payload):
        data_dir = tmp_path / "data" / "security"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "osv_stack_latest.json").write_text(json.dumps(payload), encoding="utf-8")
        monkeypatch.setattr(security_tab, "get_project_root", lambda: str(tmp_path))

    def test_absent_file_renders_no_osv_card(self, tmp_path, monkeypatch):
        monkeypatch.setattr(security_tab, "get_project_root", lambda: str(tmp_path))
        layout = str(security_tab.render_security_tab())
        assert "OSV" not in layout  # file absent → section stays quiet
        assert security_tab._load_osv_services() == []

    def test_calm_file_renders_quiet_success(self, tmp_path, monkeypatch):
        self._write_osv(tmp_path, monkeypatch, {"generated_at": "x", "services": [{"repo": "n8n-io/n8n", "service_label": "n8n", "advisories": []}], "total_advisories": 0})
        layout = str(security_tab.render_security_tab())
        assert "OSV advisories (≥high): 0" in layout
        assert "Avisos OSV (≥high) en TU stack" not in layout

    def test_broken_file_stays_quiet(self, tmp_path, monkeypatch):
        data_dir = tmp_path / "data" / "security"
        data_dir.mkdir(parents=True)
        (data_dir / "osv_stack_latest.json").write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(security_tab, "get_project_root", lambda: str(tmp_path))
        assert security_tab._load_osv_services() == []
        assert str(security_tab.render_security_tab())  # still renders

    def test_hits_render_with_link_badge_fixed_and_date(self, tmp_path, monkeypatch):
        services = [
            {
                "repo": "home-assistant/core",
                "service_label": "home-assistant",
                "advisories": [
                    {
                        "id": "GHSA-5hxg-r395-fqxx",
                        "summary": "RCE",
                        "severity": "CRITICAL",
                        "cvss_score": 9.3,
                        "severity_source": "cvss_v3",
                        "fixed_in": "2026.6.0",
                        "published": "2026-07-21",
                        "url": "https://osv.dev/vulnerability/GHSA-5hxg-r395-fqxx",
                    },
                    {
                        "id": "CVE-2026-23896",
                        "summary": "PrivEsc",
                        "severity": "HIGH",
                        "cvss_score": None,
                        "severity_source": "cvss_v4_approx",
                        "fixed_in": "",
                        "published": "2026-01-29",
                        "url": "https://osv.dev/vulnerability/CVE-2026-23896",
                    },
                ],
            }
        ]
        self._write_osv(tmp_path, monkeypatch, {"generated_at": "x", "services": services, "total_advisories": 2})
        layout = str(security_tab.render_security_tab())
        assert "OSV advisories (≥high): 2" in layout
        assert "home-assistant" in layout
        assert "https://osv.dev/vulnerability/GHSA-5hxg-r395-fqxx" in layout
        assert "CRITICAL" in layout and "HIGH" in layout
        assert "CVSS 9.3" in layout and "fixed in 2026.6.0" in layout
        assert "2026-07-21" in layout
        # No fixed-in → no badge; no score → no CVSS chip.
        assert "fixed in CVE-2026-23896" not in layout and "CVSS None" not in layout
        # The KEV UI sections stay intact alongside the new OSV section.
        assert "Vulnerabilidades explotadas" in layout and "Noticias de seguridad" in layout
        assert "0 CVEs explotados afectan a tu stack" in layout  # calm KEV card untouched
