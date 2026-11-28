"""Start the dashboard on 127.0.0.1 over a copy of ``data/``, under a temporary project root.

Usage, from the root of the checkout you are working in::

    uv run python .agents/skills/dashboard-tab/scripts/run_dashboard_temp_root.py
    uv run python .agents/skills/dashboard-tab/scripts/run_dashboard_temp_root.py --port 8791 --root <dir> --no-copy

Why a copy: the dashboard reads every file under ``data/`` and writes ``data/garden/saved_items.json`` when a star is clicked, so a check against the checkout's own ``data/`` edits the user's saved items. The copy is made once per root; pass ``--root`` to keep it between runs (delete it to copy again).

Both project-root helpers are redirected before anything under ``src/`` is imported — ``get_data_path()`` in ``src/web/dashboard/utils.py`` and ``get_project_root()`` in ``src/utils/file_system.py`` — and ``WATCHTOWER_PROJECT_ROOT`` sends Settings' ``data/`` and ``logs/`` to the same root. The source ``data/`` is only read.

Stop the server with Ctrl+C. It runs with ``debug=False``: no reloader, so the port is free when the process ends.
"""

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

IGNORED_ON_COPY = ("metrics", "__pycache__")


def copy_data(source: Path, target: Path) -> None:
    """Copy ``source`` into ``target`` once; say which data is in use."""
    if target.exists():
        print(f"data already at {target}", flush=True)
        return
    if not source.is_dir():
        raise SystemExit(f"No data to copy at {source}. Pass --source-data, or --no-copy for an empty dashboard.")
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(*IGNORED_ON_COPY))
    print(f"data copied to {target}", flush=True)


def main() -> None:
    """Prepare the temporary root, redirect both helpers and serve the app."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8790, help="port to listen on, 127.0.0.1 only (default 8790)")
    parser.add_argument("--root", type=Path, help="project root for this run (default: a new temporary directory)")
    parser.add_argument("--source-data", type=Path, help="the data/ to copy (default: the checkout's data/)")
    parser.add_argument("--no-copy", action="store_true", help="start with no data/: layout checks only")
    options = parser.parse_args()

    repo_root = Path.cwd()
    if not (repo_root / "pyproject.toml").exists():
        raise SystemExit(f"Run this from the repository root: {repo_root} has no pyproject.toml")
    root = (options.root or Path(tempfile.mkdtemp(prefix="watchtower-dashboard-"))).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not options.no_copy:
        copy_data(options.source_data or repo_root / "data", root / "data")

    sys.path.insert(0, str(repo_root))
    os.environ["WATCHTOWER_PROJECT_ROOT"] = str(root)

    from src.utils import file_system
    from src.web.dashboard import utils as dashboard_utils

    file_system.get_project_root = lambda: str(root)
    dashboard_utils.get_project_root = lambda: str(root)

    from src.web.dashboard.app import app

    print(f"Dashboard at http://127.0.0.1:{options.port}/ — project root {root} — Ctrl+C to stop", flush=True)
    app.run(debug=False, port=options.port, host="127.0.0.1")


if __name__ == "__main__":
    main()
