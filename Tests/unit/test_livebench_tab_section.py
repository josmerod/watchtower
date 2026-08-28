"""Tests for the LiveBench section of the Benchmarks tab.

Renders the section against fixture data (no repo ``data/`` dependency and no
network access).
"""

from unittest.mock import patch

import pytest

from src.web.dashboard.components import benchmarks_tab as tab

FIXTURE_DATA = {
    "source": "livebench.ai",
    "source_url": "https://livebench.ai/",
    "release": "2026-06-25",
    "fetched_at": "2026-08-28T10:33:26+00:00",
    "categories": ["overall", "reasoning", "coding", "agentic_coding"],
    "cost_key": "cost_per_successful_task",
    "models_count": 2,
    "models": [
        {"rank": 1, "model": "Claude Fable 5 Max Effort", "overall": 83.0, "reasoning": 89.7, "coding": 86.0, "agentic_coding": 62.2, "cost_per_successful_task": 1.439},
        {"rank": 2, "model": "GPT-5.6 Sol Max Effort", "overall": 81.0, "reasoning": 91.7, "coding": 83.9, "agentic_coding": 56.2, "cost_per_successful_task": 0.515},
    ],
}


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
    def test_fmt_cost(self):
        assert tab._fmt_cost(1.439) == "$1.439"
        assert tab._fmt_cost(None) == "—"
        assert tab._fmt_cost("x") == "—"

    def test_category_label(self):
        assert tab._category_label("agentic_coding") == "Agentic Coding"
        assert tab._category_label("overall") == "Overall"


class TestBuildLivebenchTable:
    def test_table_renders_categories_models_and_cost(self):
        table = tab._build_livebench_table(FIXTURE_DATA["models"], FIXTURE_DATA["categories"])
        text = _component_text(table)
        assert "Agentic Coding" in text
        assert "Claude Fable 5 Max Effort" in text
        assert "$1.439" in text
        assert "🥇" in text  # rank 1 medal


class TestRenderLivebenchSection:
    def test_no_data_placeholder(self):
        with patch.object(tab, "_load_livebench", return_value={}):
            section = tab._render_livebench_section()
        text = _component_text(section)
        assert "No benchmark data yet" in text
        assert "src.etl.benchmarks.livebench_etl" in text

    def test_with_data(self):
        with patch.object(tab, "_load_livebench", return_value=FIXTURE_DATA):
            section = tab._render_livebench_section()
        text = _component_text(section)
        assert "2026-06-25" in text
        assert "Claude Fable 5 Max Effort" in text
        assert "livebench.ai" in text


class TestRenderBenchmarksTab:
    def test_livebench_source_tab_is_registered(self):
        """The full tab must keep all sources and expose the LiveBench tab."""
        aa_models = [{"name": "Model A", "creator": "X", "open_weights": True, "intelligence_index": 50.0}]
        with patch.object(tab, "_load_aa_data", return_value=(aa_models, {"fetched_at": "2026-08-28T00:00:00+00:00", "count": 1})):
            rendered = tab.render_benchmarks_tab()
        text = _component_text(rendered)
        for label in ("Community LLM Leaderboard", "LiveBench", "BridgeBench.ai", "Artificial Analysis"):
            assert label in text
        # Existing ids must stay intact (single callback pattern preserved).
        ids = _component_ids(rendered)
        assert "benchmark-category-tabs" in ids
        assert "aa-llm-table-container" in ids
        assert "aa-llm-filter-open" in ids
        assert "benchmarks-source-tabs" in ids
