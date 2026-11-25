"""Unit tests for the spec-13 TR-F2 momentum panel (T-048).

Covers the pure momentum core (weekly mentions vs the 4-week moving average,
thresholds, coverage-aware baseline, ranked Subiendo/Bajando shortlists), the
week bucketing helpers, the snapshot scan over timestamped M5 files (with
per-week article de-duplication and window gating) and the rendered panel's
sufficient/insufficient-history states. All fixtures are inline (tmp_path);
no network, no real data/ reads.
"""

import json
from datetime import datetime

import pytest

from src.web.dashboard.components import tech_radar_tab as tab

# Fixture calendar: Mondays spanning the 5-week momentum window.
W1, W2, W3, W4, W5 = "2026-08-03", "2026-08-10", "2026-08-17", "2026-08-24", "2026-08-31"


def _write(tmp_path, rel, articles):
    target = tmp_path / "data" / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(articles), encoding="utf-8")


def _articles(tech, n, week):
    """n distinct articles mentioning ``tech`` (unique links, tech in title)."""
    return [{"title": f"{tech} story {week} {i}", "link": f"https://x/{week}/{tech}/{i}", "published": f"{week}T10:00:00+00:00"} for i in range(n)]


def _snapshot_file(week, hhmmss="120000"):
    """Timestamped snapshot filename for a Monday week key."""
    return f"news/google_ai_blog_{week.replace('-', '')}_{hhmmss}.json"


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_MOMENTUM_CACHE", tab.TTLDataCache(ttl_seconds=60))


# ---------------------------------------------------------------------------
# Week bucketing helpers
# ---------------------------------------------------------------------------


def test_week_start_snaps_to_monday():
    assert tab._week_start(datetime(2026, 11, 25)) == "2026-11-23"  # Wednesday -> Monday
    assert tab._week_start(datetime(2026, 8, 31)) == "2026-08-31"  # already Monday


def test_week_label_is_compact_spanish():
    assert tab._week_label("2026-08-24") == "24 ago"
    assert tab._week_label("2026-11-23") == "23 nov"
    assert tab._week_label("not-a-date") == "not-a-date"  # graceful passthrough


def test_momentum_snapshot_targets_derive_dir_and_prefix():
    targets = {prefix: dir_rel for dir_rel, prefix in tab._momentum_snapshot_targets()}
    assert targets["google_ai_blog"] == "news"  # latest file -> bare prefix
    assert targets["kdnuggets"] == "kdnuggets"  # live non-latest file keeps its stem
    assert targets["stack_releases"] == "github"  # multi-file source (mi_stack)
    assert len(tab._momentum_snapshot_targets()) == len(set(tab._momentum_snapshot_targets()))


# ---------------------------------------------------------------------------
# compute_momentum (pure core)
# ---------------------------------------------------------------------------


def test_compute_momentum_classifies_rising_falling_flat_new():
    weeks = [W1, W2, W3, W4, W5]
    counts = {
        "docker": [10, 10, 10, 10, 14],  # baseline 10 -> +40% rising
        "rust": [10, 10, 10, 10, 5],  # baseline 10 -> -50% falling
        "golang": [10, 10, 10, 10, 11],  # baseline 10 -> +10% flat (inside ±20%)
        "llama": [0, 0, 0, 0, 5],  # zero baseline -> "new", no % delta
        "k8s": [10, 10, 10, 10, 10],  # 0% flat
    }
    records = {r["tech"]: r for r in tab.compute_momentum(weeks, counts)}
    assert records["docker"]["direction"] == "rising" and records["docker"]["delta_pct"] == 40.0
    assert records["rust"]["direction"] == "falling" and records["rust"]["delta_pct"] == -50.0
    assert records["golang"]["direction"] == "flat"
    assert records["llama"]["direction"] == "new" and records["llama"]["delta_pct"] is None
    assert records["k8s"]["direction"] == "flat" and records["k8s"]["delta_pct"] == 0.0
    assert records["docker"]["baseline_weeks"] == 4 and records["docker"]["baseline"] == 10.0


