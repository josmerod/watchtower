"""Tests for the OpenRouter models catalog ETL (src/etl/benchmarks/openrouter_models_etl.py).

All parsing tests run against fixture payloads captured from the real API —
no live network access.
"""

import json

import pytest

from src.etl.benchmarks.openrouter_models_etl import (
    NEW_MODELS_CAP,
    diff_new_models,
    fetch_models_catalog,
    load_seen_map,
    parse_model,
    parse_price_per_mtok,
    run,
    save_json,
)

# Raw records captured from https://openrouter.ai/api/v1/models (2026-08-28),
# trimmed to a representative subset. Pricing strings are per-token USD.
RAW_CATALOG = {
    "data": [
        {
            "id": "tencent/hy4-preview",
            "name": "Tencent: Hy4 preview",
            "created": 1787897375,
            "context_length": 1048576,
            "architecture": {"modality": "text->text", "input_modalities": ["text"], "output_modalities": ["text"], "tokenizer": "Other", "instruct_type": None},
            "pricing": {"prompt": "0.000000834", "completion": "0.000002501", "input_cache_read": "0.000000042"},
            "top_provider": {"context_length": 1048576, "max_completion_tokens": 64000, "is_moderated": False},
        },
        {
            "id": "openai/gpt-5.2",
            "name": "OpenAI: GPT-5.2",
            "created": 1767225600,
            "context_length": 400000,
            "architecture": {"modality": "text->text", "input_modalities": ["text"], "output_modalities": ["text"], "tokenizer": "GPT"},
            "pricing": {"prompt": "0.00000125", "completion": "0.00001"},
            "top_provider": {"context_length": 400000, "max_completion_tokens": 128000, "is_moderated": True},
        },
        {
            "id": "meta-llama/llama-4-free",
            "name": "Meta: Llama 4 (free)",
            "created": 1759276800,
            "context_length": 131072,
            "architecture": {"modality": "text->text", "input_modalities": ["text"], "output_modalities": ["text"], "tokenizer": "Llama"},
            "pricing": {"prompt": "0", "completion": "0"},
            "top_provider": {"context_length": 131072, "max_completion_tokens": 8192, "is_moderated": False},
        },
        {
            "id": "weird/negative-price",
            "name": "Weird: Negative Price",
            "created": 1759000000,
            "context_length": None,
            "architecture": {},
            "pricing": {"prompt": "-0.000001", "completion": "bogus"},
            "top_provider": None,
        },
        {"id": "", "name": "No id model", "created": 1780000000, "pricing": {}},
    ],
}


class TestParsePricePerMtok:
    """Per-token string to per-Mtok USD conversion."""

    def test_valid_strings(self):
        assert parse_price_per_mtok("0.000000834") == pytest.approx(0.834)
        assert parse_price_per_mtok("0.000002501") == pytest.approx(2.501)
        assert parse_price_per_mtok("0.00000125") == pytest.approx(1.25)

    def test_zero_is_free(self):
        assert parse_price_per_mtok("0") == 0.0

    def test_invalid_and_negative(self):
        assert parse_price_per_mtok(None) is None
        assert parse_price_per_mtok("bogus") is None
        assert parse_price_per_mtok("-0.000001") is None


class TestParseModel:
    """Raw record normalization."""

    @pytest.fixture
    def parsed(self):
        models = [m for m in (parse_model(r) for r in RAW_CATALOG["data"]) if m]
        assert len(models) == 4  # the empty-id record is dropped
        return models

    def test_first_model_fields(self, parsed):
        m = parsed[0]
        assert m["id"] == "tencent/hy4-preview"
        assert m["name"] == "Tencent: Hy4 preview"
        assert m["created"] == 1787897375
        assert m["created_iso"].startswith("2026-08-2")
        assert m["context_length"] == 1048576
        assert m["prompt_price_per_mtok"] == pytest.approx(0.834)
        assert m["completion_price_per_mtok"] == pytest.approx(2.501)
        assert m["provider"] == "tencent"
        assert m["modality"] == "text->text"
        assert m["input_modalities"] == ["text"]
        assert m["output_modalities"] == ["text"]

    def test_free_and_degenerate_pricing(self, parsed):
        free = next(m for m in parsed if m["id"] == "meta-llama/llama-4-free")
        assert free["prompt_price_per_mtok"] == 0.0
        assert free["completion_price_per_mtok"] == 0.0
        weird = next(m for m in parsed if m["id"] == "weird/negative-price")
        assert weird["prompt_price_per_mtok"] is None  # negative -> unknown
        assert weird["completion_price_per_mtok"] is None  # unparsable -> unknown
        assert weird["context_length"] is None

    def test_record_without_id_is_skipped(self):
        assert parse_model(RAW_CATALOG["data"][4]) is None


