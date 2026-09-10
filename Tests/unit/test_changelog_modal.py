"""Unit tests for the 🆕 Novedades changelog modal (T-089).

Covers three layers:
- the repo-root ``changelog.json`` (parses, schema, newest-first ordering),
- the component renderer (elements built, hidden data div carries the version,
  modal starts closed, missing/invalid file renders nothing), and
- callback registration (single guarded callback, prevent_initial_call).
"""

import json
from pathlib import Path
from unittest.mock import Mock

import dash

from src.web.dashboard.components.changelog_modal import (
    _next_modal_state,
    load_changelog,
    register_changelog_callbacks,
    render_changelog_elements,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CHANGELOG_FILE = REPO_ROOT / "changelog.json"


def _iter_components(component):
    """Yield component and every descendant that looks like a Dash component."""
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    kids = children if isinstance(children, (list, tuple)) else [children]
    for kid in kids:
        if hasattr(kid, "id") or hasattr(kid, "children"):
            yield from _iter_components(kid)


def _find_by_id(elements, target_id):
    """Return the first component (any depth) whose id equals target_id."""
    for element in elements:
        for component in _iter_components(element):
            if getattr(component, "id", None) == target_id:
                return component
    return None


class TestChangelogFile:
    """The versioned changelog.json at the repo root."""

    def test_parses_and_has_schema_fields(self):
        data = json.loads(CHANGELOG_FILE.read_text(encoding="utf-8"))

        assert isinstance(data["version"], str) and data["version"]
        assert isinstance(data["generated_at"], str) and data["generated_at"]
        entries = data["entries"]
        assert isinstance(entries, list) and 1 <= len(entries) <= 4
        for entry in entries:
            assert {"date", "title", "items"} <= set(entry)
            assert isinstance(entry["date"], str) and entry["date"]
            assert isinstance(entry["title"], str) and entry["title"]
            assert isinstance(entry["items"], list) and entry["items"]
            assert all(isinstance(item, str) and item for item in entry["items"])

    def test_entries_sorted_newest_first(self):
        data = json.loads(CHANGELOG_FILE.read_text(encoding="utf-8"))
        dates = [entry["date"] for entry in data["entries"]]
        assert dates == sorted(dates, reverse=True)

    def test_load_changelog_default_path(self):
        data = load_changelog()
        assert data is not None
        assert data["version"]


class TestRenderChangelogElements:
    """The self-contained layout builder."""

    def test_renders_data_div_button_and_modal(self):
        elements = render_changelog_elements()
        assert elements, "valid changelog must render elements"

        ids = {getattr(c, "id", None) for e in elements for c in _iter_components(e)}
        assert "changelog-data" in ids
        assert "changelog-open-button" in ids
        assert "changelog-new-dot" in ids
        assert "changelog-modal" in ids
        assert "changelog-modal-close" in ids

    def test_hidden_data_div_carries_version(self):
        elements = render_changelog_elements()
        holder = _find_by_id(elements, "changelog-data")
        assert holder is not None
        assert holder.style.get("display") == "none"
        payload = json.loads(holder.children)
        assert payload["version"] == load_changelog()["version"]

    def test_modal_starts_closed_with_static_content(self):
        elements = render_changelog_elements()
        modal = _find_by_id(elements, "changelog-modal")
        assert modal is not None
        assert modal.is_open is False
        # Body is built server-side at layout time, not via callback outputs.
        assert modal.children is not None and len(modal.children) > 0

    def test_missing_file_renders_nothing(self, tmp_path):
        missing = tmp_path / "does_not_exist.json"
        assert load_changelog(path=missing) is None
        assert render_changelog_elements(path=missing) == []

    def test_invalid_json_renders_nothing(self, tmp_path):
        broken = tmp_path / "broken.json"
        broken.write_text("{not valid json", encoding="utf-8")
        assert load_changelog(path=broken) is None
        assert render_changelog_elements(path=broken) == []

    def test_schema_without_version_renders_nothing(self, tmp_path):
        incomplete = tmp_path / "incomplete.json"
        incomplete.write_text(json.dumps({"entries": []}), encoding="utf-8")
        assert load_changelog(path=incomplete) is None
        assert render_changelog_elements(path=incomplete) == []


class TestRegisterCallbacks:
    """Callback registration follows the repo's anti-self-open pattern."""

    def test_registers_single_guarded_callback(self):
        app = Mock()
        register_changelog_callbacks(app)

        app.callback.assert_called_once()
        kwargs = app.callback.call_args.kwargs
        assert kwargs["prevent_initial_call"] is True
        # Two Inputs: the 🆕 open button and the Cerrar button.
        inputs = kwargs["inputs"] if "inputs" in kwargs else list(app.callback.call_args.args[1:])
        assert len(inputs) == 2


class TestToggleLogic:
    """The open/close decision function behind the callback."""

    def test_open_button_click_opens(self):
        assert _next_modal_state("changelog-open-button", 1, 0) is True

    def test_close_button_click_closes(self):
        assert _next_modal_state("changelog-modal-close", 3, 1) is False

    def test_zero_clicks_is_noop(self):
        # Component-added firings carry n_clicks=0/None — must never open.
        assert _next_modal_state("changelog-open-button", 0, 0) is dash.no_update
        assert _next_modal_state("changelog-open-button", None, None) is dash.no_update

    def test_unknown_trigger_is_noop(self):
        assert _next_modal_state(None, 5, 5) is dash.no_update
        assert _next_modal_state("something-else", 5, 0) is dash.no_update


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-v"]))
