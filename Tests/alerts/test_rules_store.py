"""Unit tests for the shared alert-rule store (src/alerts/rules_store.py).

All tests run against tmp_path rule files — the real ``data/alerts/rules.json``
is never touched.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from src.alerts.rules_store import (
    SEVERITY_BY_FRESHNESS,
    build_freshness_rule,
    build_stack_cve_rule,
    load_rules,
    resolve_rule,
    stack_cve_rule_id,
    sync_freshness_rules,
    sync_stack_cve_rules,
    upsert_rule,
)

NOW = 1_800_000_000.0


def _record(status="stale", age_hours=30.0, key="t", label="Test", exists=True):
    return {"key": key, "label": label, "path": f"{key}_latest.json", "exists": exists, "age_hours": age_hours, "status": status}


def _summary(*records):
    return {"checked_at": "2026-08-28T00:00:00+00:00", "counts": {}, "sources": list(records)}


class TestSeverityMapping:
    """Freshness status maps to alert severity."""

    def test_mapping(self):
        assert SEVERITY_BY_FRESHNESS == {"stale": "medium", "critical": "high"}


class TestBuildFreshnessRule:
    """Rule construction from a freshness record."""

    def test_stale_rule_shape_and_message(self):
        rule = build_freshness_rule(_record(), now=NOW)
        assert rule["id"] == "data_freshness_t"
        assert rule["severity"] == "medium"
        assert rule["active"] is True
        expected_since = datetime.fromtimestamp(NOW - 30 * 3600, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        assert rule["description"] == f"Fuente Test sin datos desde {expected_since} UTC (30h)"

    def test_critical_rule_is_high(self):
        rule = build_freshness_rule(_record(status="critical", age_hours=200.0), now=NOW)
        assert rule["severity"] == "high"
        assert rule["description"].endswith("(200h)")

    def test_missing_file_rule(self):
        rule = build_freshness_rule(_record(status="critical", age_hours=None, exists=False), now=NOW)
        assert rule["severity"] == "high"
        assert rule["description"] == "Fuente Test sin datos (archivo ausente)"


class TestLoadSave:
    """Store read/write robustness."""

    def test_load_missing_file_is_empty(self, tmp_path: Path):
        assert load_rules(tmp_path / "nope.json") == []

    def test_load_wraps_lone_dict(self, tmp_path: Path):
        f = tmp_path / "rules.json"
        f.write_text(json.dumps({"id": "r1"}), encoding="utf-8")
        assert load_rules(f) == [{"id": "r1"}]

    def test_load_invalid_json_is_empty(self, tmp_path: Path):
        f = tmp_path / "rules.json"
        f.write_text("{not json", encoding="utf-8")
        assert load_rules(f) == []


class TestUpsertRule:
    """Idempotent upsert-by-id semantics."""

    def test_created_then_unchanged(self, tmp_path: Path):
        f = tmp_path / "rules.json"
        rule = build_freshness_rule(_record(), now=NOW)
        assert upsert_rule(rule, rules_file=f) == "created"
        assert upsert_rule(dict(rule), rules_file=f) == "unchanged"
        rules = load_rules(f)
        assert len(rules) == 1
        assert rules[0]["created_at"] == rules[0]["updated_at"]  # unchanged pass never rewrites

    def test_update_changes_payload_and_keeps_created_at(self, tmp_path: Path):
        f = tmp_path / "rules.json"
        upsert_rule(build_freshness_rule(_record(), now=NOW), rules_file=f)
        before = load_rules(f)[0]
        assert upsert_rule(build_freshness_rule(_record(age_hours=31.0), now=NOW), rules_file=f) == "updated"
        after = load_rules(f)
        assert len(after) == 1
        assert after[0]["created_at"] == before["created_at"]
        assert after[0]["description"].endswith("(31h)")

    def test_upsert_never_duplicates_and_keeps_manual_rules(self, tmp_path: Path):
        f = tmp_path / "rules.json"
        f.write_text(json.dumps([{"id": "manual", "name": "Manual", "active": True}]), encoding="utf-8")
        for _ in range(3):
            upsert_rule(build_freshness_rule(_record(), now=NOW), rules_file=f)
        assert sorted(r["id"] for r in load_rules(f)) == ["data_freshness_t", "manual"]


class TestResolveRule:
    """Resolve (clear) semantics."""

    def test_removes_only_target(self, tmp_path: Path):
        f = tmp_path / "rules.json"
        f.write_text(json.dumps([{"id": "a"}, {"id": "data_freshness_t"}, {"id": "b"}]), encoding="utf-8")
        assert resolve_rule("data_freshness_t", rules_file=f) is True
        assert [r["id"] for r in load_rules(f)] == ["a", "b"]

    def test_absent_id_is_false(self, tmp_path: Path):
        f = tmp_path / "rules.json"
        f.write_text(json.dumps([{"id": "a"}]), encoding="utf-8")
        assert resolve_rule("nope", rules_file=f) is False
        assert resolve_rule("nope", rules_file=tmp_path / "nope.json") is False


class TestSyncFreshnessRules:
    """Full summary -> store sync."""

    def test_raise_idempotent_recover_lifecycle(self, tmp_path: Path):
        f = tmp_path / "rules.json"
        stale_summary = _summary(_record(), _record(key="ok", label="OK", status="fresh", age_hours=1.0))

        assert sync_freshness_rules(stale_summary, rules_file=f, now=NOW) == {"created": 1, "updated": 0, "unchanged": 0, "resolved": 0}
        assert sync_freshness_rules(stale_summary, rules_file=f, now=NOW)["unchanged"] == 1  # idempotent re-check

        recovered = _summary(_record(status="fresh", age_hours=1.0), _record(key="ok", label="OK", status="fresh", age_hours=1.0))
        assert sync_freshness_rules(recovered, rules_file=f, now=NOW)["resolved"] == 1
        assert load_rules(f) == []

    def test_all_fresh_leaves_store_untouched(self, tmp_path: Path):
        f = tmp_path / "rules.json"
        fresh = _summary(_record(status="fresh", age_hours=1.0))
        assert sync_freshness_rules(fresh, rules_file=f, now=NOW) == {"created": 0, "updated": 0, "unchanged": 0, "resolved": 0}
        assert not f.exists()

    def test_deregistered_source_gets_cleaned_up(self, tmp_path: Path):
        f = tmp_path / "rules.json"
        sync_freshness_rules(_summary(_record(key="gone")), rules_file=f, now=NOW)
        assert len(load_rules(f)) == 1
        sync_freshness_rules(_summary(_record(key="other", label="Other")), rules_file=f, now=NOW)
        assert [r["id"] for r in load_rules(f)] == ["data_freshness_other"]


def _stack_match(repo="n8n-io/n8n", label="n8n", cve="CVE-2026-1234", product="n8n", ransomware="Known"):
    """Build one stack match group as produced by match_stack_to_kev."""
    return {
        "repo": repo,
        "service_label": label,
        "cves": [{"cve": cve, "product": product, "dateAdded": "2026-08-26", "title": f"🔴 {cve} — {product}", "ransomware": ransomware}],
    }


class TestBuildStackCveRule:
    """Stack CVE rule construction and id stability."""

    def test_rule_shape_and_message(self):
        rule = build_stack_cve_rule("home-assistant/core", "home-assistant", "CVE-2026-1234", product="HASSIO", date_added="2026-08-20", ransomware="Known")
        assert rule["id"] == "stack_cve_home-assistant_core_cve-2026-1234"
        assert rule["name"] == "Stack CVE: home-assistant"
        assert rule["description"] == "CVE CVE-2026-1234 explotado activamente afecta a home-assistant"
        assert rule["severity"] == "high"
        assert rule["source"] == "stack_cves" and rule["auto_managed"] is True and rule["active"] is True

    def test_rule_id_normalizes_repo_slug_and_cve_case(self):
        assert stack_cve_rule_id("JustArchiNET/ArchiSteamFarm", "CVE-2025-9276") == "stack_cve_justarchinet_archisteamfarm_cve-2025-9276"
        assert stack_cve_rule_id("n8n-io/n8n", "cve-2026-1234") == stack_cve_rule_id("n8n-io/n8n", "CVE-2026-1234")


class TestSyncStackCveRules:
    """Stack match -> store sync: raise, idempotence, resolve on aging out."""

    def test_raise_idempotent_resolve_lifecycle(self, tmp_path: Path):
        f = tmp_path / "rules.json"
        matches = [_stack_match(), _stack_match(repo="jellyfin/jellyfin", label="jellyfin", cve="CVE-2026-2222", product="JellyFin")]

        assert sync_stack_cve_rules(matches, rules_file=f) == {"created": 2, "updated": 0, "unchanged": 0, "resolved": 0}
        assert sync_stack_cve_rules(matches, rules_file=f)["unchanged"] == 2  # idempotent re-check
        assert len(load_rules(f)) == 2

        # One CVE ages out of the KEV window -> only that rule resolves.
        surviving = [matches[0]]
        assert sync_stack_cve_rules(surviving, rules_file=f)["resolved"] == 1
        assert [r["id"] for r in load_rules(f)] == ["stack_cve_n8n-io_n8n_cve-2026-1234"]

        # All clear -> store empty again.
        assert sync_stack_cve_rules([], rules_file=f)["resolved"] == 1
        assert load_rules(f) == []

    def test_freshness_sync_and_stack_sync_coexist(self, tmp_path: Path):
        f = tmp_path / "rules.json"
        sync_freshness_rules(_summary(_record()), rules_file=f, now=NOW)
        sync_stack_cve_rules([_stack_match()], rules_file=f)
        # Neither cleanup touches the other namespace.
        sync_freshness_rules(_summary(_record(status="fresh", age_hours=1.0)), rules_file=f, now=NOW)
        assert [r["id"] for r in load_rules(f)] == ["stack_cve_n8n-io_n8n_cve-2026-1234"]
        sync_stack_cve_rules([], rules_file=f)
        assert load_rules(f) == []

    def test_manual_rules_never_touched(self, tmp_path: Path):
        f = tmp_path / "rules.json"
        manual = [{"id": "manual", "name": "Manual", "active": True}, {"id": "data_freshness_t", "name": "Freshness", "active": True}]
        f.write_text(json.dumps(manual), encoding="utf-8")
        sync_stack_cve_rules([_stack_match()], rules_file=f)
        sync_stack_cve_rules([], rules_file=f)
        assert load_rules(f) == manual  # non-stack namespaces survive both syncs

    def test_new_cve_for_same_repo_gets_its_own_rule(self, tmp_path: Path):
        f = tmp_path / "rules.json"
        first = _stack_match(cve="CVE-2026-0001")
        both = [_stack_match(cve="CVE-2026-0001"), _stack_match(cve="CVE-2026-0002")]
        sync_stack_cve_rules([first], rules_file=f)
        sync_stack_cve_rules(both, rules_file=f)  # new CVE joins, old one still matched
        assert sorted(r["id"] for r in load_rules(f)) == ["stack_cve_n8n-io_n8n_cve-2026-0001", "stack_cve_n8n-io_n8n_cve-2026-0002"]


class TestStackEolRules:
    """Stack-product EOL rules (T-092): HIGH inside the 90-day horizon."""

    def test_eol_soon_gets_high_rule(self, tmp_path: Path):
        from src.alerts.rules_store import sync_stack_eol_rules

        f = tmp_path / "rules.json"
        products = [{"product": "debian", "label": "Debian", "tracked": True, "days_to_eol": 30, "nearest_eol": "2026-10-10"}]
        counts = sync_stack_eol_rules(products, rules_file=f, today=__import__("datetime").date(2026, 9, 10))
        assert counts["created"] == 1
        rule = load_rules(f)[0]
        assert rule["id"] == "stack_eol_debian"
        assert rule["severity"] == "high"
        assert "30 días" in rule["description"]

    def test_eol_far_no_rule_and_back_in_clear_resolves(self, tmp_path: Path):
        from datetime import date as _date

        from src.alerts.rules_store import sync_stack_eol_rules

        f = tmp_path / "rules.json"
        today = _date(2026, 9, 10)
        near = [{"product": "debian", "label": "Debian", "tracked": True, "days_to_eol": 30, "nearest_eol": "2026-10-10"}]
        far = [{"product": "debian", "label": "Debian", "tracked": True, "days_to_eol": 600, "nearest_eol": "2028-05-01"}]
        sync_stack_eol_rules(near, rules_file=f, today=today)
        assert sync_stack_eol_rules(far, rules_file=f, today=today)["resolved"] == 1
        assert load_rules(f) == []

    def test_past_eol_and_untracked_ignored(self, tmp_path: Path):
        from datetime import date as _date

        from src.alerts.rules_store import sync_stack_eol_rules

        f = tmp_path / "rules.json"
        products = [
            {"product": "n8n", "label": "n8n", "tracked": False},  # endoflife.date doesn't track it
            {"product": "old", "label": "Old", "tracked": True, "days_to_eol": -5, "nearest_eol": "2026-09-05"},
        ]
        sync_stack_eol_rules(products, rules_file=f, today=_date(2026, 9, 10))
        rules = load_rules(f)
        assert len(rules) == 1  # only the past-EOL product rules; untracked never
        assert "ya sin soporte" in rules[0]["description"]
