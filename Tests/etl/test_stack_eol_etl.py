"""Tests for the mi-stack EOL radar ETL (src/etl/github/stack_eol_etl.py).

All parsing/normalization tests run against fixture payloads captured from
https://endoflife.date/api/v1/products/{slug} (2026-09-10, trimmed to a
representative subset) — no live network access. Day math freezes "today" at
2026-09-10 so the expected deltas are stable:

    python 3.14 eol 2030-10-31 -> +1512d   python 3.13 eol 2029-10-31 -> +1147d
    ubuntu 26.04 eol 2031-05-29 -> +1722d  ubuntu 25.10 eol 2026-07-01 -> -71d (past)
    debian 13 eol 2030-06-30 -> +1383d     debian 12 eol 2028-06-30 -> +659d
"""

import json
from datetime import date

import pytest
import requests

from src.etl.github.stack_eol_etl import (
    MAX_CYCLES_PER_PRODUCT,
    STACK_EOL_PRODUCTS,
    days_until,
    eol_badge,
    fetch_stack_eol,
    nearest_eol,
    normalize_cycles,
    normalize_product,
    parse_iso_date,
    save_stack_eol,
)

NOW = date(2026, 9, 10)

# Captured from https://endoflife.date/api/v1/products/python (2026-09-10),
# trimmed to 3 cycles — enough to prove only the 2 newest are kept.
PYTHON_V1 = {
    "schema_version": "1.2.1",
    "generated_at": "2026-09-10T08:47:46+00:00",
    "result": {
        "name": "python",
        "label": "Python",
        "category": "lang",
        "releases": [
            {
                "name": "3.14",
                "codename": None,
                "label": "3.14",
                "releaseDate": "2025-10-07",
                "isLts": False,
                "ltsFrom": None,
                "isEoas": False,
                "eoasFrom": "2027-10-01",
                "isEol": False,
                "eolFrom": "2030-10-31",
                "isMaintained": True,
                "latest": {"name": "3.14.7", "date": "2026-08-05", "link": "https://www.python.org/downloads/release/python-3147/"},
                "custom": {"pep": "PEP-0745"},
            },
            {
                "name": "3.13",
                "codename": None,
                "label": "3.13",
                "releaseDate": "2024-10-07",
                "isLts": False,
                "ltsFrom": None,
                "isEoas": False,
                "eoasFrom": "2026-10-01",
                "isEol": False,
                "eolFrom": "2029-10-31",
                "isMaintained": True,
                "latest": {"name": "3.13.15", "date": "2026-08-05", "link": "https://www.python.org/downloads/release/python-31315/"},
            },
            {
                "name": "3.12",
                "codename": None,
                "label": "3.12",
                "releaseDate": "2023-10-02",
                "isLts": False,
                "ltsFrom": None,
                "eoasFrom": "2025-04-02",
                "eolFrom": "2028-10-31",
                "isMaintained": True,
                "latest": {"name": "3.12.14", "date": "2026-08-12", "link": "https://www.python.org/downloads/release/python-31214/"},
            },
        ],
    },
}

# Captured from https://endoflife.date/api/v1/products/ubuntu (2026-09-10):
# the newest cycle is fine until 2031 but the interim 25.10 cycle is already
# past EOL — the "nearest EOL" logic must prefer the future date.
UBUNTU_V1 = {
    "result": {
        "name": "ubuntu",
        "label": "Ubuntu",
        "releases": [
            {
                "name": "26.04",
                "codename": "Resolute Raccoon",
                "label": "26.04 'Resolute Raccoon' (LTS)",
                "releaseDate": "2026-04-23",
                "isLts": True,
                "ltsFrom": None,
                "eoasFrom": "2031-05-29",
                "eolFrom": "2031-05-29",
                "isMaintained": True,
                "latest": {"name": "26.04.1", "date": "2026-08-31", "link": "https://wiki.ubuntu.com/ResoluteRaccoon/ReleaseNotes/"},
            },
            {
                "name": "25.10",
                "codename": "Questing Quokka",
                "label": "25.10 'Questing Quokka'",
                "releaseDate": "2025-10-09",
                "isLts": False,
                "ltsFrom": None,
                "eoasFrom": "2026-07-01",
                "eolFrom": "2026-07-01",
                "isMaintained": False,
                "latest": {"name": "25.10", "date": "2025-10-09", "link": "https://wiki.ubuntu.com/QuestingQuokka/ReleaseNotes/"},
            },
            {
                "name": "25.04",
                "codename": "Plucky Puffin",
                "label": "25.04 'Plucky Puffin'",
                "releaseDate": "2025-04-17",
                "isLts": False,
                "eoasFrom": "2026-01-17",
                "eolFrom": "2026-01-17",
                "isMaintained": False,
                "latest": {"name": "25.04", "date": "2025-04-17"},
            },
        ],
    },
}


