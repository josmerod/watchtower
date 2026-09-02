"""Sync test: the API's replicated radar source table must match the tab's.

``src/api/public.py`` deliberately does not import Dash modules, so its
RADAR_SOURCES table duplicates the tab's list. This test imports BOTH sides
(tests may import Dash) and fails the moment someone adds/removes a source in
the tab without syncing the API — the exact drift that silently hid six radar
sources from ``/api/v1/radar`` between 2026-08-28 and 2026-09-02.
"""

from src.api import public as public_api
from src.web.dashboard.components import tech_radar_tab


def test_api_radar_keys_match_tab_sources():
    """Every tab RADAR_SOURCES key/file/category must exist in the API table."""
    tab_sources = tech_radar_tab.RADAR_SOURCES
    api_sources = {s["key"]: s for s in public_api.RADAR_SOURCES}

    assert api_sources, "API radar table is empty"
    assert set(api_sources) == {s["key"] for s in tab_sources}, (
        f"Radar source drift between tab and API. "
        f"Missing from API: {sorted({s['key'] for s in tab_sources} - set(api_sources))}; "
        f"Extra in API: {sorted(set(api_sources) - {s['key'] for s in tab_sources})}"
    )

    for tab_src in tab_sources:
        api_src = api_sources[tab_src["key"]]
        expected_files = tab_src.get("files") or [tab_src["file"]]
        assert sorted(api_src["files"]) == sorted(expected_files), (
            f"{tab_src['key']}: API files {api_src['files']} != tab files {expected_files}"
        )
        assert api_src["category"] == tab_src["category"], f"{tab_src['key']}: category drift"
