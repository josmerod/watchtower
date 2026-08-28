"""Tests for the LiveBench leaderboard ETL (src/etl/benchmarks/livebench_etl.py).

All parsing tests run against fixture payloads captured from the real site —
no live network access.
"""

import json
from pathlib import Path

import pytest

from src.etl.benchmarks.livebench_etl import (
    COST_KEY,
    _norm_category,
    parse_cost,
    parse_leaderboard,
    parse_score,
    run,
    save_json,
)

# Real DOM rows captured from https://livebench.ai/ (release 2026-06-25),
# trimmed to a representative subset. Column 0 is the row expander.
FIXTURE_ROWS = [
    ["", "MODEL", "OVERALL\n▼", "REASONING", "CODING", "AGENTIC CODING", "MATHEMATICS", "DATA ANALYSIS", "LANGUAGE", "INSTRUCTION FOLLOWING", "COST PER\nSUCCESSFUL\u00a0TASK"],
    ["▸", "Claude Fable 5 Max Effort", "83.0", "89.7", "86.0", "62.2", "96.0", "80.5", "90.7", "75.8", "$1.439"],
    ["▸", "GPT-5.6 Sol Max Effort", "81.0", "91.7", "83.9", "56.2", "96.2", "79.8", "87.7", "71.8", "$0.515"],
    ["▸", "GPT-5.5 Thinking xHigh Effort", "80.2", "89.7", "82.1", "54.0", "95.9", "81.6", "87.4", "70.7", "$0.435"],
]

FIXTURE_PAYLOAD = {"release": "2026-06-25", "rows": FIXTURE_ROWS}


class TestNormCategory:
    """Header normalization."""

    def test_plain_category(self):
        assert _norm_category("REASONING") == "reasoning"

    def test_multi_word_with_arrow_and_newline(self):
        assert _norm_category("OVERALL\n▼") == "overall"
        assert _norm_category("AGENTIC CODING") == "agentic_coding"

    def test_cost_header_multiline(self):
        assert _norm_category("COST PER\nSUCCESSFUL\u00a0TASK") == "cost_per_successful_task"

    def test_empty_header(self):
        assert _norm_category("") == ""
        assert _norm_category("  ") == ""


class TestParsers:
    """Score and cost cell parsing."""

    def test_parse_score_valid(self):
        assert parse_score("83.0") == 83.0
        assert parse_score(" 1,234 ") == 1234.0

    def test_parse_score_invalid(self):
        assert parse_score("—") is None
        assert parse_score(None) is None

    def test_parse_cost_dollar(self):
        assert parse_cost("$1.439") == 1.439

    def test_parse_cost_invalid(self):
        assert parse_cost("—") is None
        assert parse_cost(None) is None


class TestParseLeaderboard:
    """Fixture-payload parsing into the persisted schema."""

    @pytest.fixture
    def result(self):
        parsed = parse_leaderboard(FIXTURE_PAYLOAD)
        assert parsed is not None
        return parsed

    def test_metadata_fields(self, result):
        assert result["source"] == "livebench.ai"
        assert result["release"] == "2026-06-25"
        assert result["models_count"] == 3
        assert "fetched_at" in result

    def test_categories_exclude_model_and_cost(self, result):
        assert result["categories"] == ["overall", "reasoning", "coding", "agentic_coding", "mathematics", "data_analysis", "language", "instruction_following"]
        assert COST_KEY not in result["categories"]

    def test_model_scores(self, result):
        top = result["models"][0]
        assert top["rank"] == 1
        assert top["model"] == "Claude Fable 5 Max Effort"
        assert top["overall"] == 83.0
        assert top["agentic_coding"] == 62.2
        assert top[COST_KEY] == pytest.approx(1.439)

    def test_rows_without_overall_are_skipped(self):
        payload = {
            "release": "2026-06-25",
            "rows": [
                FIXTURE_ROWS[0],
                ["▸", "Broken Model", "", "50.0", "", "", "", "", "", "", ""],
                ["▸", "Good Model", "70.0", "50.0", "", "", "", "", "", "", "$0.1"],
            ],
        }
        parsed = parse_leaderboard(payload)
        assert parsed is not None
        assert parsed["models_count"] == 1
        assert parsed["models"][0]["model"] == "Good Model"

    def test_empty_payload_returns_none(self):
        assert parse_leaderboard({"release": None, "rows": []}) is None
        assert parse_leaderboard({"release": None, "rows": [FIXTURE_ROWS[0]]}) is None


class TestSaveAndRun:
    """File persistence and last-good behaviour."""

    def test_save_json_roundtrip(self, tmp_path, monkeypatch):
        from src.etl.benchmarks import livebench_etl

        monkeypatch.setattr(livebench_etl, "get_data_dir", lambda: tmp_path)
        data = parse_leaderboard(FIXTURE_PAYLOAD)
        out = save_json(data, "livebench_latest.json")
        assert out == tmp_path / "livebench_latest.json"
        loaded = json.loads(out.read_text(encoding="utf-8"))
        assert loaded["models_count"] == 3

    def test_run_failure_keeps_last_good(self, tmp_path, monkeypatch):
        from src.etl.benchmarks import livebench_etl

        monkeypatch.setattr(livebench_etl, "get_data_dir", lambda: tmp_path)
        sentinel = tmp_path / "livebench_latest.json"
        sentinel.write_text('{"models_count": 42}', encoding="utf-8")
        monkeypatch.setattr(livebench_etl, "fetch_livebench_data", lambda max_retries=3: None)
        run()
        assert json.loads(sentinel.read_text(encoding="utf-8"))["models_count"] == 42