class TestParseIsoDate:
    """API date-field coercion."""

    def test_valid(self):
        assert parse_iso_date("2030-06-30") == "2030-06-30"

    def test_invalid_values(self):
        assert parse_iso_date(None) is None
        assert parse_iso_date(False) is None
        assert parse_iso_date(True) is None
        assert parse_iso_date("soon") is None
        assert parse_iso_date("") is None


class TestDaysUntil:
    """Day-delta math against a frozen reference date."""

    def test_future_and_past(self):
        assert days_until("2030-06-30", NOW) == 1389
        assert days_until("2026-07-01", NOW) == -71

    def test_unknown(self):
        assert days_until(None, NOW) is None
        assert days_until("garbage", NOW) is None


class TestNormalizeCycles:
    """v1 release-cycle normalization."""

    def test_keeps_two_newest_only(self):
        cycles = normalize_cycles(PYTHON_V1["result"]["releases"], NOW)
        assert len(cycles) == MAX_CYCLES_PER_PRODUCT == 2
        assert [c["cycle"] for c in cycles] == ["3.14", "3.13"]  # 3.12 dropped

    def test_field_mapping(self):
        cycle = normalize_cycles(PYTHON_V1["result"]["releases"], NOW)[0]
        assert cycle["cycle"] == "3.14"
        assert cycle["release_name"] == "3.14"
        assert cycle["release_date"] == "2025-10-07"
        assert cycle["latest_release"] == "3.14.7"
        assert cycle["latest_release_date"] == "2026-08-05"
        assert cycle["eol"] == "2030-10-31"
        assert cycle["support"] == "2027-10-01"  # v1 eoasFrom
        assert cycle["lts_from"] is None
        assert cycle["is_lts"] is False
        assert cycle["is_maintained"] is True
        assert cycle["days_to_eol"] == 1512

    def test_unordered_input_is_sorted_by_release_date(self):
        releases = list(reversed(PYTHON_V1["result"]["releases"]))
        assert [c["cycle"] for c in normalize_cycles(releases, NOW)] == ["3.14", "3.13"]

    def test_degenerate_cycle_fields(self):
        cycles = normalize_cycles([{"name": "nightly", "releaseDate": "2026-01-01", "eolFrom": None, "latest": None}], NOW)
        assert cycles[0]["latest_release"] == ""
        assert cycles[0]["latest_release_date"] is None
        assert cycles[0]["eol"] is None
        assert cycles[0]["days_to_eol"] is None


class TestNearestEol:
    """Most-actionable EOL selection across a product's kept cycles."""

    def test_prefers_soonest_future_over_past(self):
        """Ubuntu 26.04 (2031) must win over the already-EOL 25.10 (2026-07)."""
        cycles = normalize_cycles(UBUNTU_V1["result"]["releases"], NOW)
        assert nearest_eol(cycles, NOW) == ("2031-05-29", 1722)

    def test_all_past_takes_most_recent(self):
        cycles = [
            {"eol": "2026-07-01"},
            {"eol": "2026-08-31"},
        ]
        assert nearest_eol(cycles, NOW) == ("2026-08-31", -10)

    def test_no_dates(self):
        assert nearest_eol([{"eol": None}, {}], NOW) == (None, None)
        assert nearest_eol([], NOW) == (None, None)


class TestNormalizeProduct:
    """Full v1 envelope to persisted product record."""

    def test_python_record(self):
        record = normalize_product(PYTHON_V1, {"product": "python", "label": "Python", "role": "adjacent"}, NOW)
        assert record["product"] == "python"
        assert record["label"] == "Python"
        assert record["tracked"] is True
        assert len(record["cycles"]) == 2
        # 3.13's 2029-10-31 is the sooner future EOL of the two kept cycles.
        assert record["nearest_eol"] == "2029-10-31"
        assert record["days_to_eol"] == 1147

    def test_label_falls_back_to_registry(self):
        payload = {"result": {"releases": []}}
        record = normalize_product(payload, {"product": "debian", "label": "Debian", "role": "adjacent"}, NOW)
        assert record["label"] == "Debian"
        assert record["cycles"] == []
        assert record["nearest_eol"] is None
        assert record["days_to_eol"] is None


