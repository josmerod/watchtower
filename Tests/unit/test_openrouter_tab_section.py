"""Tests for the OpenRouter "New Models" section of the Benchmarks tab.

Renders the section against fixture data (no repo ``data/`` dependency and no
network access).
"""

from unittest.mock import patch

from src.web.dashboard.components import benchmarks_tab as tab

FIXTURE_NEW_MODELS = {
    "source": "openrouter.ai",
    "source_url": "https://openrouter.ai/api/v1/models",
    "generated_at": "2026-08-28T12:45:18+00:00",
    "total_models": 387,
    "tracked_since": "2026-08-27T06:00:00+00:00",
    "new_models_count": 2,
    "is_baseline_run": False,
    "new_models": [
        {
            "id": "tencent/hy4-preview",
            "name": "Tencent: Hy4 preview",
            "created": 1787897375,
            "created_iso": "2026-08-28T06:09:35+00:00",
            "context_length": 1048576,
            "prompt_price_per_mtok": 0.834,
            "completion_price_per_mtok": 2.501,
            "provider": "tencent",
            "modality": "text->text",
            "first_seen": "2026-08-28T12:45:18+00:00",
        },
        {
            "id": "newco/fresh-model",
            "name": "NewCo: Fresh",
            "created": 1787900000,
            "created_iso": "2026-08-28T07:06:40+00:00",
            "context_length": 128000,
            "prompt_price_per_mtok": 0.0,
            "completion_price_per_mtok": None,
            "provider": "newco",
            "modality": "text->text",
            "first_seen": "2026-08-28T12:45:18+00:00",
        },
    ],
    "models": [],
}

FIXTURE_BASELINE = {**FIXTURE_NEW_MODELS, "new_models": [], "new_models_count": 0, "is_baseline_run": True}


def _component_text(component) -> str:
    """Flatten a Dash component tree into its visible text."""
    texts = []

    def walk(node):
        if isinstance(node, str):
            texts.append(node)
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item)
        elif hasattr(node, "children"):
            walk(node.children)
        elif hasattr(node, "value") and isinstance(node.value, str):
            texts.append(node.value)

    walk(component)
    return " ".join(texts)


def _component_ids(component) -> set:
    """Collect every element id present in a Dash component tree."""
    ids = set()

    def walk(node):
        if isinstance(node, (list, tuple)):
            for item in node:
                walk(item)
            return
        # Collect ids even for components without a children prop (e.g. dcc.Dropdown).
        node_id = getattr(node, "id", None)
        if node_id:
            ids.add(node_id)
        children = getattr(node, "children", None)
        if children is not None:
            walk(children)

    walk(component)
    return ids


class TestFormatters:
    def test_fmt_context(self):
        assert tab._fmt_context(1048576) == "1.0M"
        assert tab._fmt_context(128000) == "128K"
        assert tab._fmt_context(512) == "512"
        assert tab._fmt_context(None) == "—"
        assert tab._fmt_context("x") == "—"

    def test_fmt_date(self):
        assert tab._fmt_date("2026-08-28T12:45:18+00:00") == "2026-08-28"
        assert tab._fmt_date(None) == "—"
        assert tab._fmt_date("") == "—"


class TestBuildNewModelsTable:
    def test_table_renders_rows(self):
        table = tab._build_new_models_table(FIXTURE_NEW_MODELS["new_models"])
        text = _component_text(table)
        assert "Tencent: Hy4 preview" in text
        assert "tencent/hy4-preview" in text
        assert "1.0M" in text  # context
        assert "$0.8340" in text  # $/Mtok in (reused _fmt_price, 4 decimals < $1)
        assert "$2.50" in text  # $/Mtok out
        assert "Free" in text  # zero price renders as Free
        assert "—" in text  # missing completion price
        assert "2026-08-28" in text  # first_seen date


class TestRenderOpenRouterSection:
    def test_no_data_placeholder(self):
        with patch.object(tab, "_load_openrouter_models", return_value={}):
            section = tab._render_openrouter_new_models_section()
        text = _component_text(section)
        assert "No benchmark data yet" in text
        assert "src.etl.benchmarks.openrouter_models_etl" in text

    def test_with_data_summary_and_table(self):
        with patch.object(tab, "_load_openrouter_models", return_value=FIXTURE_NEW_MODELS):
            section = tab._render_openrouter_new_models_section()
        text = _component_text(section)
        assert "2 new models since 2026-08-27" in text
        assert "387 models in the OpenRouter catalog" in text
        assert "openrouter.ai/models" in text
        assert "Tencent: Hy4 preview" in text

    def test_baseline_note_when_empty(self):
        with patch.object(tab, "_load_openrouter_models", return_value=FIXTURE_BASELINE):
            section = tab._render_openrouter_new_models_section()
        text = _component_text(section)
        assert "No new models since the baseline" in text
        assert "marked as seen" in text
        assert "0 new models since" in text


class TestRenderBenchmarksTab:
    def test_new_models_source_tab_is_registered(self):
        """The full tab must keep all sources and expose the New Models tab."""
        aa_models = [{"name": "Model A", "creator": "X", "open_weights": True, "intelligence_index": 50.0}]
        bridgebench = [{"model": "Model A", "quality": 1.0, "vibe": 2.0}]
        with (
            patch.object(tab, "_load_aa_data", return_value=(aa_models, {"fetched_at": "2026-08-28T00:00:00+00:00", "count": 1})),
            patch.object(tab, "_load_openrouter_models", return_value=FIXTURE_NEW_MODELS),
            patch.object(tab, "_load_benchmark_category", return_value=bridgebench),
        ):
            rendered = tab.render_benchmarks_tab()
        text = _component_text(rendered)
        for label in ("Community LLM Leaderboard", "LiveBench", "New Models", "BridgeBench.ai", "Artificial Analysis"):
            assert label in text
        # The new-models feed content renders inside the full tab.
        assert "Tencent: Hy4 preview" in text
        # Existing ids must stay intact (single callback pattern preserved).
        ids = _component_ids(rendered)
        assert "benchmark-category-tabs" in ids
        assert "aa-llm-table-container" in ids
        assert "aa-llm-filter-open" in ids
        assert "benchmarks-source-tabs" in ids