def test_compute_momentum_noise_floor_and_low_baseline_guard():
    weeks = [W1, W2, W3, W4, W5]
    records = {r["tech"]: r for r in tab.compute_momentum(weeks, {"vue": [0, 0, 0, 1, 1], "svelte": [0, 0, 0, 1, 4]})}
    assert "vue" not in records  # window_total 2 < MOMENTUM_MIN_MENTIONS (3)
    assert records["svelte"]["direction"] == "flat"  # +300% but baseline 1 < 2.0: noise, not momentum


def test_compute_momentum_vanishing_tech_is_a_faller():
    records = tab.compute_momentum([W1, W2, W3, W4, W5], {"traefik": [5, 5, 5, 5, 0]})
    assert records[0]["direction"] == "falling" and records[0]["delta_pct"] == -100.0


def test_compute_momentum_coverage_aware_baseline_ignores_empty_slots():
    weeks = [W1, W2, W3, W4, W5]
    counts = {"docker": [0, 0, 0, 2, 6]}
    # Weeks W1-W3 have no snapshots at all: the baseline uses only covered slots
    # (week W4 -> mean 2.0), so +200% is read as momentum, not diluted to +20%.
    covered = tab.compute_momentum(weeks, counts, coverage=[False, False, False, True, True])
    assert covered[0]["direction"] == "rising" and covered[0]["baseline"] == 2.0 and covered[0]["baseline_weeks"] == 1
    # Without coverage info every slot counts (mean 0.5 < min baseline) -> flat.
    uncovered = tab.compute_momentum(weeks, counts)
    assert uncovered[0]["direction"] == "flat"


def test_compute_momentum_pads_and_truncates_series():
    # Shorter than weeks -> zero-padded on the left: [4, 8] -> [0, 4, 8];
    # the 4-week baseline spans both previous slots -> mean(0, 4) = 2.0.
    padded = tab.compute_momentum([W1, W2, W3], {"nginx": [4, 8]})
    assert padded[0]["current"] == 8 and padded[0]["baseline"] == 2.0 and padded[0]["direction"] == "rising"
    # Longer than weeks -> truncated to the last 3 slots.
    truncated = tab.compute_momentum([W1, W2, W3], {"nginx": [99, 99, 4, 4, 8]})
    assert truncated[0]["current"] == 8 and truncated[0]["baseline"] == 4.0
    # No weeks -> no records.
    assert tab.compute_momentum([], {"nginx": [1]}) == []


def test_momentum_lists_rank_and_cap():
    records = [
        {"tech": "flat", "direction": "flat", "delta_pct": 5.0, "current": 3},
        {"tech": "new-entry", "direction": "new", "delta_pct": None, "current": 5},
        {"tech": "small-rise", "direction": "rising", "delta_pct": 40.0, "current": 7},
        {"tech": "big-rise", "direction": "rising", "delta_pct": 150.0, "current": 4},
        {"tech": "small-drop", "direction": "falling", "delta_pct": -30.0, "current": 2},
        {"tech": "big-drop", "direction": "falling", "delta_pct": -80.0, "current": 1},
    ]
    risers, fallers = tab._momentum_lists(records, top_n=2)
    assert [r["tech"] for r in risers] == ["new-entry", "big-rise"]  # new first, then biggest %
    assert [r["tech"] for r in fallers] == ["big-drop", "small-drop"]  # steepest drop first
    full_risers, full_fallers = tab._momentum_lists(records)  # default cap shows all
    assert len(full_risers) == 3 and len(full_fallers) == 2


# ---------------------------------------------------------------------------
# Snapshot scan (timestamped M5 files)
# ---------------------------------------------------------------------------