class TestDiffNewModels:
    """Seen-map diffing: baseline, single new model, cap."""

    NOW = "2026-08-28T12:00:00+00:00"

    @pytest.fixture
    def models(self):
        return [m for m in (parse_model(r) for r in RAW_CATALOG["data"]) if m]

    def test_baseline_first_run(self, models):
        """First run ever: nothing is 'new', everything is marked seen."""
        diff = diff_new_models(models, {}, self.NOW)
        assert diff["is_baseline"] is True
        assert diff["new_models"] == []
        assert set(diff["seen_map"]) == {m["id"] for m in models}
        assert all(v == self.NOW for v in diff["seen_map"].values())
        assert diff["tracked_since"] == self.NOW

    def test_two_known_one_new(self, models):
        """3 known ids + 1 unseen id -> exactly the unseen one in new_models."""
        seen = {models[1]["id"]: "2026-08-27T00:00:00+00:00", models[2]["id"]: "2026-08-27T00:00:00+00:00", models[3]["id"]: "2026-08-27T00:00:00+00:00"}
        diff = diff_new_models(models, seen, self.NOW)
        assert diff["is_baseline"] is False
        assert [m["id"] for m in diff["new_models"]] == [models[0]["id"]]
        assert diff["new_models"][0]["first_seen"] == self.NOW
        # seen-map is upserted, old stamps preserved.
        assert diff["seen_map"][models[1]["id"]] == "2026-08-27T00:00:00+00:00"
        assert diff["seen_map"][models[0]["id"]] == self.NOW
        assert diff["tracked_since"] == "2026-08-27T00:00:00+00:00"

    def test_cap_at_30_newest_first(self):
        """35 unseen models -> feed capped at NEW_MODELS_CAP, newest created first."""
        models = [{"id": f"vendor/model-{i}", "created": 1_700_000_000 + i} for i in range(35)]
        diff = diff_new_models(models, {}, self.NOW)  # baseline: feeds stay empty
        assert diff["new_models"] == []
        diff = diff_new_models(models, {"known/old": "2026-08-01T00:00:00+00:00"}, self.NOW)
        assert len(diff["new_models"]) == NEW_MODELS_CAP == 30
        created = [m["created"] for m in diff["new_models"]]
        assert created == sorted(created, reverse=True)
        assert diff["new_models"][0]["id"] == "vendor/model-34"
        # All 35 ids still land in the seen-map even though the feed is capped.
        assert len(diff["seen_map"]) == 36


class TestLoadSeenMap:
    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        from src.etl.benchmarks import openrouter_models_etl as etl

        monkeypatch.setattr(etl, "get_data_dir", lambda: tmp_path)
        assert load_seen_map() == {}

    def test_corrupt_file_returns_empty(self, tmp_path, monkeypatch):
        from src.etl.benchmarks import openrouter_models_etl as etl

        monkeypatch.setattr(etl, "get_data_dir", lambda: tmp_path)
        (tmp_path / "openrouter_seen_models.json").write_text("{not json", encoding="utf-8")
        assert load_seen_map() == {}