class TestEolBadge:
    """Badge-tier mapping: red <90d/past, orange <180d, white fine/no date, dash untracked."""

    @pytest.mark.parametrize(
        "days,expected",
        [(-71, ("🔴", "critical")), (-1, ("🔴", "critical")), (0, ("🔴", "critical")), (89, ("🔴", "critical")), (90, ("🟠", "expiring")), (179, ("🟠", "expiring")), (180, ("⚪", "ok")), (1722, ("⚪", "ok"))],
    )
    def test_tracked_days(self, days, expected):
        assert eol_badge({"tracked": True, "days_to_eol": days}) == expected

    def test_tracked_no_date_is_ok(self):
        assert eol_badge({"tracked": True, "days_to_eol": None}) == ("⚪", "ok")

    def test_untracked(self):
        assert eol_badge({"tracked": False, "days_to_eol": None}) == ("➖", "untracked")
        assert eol_badge({}) == ("➖", "untracked")


class TestFetchStackEol:
    """Per-product resilience and zero-network untracked entries."""

    @pytest.fixture
    def fetched(self, monkeypatch):
        """Patch the HTTP fetcher with canned payloads; record every call."""
        from src.etl.github import stack_eol_etl as etl

        calls: list[str] = []

        def _fake(product):
            calls.append(product)
            if product == "python":
                raise requests.RequestException("boom")
            return {"debian": {"result": {"label": "Debian", "releases": PYTHON_V1["result"]["releases"]}}, "ubuntu": UBUNTU_V1}[product]

        monkeypatch.setattr(etl, "_fetch_product", _fake)
        monkeypatch.setattr(etl.time, "sleep", lambda _s: None)
        products, stats = fetch_stack_eol(now=NOW)
        return products, stats, calls

    def test_untracked_services_never_hit_the_network(self, fetched):
        _products, _stats, calls = fetched
        # Only the fetchable adjacents are requested — the six mi-stack
        # services (fetch: False) must never touch the API.
        assert set(calls) == {"debian", "ubuntu", "python"}
        untracked = {cfg["product"] for cfg in STACK_EOL_PRODUCTS if not cfg.get("fetch")}
        assert untracked and not (untracked & set(calls))

    def test_failure_isolated_per_product(self, fetched):
        products, stats, _calls = fetched
        by_slug = {p["product"]: p for p in products}
        assert len(products) == 9  # full registry emitted regardless
        assert stats["products_ok"] == 2
        assert "python" in stats["errors"]
        failed = by_slug["python"]
        assert failed["tracked"] is True
        assert failed["cycles"] == []
        assert failed["days_to_eol"] is None
        assert "boom" in failed["error"]

    def test_untracked_records_shape(self, fetched):
        products, _stats, _calls = fetched
        n8n = next(p for p in products if p["product"] == "n8n")
        assert n8n["tracked"] is False
        assert n8n["cycles"] == []
        assert n8n["nearest_eol"] is None
        assert n8n["days_to_eol"] is None

    def test_http_404_means_untracked(self, monkeypatch):
        from types import SimpleNamespace

        from src.etl.github import stack_eol_etl as etl

        def _fake(_product):
            raise requests.HTTPError("404 Client Error", response=SimpleNamespace(status_code=404))

        monkeypatch.setattr(etl, "_fetch_product", _fake)
        monkeypatch.setattr(etl.time, "sleep", lambda _s: None)
        products, stats = fetch_stack_eol(now=NOW)
        assert stats["products_ok"] == 0
        assert all(p["tracked"] is False for p in products)
        assert all(p.get("error") == "not tracked by endoflife.date" for p in products if p.get("error"))


