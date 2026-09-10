"""🆕 Novedades modal: versioned changelog surfaced in the dashboard header (T-089).

Reads the repo-root ``changelog.json`` once per layout render and builds three
elements meant to be splatted into the header actions area of ``app.py``:

- a hidden JSON holder div (``changelog-data``) carrying the current version,
  consumed by ``assets/js/changelog_state.js`` for the auto-open logic,
- the header 🆕 button with its unread dot (shown by JS when a new version
  has not been seen yet), and
- a ``dbc.Modal`` whose content is rendered SERVER-side at layout time.

The modal never self-opens from a callback (known bug class in this repo —
see the ``wt-video-modal`` guards in ``videos_tab.py``): the only callback
toggles ``is_open`` with ``prevent_initial_call`` plus ``n_clicks >= 1``
guards, so the JS auto-open routes through a real button click. A missing or
invalid ``changelog.json`` renders nothing (empty list), keeping the header
clean on fresh checkouts.
"""

import json
import logging
from pathlib import Path
from typing import Any

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, html

from src.utils.file_system import get_project_root

logger = logging.getLogger(__name__)

CHANGELOG_FILENAME = "changelog.json"


def _changelog_path() -> Path:
    """Absolute path of the repo-root changelog.json."""
    return Path(get_project_root()) / CHANGELOG_FILENAME


def load_changelog(path: Path | None = None) -> dict[str, Any] | None:
    """Load and minimally validate changelog.json.

    Args:
        path: Override path (tests); defaults to the repo-root changelog.

    Returns:
        Parsed changelog dict, or None when the file is missing, unreadable,
        not valid JSON, or missing the required ``version``/``entries`` fields.
    """
    target = path if path is not None else _changelog_path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Changelog not loadable at %s: %s", target, exc)
        return None
    if not isinstance(raw, dict):
        return None
    version = raw.get("version")
    entries = raw.get("entries")
    if not isinstance(version, str) or not version or not isinstance(entries, list):
        return None
    return raw


def _render_entries(entries: list[Any]) -> list[Any]:
    """Build the modal body sections, newest deploy first."""
    sections: list[Any] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        items = [str(item) for item in entry.get("items", []) if item]
        if not items:
            continue
        sections.append(
            html.Div(
                [
                    html.Div(
                        [
                            dbc.Badge(str(entry.get("date", "")), color="secondary", pill=True, className="me-2"),
                            html.Strong(str(entry.get("title", ""))),
                        ],
                        className="d-flex align-items-center flex-wrap gap-1 mb-2",
                    ),
                    dbc.ListGroup([dbc.ListGroupItem(html.Small(item)) for item in items]),
                ],
                className="mb-4",
            )
        )
    return sections or [html.P("Sin novedades registradas.", className="text-muted")]


def render_changelog_elements(path: Path | None = None) -> list[Any]:
    """Build the hidden data div, header 🆕 button and modal.

    Args:
        path: Override changelog path (tests); defaults to the repo-root file.

    Returns:
        ``[html.Div (changelog-data), html.Button (changelog-open-button),
        dbc.Modal (changelog-modal)]`` — or ``[]`` when no valid changelog
        exists, so callers can splat the result unconditionally.
    """
    data = load_changelog(path)
    if not data:
        return []

    version = data["version"]
    # JS only needs the version to decide dot/auto-open — keep the payload tiny.
    payload = json.dumps({"version": version}, ensure_ascii=False)

    hidden_data = html.Div(payload, id="changelog-data", style={"display": "none"})

    open_button = html.Button(
        [
            "🆕",
            html.Span(
                id="changelog-new-dot",
                style={
                    "display": "none",
                    "position": "absolute",
                    "top": "-4px",
                    "right": "-4px",
                    "width": "9px",
                    "height": "9px",
                    "border-radius": "50%",
                    "background": "#e5534b",
                    "box-shadow": "0 0 0 2px rgba(255,255,255,0.85)",
                },
            ),
        ],
        id="changelog-open-button",
        className="btn btn-outline-light",
        title=f"Novedades del despliegue (v {version})",
        n_clicks=0,
        style={"position": "relative", "line-height": "1"},
    )

    modal = dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle(
                    [
                        "🆕 Novedades",
                        dbc.Badge(f"v {version}", color="info", pill=True, className="ms-2 align-middle"),
                    ]
                ),
                close_button=True,
            ),
            dbc.ModalBody(_render_entries(data["entries"])),
            dbc.ModalFooter(
                dbc.Button("Cerrar", id="changelog-modal-close", color="secondary", outline=True, size="sm"),
            ),
        ],
        id="changelog-modal",
        is_open=False,  # Static shell: content is server-rendered, never self-opens
        size="lg",
        centered=True,
        scrollable=True,
    )

    return [hidden_data, open_button, modal]


def _next_modal_state(triggered_id: Any, open_clicks: int | None, close_clicks: int | None) -> Any:
    """Decide the modal ``is_open`` value for a callback firing.

    Guards mirror ``videos_tab.py``: a real click additionally requires
    ``n_clicks >= 1`` on the *triggered* input only, so layout renders and
    component-added firings can never leave the modal stuck open.

    Args:
        triggered_id: ``dash.ctx.triggered_id`` of the current firing.
        open_clicks: n_clicks of the 🆕 header button.
        close_clicks: n_clicks of the modal's Cerrar button.

    Returns:
        ``True``/``False`` to open/close, or ``dash.no_update`` otherwise.
    """
    if triggered_id == "changelog-modal-close" and (close_clicks or 0) >= 1:
        return False
    if triggered_id == "changelog-open-button" and (open_clicks or 0) >= 1:
        return True
    return dash.no_update


def register_changelog_callbacks(app: dash.Dash) -> None:
    """Register the open/close callbacks for the 🆕 Novedades modal."""

    @app.callback(
        Output("changelog-modal", "is_open"),
        Input("changelog-open-button", "n_clicks"),
        Input("changelog-modal-close", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_changelog_modal(open_clicks: int | None, close_clicks: int | None) -> Any:
        """Open on 🆕 click, close on Cerrar click; anything else is a no-op."""
        return _next_modal_state(dash.ctx.triggered_id, open_clicks, close_clicks)
