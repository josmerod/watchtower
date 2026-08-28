"""Saved-items persistence for the dashboard (spec 03 F3, read-it-later).

Items are stored in ``data/garden/saved_items.json`` keyed by a stable hash of
their URL/title so any tab (Knowledge Garden, News "🔎 Global", Tech Radar
"🔄 Todos" feed, Markets) can star an item and the "⭐ Guardados" views all
read the same file. Records carry a ``tab`` field with the originating tab so
the unified saved list stays coherent across sources.
"""

import hashlib
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output

from src.web.dashboard.utils import get_data_path

SAVED_FILE = Path(get_data_path("garden", "saved_items.json"))

logger = logging.getLogger(__name__)

_lock = threading.Lock()

# hash -> full item dict, filled at render time by every tab that renders a
# star button, so a toggle callback can create a complete saved record on the
# first star (the button id only carries the hash). Shared across tabs: the
# hash is global, so the same item starred from two tabs is one record.
SAVE_CANDIDATES: dict[str, dict[str, Any]] = {}


def item_hash(url: str | None, title: str | None) -> str:
    """Stable hash identifying an item across renders and tabs."""
    key = (url or "").strip().lower() or (title or "").strip().lower()
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def load_saved() -> list[dict[str, Any]]:
    """Return the saved items list (newest first), tolerating a missing file."""
    try:
        data = json.loads(SAVED_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def is_saved(h: str) -> bool:
    """Check whether an item hash is currently saved."""
    return any(item.get("hash") == h for item in load_saved())


def toggle_saved(item: dict[str, Any]) -> bool:
    """Star or unstar an item; returns the new saved state.

    Args:
        item: Dict with at least ``url`` or ``title``; ``source`` and ``tab``
            optional (``tab`` records the originating dashboard tab).
    """
    h = item_hash(item.get("url") or item.get("link"), item.get("title") or item.get("name"))
    with _lock:
        saved = load_saved()
        remaining = [s for s in saved if s.get("hash") != h]
        if len(remaining) == len(saved):
            record = {
                "hash": h,
                "title": str(item.get("title") or item.get("name") or ""),
                "url": item.get("url") or item.get("link"),
                "source": item.get("source_display_name") or item.get("source") or "",
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "tab": str(item.get("tab") or ""),
            }
            saved.insert(0, record)
            new_state = True
        else:
            saved = remaining
            new_state = False
        SAVED_FILE.parent.mkdir(parents=True, exist_ok=True)
        SAVED_FILE.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    return new_state


def lookup_candidate(h: str) -> dict[str, Any] | None:
    """Resolve the record for a star toggle.

    The saved file wins (once saved the record there is complete, including
    the original title/url/source/tab); the render-time registry is the
    fallback for a first star whose button was rendered this session.
    """
    record = next((s for s in load_saved() if s.get("hash") == h), None)
    if record is None:
        record = SAVE_CANDIDATES.get(h)
    return record


def save_button(item: dict[str, Any], btn_type: str, tab: str = "", class_name: str = "ms-1 p-0 border-0") -> dbc.Button:
    """Build the ⭐/☆ toggle button for one item (pattern-matching id per hash).

    Also registers the item in :data:`SAVE_CANDIDATES` so the toggle callback
    can persist a full record on the first star.

    Args:
        item: Dict with at least ``url``/``link`` or ``title``/``name``.
        btn_type: Per-tab pattern id type (e.g. ``"kg-save-btn"``).
        tab: Tab key stored on the saved record (e.g. ``"news"``).
        class_name: Button classes; the margin side depends on whether the
            star leads or trails its row.

    Returns:
        The dbc.Button with the saved state rendered for load time.
    """
    h = item_hash(item.get("url") or item.get("link"), item.get("title") or item.get("name"))
    SAVE_CANDIDATES[h] = {**item, "tab": tab}
    saved = is_saved(h)
    return dbc.Button(
        "★" if saved else "☆",
        id={"type": btn_type, "hash": h},
        color="warning" if saved else "outline-secondary",
        size="sm",
        className=class_name,
        title="Quitar de guardados" if saved else "Guardar para luego",
    )


def toggle_response(h: str) -> tuple[Any, Any, Any]:
    """Toggle saved state for ``h`` and return the button (children, color, title)."""
    try:
        record = lookup_candidate(h)
        if record is None:
            return dash.no_update, dash.no_update, dash.no_update
        if toggle_saved(record):
            return "★", "warning", "Quitar de guardados"
        return "☆", "outline-secondary", "Guardar para luego"
    except Exception:
        logger.exception("Error computing saved-item toggle response")
        return dash.no_update, dash.no_update, dash.no_update


def register_save_toggle_callback(app: dash.Dash, btn_type: str) -> None:
    """Register the star/unstar callback for one tab's button type.

    One pattern-matching (MATCH) callback per ``btn_type``, targeting only
    that type's buttons: children/color/title are new outputs, so no existing
    controller callback is touched.
    """

    @app.callback(
        Output({"type": btn_type, "hash": dash.MATCH}, "children"),
        Output({"type": btn_type, "hash": dash.MATCH}, "color"),
        Output({"type": btn_type, "hash": dash.MATCH}, "title"),
        Input({"type": btn_type, "hash": dash.MATCH}, "n_clicks"),
        prevent_initial_call=True,
    )
    def _toggle_saved_item(_n_clicks: int):
        return toggle_response(dash.ctx.triggered_id.hash)
