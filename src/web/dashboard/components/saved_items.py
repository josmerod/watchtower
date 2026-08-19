"""Saved-items persistence for the dashboard (spec 03 F3, read-it-later).

Items are stored in ``data/garden/saved_items.json`` keyed by a stable hash of
their URL/title so any tab (KG today, others later) can star an item and the
"⭐ Guardados" views all read the same file.
"""

import hashlib
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from src.web.dashboard.utils import get_data_path

SAVED_FILE = Path(get_data_path("garden", "saved_items.json"))

_lock = threading.Lock()


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
        item: Dict with at least ``url`` or ``title``; ``source`` optional.
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
            }
            saved.insert(0, record)
            new_state = True
        else:
            saved = remaining
            new_state = False
        SAVED_FILE.parent.mkdir(parents=True, exist_ok=True)
        SAVED_FILE.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    return new_state