class TestFetchModelsCatalog:
    def test_failure_returns_none(self, monkeypatch):
        from src.etl.benchmarks import openrouter_models_etl as etl

        def _boom():
            raise RuntimeError("network down")

        monkeypatch.setattr(etl, "_fetch_raw", _boom)
        assert fetch_models_catalog() is None

    def test_empty_data_returns_none(self, monkeypatch):
        from src.etl.benchmarks import openrouter_models_etl as etl

        monkeypatch.setattr(etl, "_fetch_raw", lambda: {"data": []})
        assert fetch_models_catalog() is None


class TestRun:
    """File persistence and last-good behaviour."""

    def test_run_failure_keeps_last_good(self, tmp_path, monkeypatch):
        from src.etl.benchmarks import openrouter_models_etl as etl

        monkeypatch.setattr(etl, "get_data_dir", lambda: tmp_path)
        sentinel = tmp_path / "openrouter_models_latest.json"
        sentinel.write_text('{"total_models": 42}', encoding="utf-8")
        seen_sentinel = tmp_path / "openrouter_seen_models.json"
        seen_sentinel.write_text('{"a/b": "2026-08-01"}', encoding="utf-8")
        monkeypatch.setattr(etl, "fetch_models_catalog", lambda: None)
        run()
        assert json.loads(sentinel.read_text(encoding="utf-8"))["total_models"] == 42
        assert json.loads(seen_sentinel.read_text(encoding="utf-8")) == {"a/b": "2026-08-01"}

    def test_run_baseline_writes_snapshot_and_seen_map(self, tmp_path, monkeypatch):
        from src.etl.benchmarks import openrouter_models_etl as etl

        monkeypatch.setattr(etl, "get_data_dir", lambda: tmp_path)
        monkeypatch.setattr(etl, "fetch_models_catalog", lambda: list(RAW_CATALOG["data"]))
        run()

        latest = json.loads((tmp_path / "openrouter_models_latest.json").read_text(encoding="utf-8"))
        assert latest["source"] == "openrouter.ai"
        assert latest["total_models"] == 4
        assert latest["is_baseline_run"] is True
        assert latest["new_models"] == []
        assert len(latest["models"]) == 4
        assert latest["models"][0]["id"] == "tencent/hy4-preview"  # newest first

        timestamped = list(tmp_path.glob("openrouter_models_2*.json"))
        assert len(timestamped) == 1

        seen = json.loads((tmp_path / "openrouter_seen_models.json").read_text(encoding="utf-8"))
        assert len(seen) == 4

    def test_run_second_pass_reports_only_new(self, tmp_path, monkeypatch):
        from src.etl.benchmarks import openrouter_models_etl as etl

        monkeypatch.setattr(etl, "get_data_dir", lambda: tmp_path)
        monkeypatch.setattr(etl, "fetch_models_catalog", lambda: list(RAW_CATALOG["data"]))
        run()
        # Next run the catalog gains one brand-new model (newest created date).
        extended = list(RAW_CATALOG["data"]) + [{"id": "newco/fresh-model", "name": "NewCo: Fresh", "created": 1787900000, "context_length": 8192, "pricing": {"prompt": "0.000002", "completion": "0.000006"}}]
        monkeypatch.setattr(etl, "fetch_models_catalog", lambda: extended)
        run()

        latest = json.loads((tmp_path / "openrouter_models_latest.json").read_text(encoding="utf-8"))
        assert latest["is_baseline_run"] is False
        assert latest["new_models_count"] == 1
        assert latest["new_models"][0]["id"] == "newco/fresh-model"
        assert latest["new_models"][0]["first_seen"]

        seen = json.loads((tmp_path / "openrouter_seen_models.json").read_text(encoding="utf-8"))
        assert len(seen) == 5

    def test_save_json_roundtrip(self, tmp_path, monkeypatch):
        from src.etl.benchmarks import openrouter_models_etl as etl

        monkeypatch.setattr(etl, "get_data_dir", lambda: tmp_path)
        out = save_json({"total_models": 4}, "openrouter_models_latest.json")
        assert out == tmp_path / "openrouter_models_latest.json"
        assert json.loads(out.read_text(encoding="utf-8"))["total_models"] == 4