class TestSaveStackEol:
    """File persistence, envelope shape and last-good behaviour."""

    OK_STATS = {"products_total": 9, "products_tracked_expected": 3, "products_ok": 2, "errors": {}}

    def _products(self):
        return [
            {"product": "n8n", "label": "n8n", "role": "mi_stack", "tracked": False, "cycles": [], "nearest_eol": None, "days_to_eol": None},
            {
                "product": "debian",
                "label": "Debian",
                "role": "adjacent",
                "tracked": True,
                "cycles": [{"cycle": "13", "release_name": "13 (Trixie)", "latest_release": "13.6", "eol": "2030-06-30", "days_to_eol": 1383}],
                "nearest_eol": "2030-06-30",
                "days_to_eol": 1383,
            },
        ]

    def test_writes_envelope_snapshot_and_summary(self, tmp_path, monkeypatch):
        from src.etl.github import stack_eol_etl as etl

        monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
        assert save_stack_eol(self._products(), self.OK_STATS) is True

        latest = json.loads((tmp_path / "data" / "stack" / "eol_latest.json").read_text(encoding="utf-8"))
        assert latest["source"] == "endoflife.date"
        assert latest["generated_at"]
        assert [p["product"] for p in latest["products"]] == ["n8n", "debian"]
        for product in latest["products"]:
            assert {"product", "label", "cycles", "nearest_eol", "days_to_eol"} <= set(product)

        assert len(list((tmp_path / "data" / "stack").glob("eol_2*.json"))) == 1
        summary = json.loads((tmp_path / "data" / "stack" / "run_summary_latest.json").read_text(encoding="utf-8"))
        assert summary["etl_name"] == "stack_eol"
        assert summary["products_ok"] == 2

    def test_partial_run_keeps_last_good(self, tmp_path, monkeypatch):
        from src.etl.github import stack_eol_etl as etl

        monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
        sentinel = tmp_path / "data" / "stack"
        sentinel.mkdir(parents=True)
        (sentinel / "eol_latest.json").write_text('{"generated_at": "sentinel"}', encoding="utf-8")

        partial = {**self.OK_STATS, "products_ok": 1}  # 1 of 3 < half
        assert save_stack_eol(self._products(), partial) is False
        none_ok = {**self.OK_STATS, "products_ok": 0}
        assert save_stack_eol(self._products(), none_ok) is False
        assert json.loads((sentinel / "eol_latest.json").read_text(encoding="utf-8"))["generated_at"] == "sentinel"


class TestMiStackEolSection:
    """Render smoke for the Tech Radar "Mi stack" EOL card (T-092)."""

    def _write_eol_file(self, tmp_path, products):
        eol_dir = tmp_path / "data" / "stack"
        eol_dir.mkdir(parents=True)
        (eol_dir / "eol_latest.json").write_text(json.dumps({"generated_at": "2026-09-10T00:00:00+00:00", "source": "endoflife.date", "products": products}), encoding="utf-8")

    def test_renders_badges_per_product(self, tmp_path, monkeypatch):
        from src.web.dashboard.components import tech_radar_tab as tab

        monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
        self._write_eol_file(
            tmp_path,
            [
                {"product": "n8n", "label": "n8n", "tracked": False, "cycles": [], "nearest_eol": None, "days_to_eol": None},
                {"product": "debian", "label": "Debian", "tracked": True, "cycles": [{"cycle": "13", "latest_release": "13.6", "eol": "2030-06-30"}], "nearest_eol": "2030-06-30", "days_to_eol": 1383},
                {"product": "ubuntu", "label": "Ubuntu", "tracked": True, "cycles": [{"cycle": "26.04", "latest_release": "26.04.1", "eol": "2026-10-15"}], "nearest_eol": "2026-10-15", "days_to_eol": 35},
            ],
        )
        rendered = str(tab._render_stack_eol_section())
        assert "n8n" in rendered and "➖" in rendered  # untracked service
        assert "Debian" in rendered and "⚪" in rendered  # fine (>180d)
        assert "Ubuntu" in rendered and "🔴" in rendered  # critical (<90d)
        assert "endoflife.date" in rendered
        assert "13.6" in rendered  # newest cycle's latest release shown

    def test_missing_file_renders_no_section(self, tmp_path, monkeypatch):
        from src.web.dashboard.components import tech_radar_tab as tab

        monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
        assert tab._render_stack_eol_section() == []

    def test_corrupt_file_renders_no_section(self, tmp_path, monkeypatch):
        from src.web.dashboard.components import tech_radar_tab as tab

        monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
        eol_dir = tmp_path / "data" / "stack"
        eol_dir.mkdir(parents=True)
        (eol_dir / "eol_latest.json").write_text("{not json", encoding="utf-8")
        assert tab._render_stack_eol_section() == []