def test_scan_counts_mentions_per_week_with_dedup_and_window_gate(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    # Week W4: 2 unique docker articles; the third is a duplicated link from a
    # daily re-run and must be counted once.
    _write(tmp_path, _snapshot_file(W4), _articles("docker", 1, W4) + [{"title": "docker dup run", "link": "https://x/x-run-dup"}] * 2)
    # Week W5: 3 docker + 1 rust.
    _write(tmp_path, _snapshot_file(W5), _articles("docker", 3, W5) + _articles("rust", 1, W5))
    # Older than the 5-week window (ref W5): never read.
    _write(tmp_path, _snapshot_file("2026-07-13"), _articles("kubernetes", 1, "2026-07-13"))
    # latest file + the KDNuggets live file are NOT snapshots — ignored.
    _write(tmp_path, "news/google_ai_blog_latest.json", _articles("kubernetes", 1, W5))
    _write(tmp_path, "kdnuggets/kdnuggets.json", _articles("kubernetes", 1, W5))
    # A real kdnuggets snapshot counts (separate source prefix, own dedup scope).
    _write(tmp_path, f"kdnuggets/kdnuggets_{W4.replace('-', '')}_090000.json", _articles("python", 1, W4))

    series = tab._load_momentum_series()
    assert series["weeks"] == [W1, W2, W3, W4, W5]
    assert series["coverage"] == [False, False, False, True, True] and series["weeks_with_data"] == 2
    assert series["counts"]["docker"] == [0, 0, 0, 2, 3]
    assert series["counts"]["rust"] == [0, 0, 0, 0, 1]
    assert series["counts"]["python"] == [0, 0, 0, 1, 0]
    assert "kubernetes" not in series["counts"]  # only present in ignored files


def test_scan_without_snapshots_returns_empty_series(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _write(tmp_path, "news/google_ai_blog_latest.json", [{"title": "docker story"}])  # latest only, no snapshots
    series = tab._load_momentum_series()
    assert series == {"weeks": [], "counts": {}, "coverage": [], "weeks_with_data": 0}


# ---------------------------------------------------------------------------
# Rendered panel
# ---------------------------------------------------------------------------


def _write_three_week_rise_and_fall(tmp_path):
    _write(tmp_path, _snapshot_file(W3), _articles("docker", 2, W3) + _articles("rust", 6, W3))
    _write(tmp_path, _snapshot_file(W4), _articles("docker", 2, W4) + _articles("rust", 2, W4) + _articles("python", 3, W4))
    _write(tmp_path, _snapshot_file(W5), _articles("docker", 6, W5) + _articles("rust", 1, W5) + _articles("python", 3, W5))


def test_panel_renders_risers_and_fallers(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _write_three_week_rise_and_fall(tmp_path)
    panel = str(tab._render_momentum_panel())
    assert "📈 Momentum por tecnología" in panel and "🔺 Subiendo" in panel and "🔻 Bajando" in panel
    assert "+200%" in panel and "docker" in panel  # docker 6 vs baseline 2.0
    assert "-75%" in panel and "rust" in panel  # rust 1 vs baseline 4.0
    assert "python" not in panel  # 0->3->3 has a 1.5 low-signal baseline -> flat, hidden
    assert "Semana del 31 ago" in panel and "3 de 5 semanas con snapshots" in panel


def test_panel_without_enough_history_shows_insufficient_notice(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _write(tmp_path, _snapshot_file(W5), _articles("docker", 6, W5))  # single week only
    panel = str(tab._render_momentum_panel())
    assert "Sin historia suficiente" in panel and "1 semana(s)" in panel
    assert "Subiendo" not in panel and "Bajando" not in panel


def test_panel_with_no_snapshots_shows_insufficient_notice(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    panel = str(tab._render_momentum_panel())
    assert "Sin historia suficiente" in panel and "0 semana(s)" in panel


@pytest.mark.parametrize("covered_weeks", [1, 2, 3, 4, 5])
def test_panel_history_threshold_is_two_weeks(tmp_path, monkeypatch, covered_weeks):
    _isolate(tmp_path, monkeypatch)
    weeks = [W1, W2, W3, W4, W5][-covered_weeks:]
    for week in weeks:
        _write(tmp_path, _snapshot_file(week), _articles("docker", 4, week))
    panel = str(tab._render_momentum_panel())
    if covered_weeks >= tab.MOMENTUM_MIN_HISTORY_WEEKS:
        assert "Sin historia suficiente" not in panel
        assert f"{covered_weeks} de 5 semanas" in panel
    else:
        assert "Sin historia suficiente" in panel
