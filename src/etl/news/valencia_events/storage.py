"""Writing a file so that a reader never sees it half written."""

import os
from pathlib import Path


def write_text_atomic(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` through a temporary file renamed over it.

    The dashboard and the API read these files while the ETL runs: with a plain
    write they could read an empty or truncated file for a moment. ``os.replace``
    swaps the whole file in one step on every platform the project runs on.

    Args:
        path: Destination, created if needed; its parent directory too.
        text: Full content, UTF-8.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)
