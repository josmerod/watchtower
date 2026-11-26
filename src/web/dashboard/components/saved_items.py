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

# Snapshot of the saved file, kept while the file does not change. Every star
# button calls is_saved(), so a table render used to read and parse the whole
# file once per row (514 times for one Knowledge Garden render, T-136). The
# stamp is the file's (path, mtime, size) plus a counter of the writes made
# through toggle_saved(): two of them can land on the same mtime tick with the
# same length, which stat() alone could not tell apart.
_saved_cache: list[dict[str, Any]] = []
_saved_stamp: tuple[str, int, int, int] | None = None
_saved_writes = 0


def item_hash(url: str | None, title: str | None) -> str:
    """Stable hash identifying an item across renders and tabs."""
    key = (url or "").strip().lower() or (title or "").strip().lower()
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def _file_stamp() -> tuple[str, int, int, int] | None:
    """Identify the current content of the saved file, or None when it is not there."""
    try:
        stat = SAVED_FILE.stat()
    except OSError:
        return None
    return (str(SAVED_FILE), stat.st_mtime_ns, stat.st_size, _saved_writes)


def _snapshot() -> list[dict[str, Any]]:
    """The saved records as they are on disk right now (shared: read-only)."""
    global _saved_stamp
    stamp = _file_stamp()
    if stamp is None:
        return []
    if stamp != _saved_stamp:
        try:
            data = json.loads(SAVED_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []  # not cached: a file that gets fixed is picked up
        _saved_cache[:] = data if isinstance(data, list) else []
        _saved_stamp = stamp
    return _saved_cache


def load_saved() -> list[dict[str, Any]]:
    """Return the saved items list (newest first), tolerating a missing file.

    The file is read again only when it changed; callers get their own
    records, free to modify.
    """
    return [dict(record) for record in _snapshot()]


def is_saved(h: str) -> bool:
    """Check whether an item hash is currently saved."""
    return any(item.get("hash") == h for item in _snapshot())


def toggle_saved(item: dict[str, Any]) -> bool:
    """Star or unstar an item; returns the new saved state.

    Args:
        item: Dict with at least ``url`` or ``title``; ``source`` and ``tab``
            optional (``tab`` records the originating dashboard tab).
    """
    global _saved_writes
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
        _saved_writes += 1
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


def register_candidate(item: dict[str, Any], tab: str = "") -> str:
    """Register an item for a later star toggle and return its hash.

    A toggle only ever receives the hash, so the full record has to be
    kept from the render that showed the star.
    """
    h = item_hash(item.get("url") or item.get("link"), item.get("title") or item.get("name"))
    SAVE_CANDIDATES[h] = {**item, "tab": tab}
    return h


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
    h = register_candidate(item, tab)
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
    def _toggle_saved_item(n_clicks: int | None):
        # Dash runs a pattern-matching callback for every button inserted into
        # the page, even with prevent_initial_call=True; those calls carry no
        # click, and toggling on them starred rows nobody clicked.
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update
        return toggle_response(dash.ctx.triggered_id.hash)
