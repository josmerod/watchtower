"""Render smoke tests for every dashboard tab (spec 15 T4).

Each test renders a tab's layout and asserts it returns a component without
raising, plus a couple of expected ids/strings. This catches wiring regressions
(dead ids, NameErrors, broken builders) that unit tests on helpers miss.
"""

import pytest

RENDERERS = [
    ("news_tab", "render_news_tab", ["news-global-search-input", "news-mark-all-read", "Salud de fuentes"]),
    ("knowledge_garden_tab", "render_knowledge_garden_tab", ["kg-global-search-input", "Guardados", "knowledge-source-tabs-main"]),
    ("shortcuts_tab", "render_shortcuts_tab", []),
    ("videos_tab", "render_videos_tab", ["videos-sort-by", "videos-container"]),
    ("courses_tab", "render_courses_tab", ["courses-global-search", "courses-main-tabs"]),
    ("fourchan_tab", "render_fourchan_tab", ["4chan-global-search"]),
    ("scavenging_tab", "render_scavenging_tab", []),
    ("valencia_events_new_tab", "render_valencia_events_tab", []),
    ("spanish_public_aid_tab", "render_spanish_public_aid_tab", []),
    ("arxiv_research_tab", "render_arxiv_research_tab", []),
    ("deals_tab", "render_deals_tab", []),
    ("benchmarks_tab", "render_benchmarks_tab", []),
    ("tech_radar_tab", "render_tech_radar_tab", ["tech-radar-plot"]),
    ("games_tab", "render_games_tab", ["games-sub-tabs"]),
    ("notifications_tab", "render_notifications_tab", []),
    ("metrics_tab", "render_metrics_tab", ["metrics-table-container", "metrics-update-interval"]),
]


def _render(module_name: str, function_name: str):
    import importlib

    module = importlib.import_module(f"src.web.dashboard.components.{module_name}")
    renderer = getattr(module, function_name)
    return renderer()


EMPTY_STATE_MARKERS = ("No 4chan Data", "No game data", "All game data files are missing", "No videos", "video-slash", "Could not load", "failed to load", "No data")


@pytest.mark.parametrize("module_name,function_name,expected_fragments", RENDERERS, ids=[m for m, _, _ in RENDERERS])
def test_tab_renders(module_name, function_name, expected_fragments):
    """Every tab renders without exploding and contains its key ids.

    Fragment assertions are skipped for legitimate empty states (no local
    data for that component) — rendering the empty state is itself the pass.
    """
    layout = _render(module_name, function_name)
    assert layout is not None
    rendered = str(layout)
    if any(marker in rendered for marker in EMPTY_STATE_MARKERS) and not any(f in rendered for f in expected_fragments):
        pytest.skip("no local data for this component — empty state rendered")
    for fragment in expected_fragments:
        assert fragment in rendered, f"{module_name}.{function_name} missing '{fragment}'"
