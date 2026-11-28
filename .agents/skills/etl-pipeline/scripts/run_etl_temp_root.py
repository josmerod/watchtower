"""Run one Watchtower ETL against a temporary project root, so nothing lands in the checkout's ``data/`` or ``logs/``.

Usage, from the root of the checkout you are working in::

    uv run python .agents/skills/etl-pipeline/scripts/run_etl_temp_root.py src/etl/news/news_get_devto.py
    uv run python .agents/skills/etl-pipeline/scripts/run_etl_temp_root.py src.etl.news.news_get_devto --flag value
    uv run python .agents/skills/etl-pipeline/scripts/run_etl_temp_root.py --seed-data <a data dir> src/etl/courses/ms_applied_skills_etl.py

The ETL is given as a path or as a dotted module; anything after it is passed on untouched. The temporary root is a new directory under the system temp folder. Its path is printed first and, when the ETL ends, every file it created or rewrote under it; the root is kept for inspection.

``--seed-data`` copies a ``data/`` into the root before the ETL starts, for an ETL that keeps state in its output (stamps of first detection, checkpoints): it shows what the ETL writes on top of existing output, which is what the next production cycle will do. The source is only read.

Why: ``data/`` is historical and never clobbered, and two helpers decide where it is. Plain modules ask ``src.utils.file_system`` for the project root and ``BaseETL`` asks ``Settings.project_root``, read from ``WATCHTOWER_PROJECT_ROOT``. Both are redirected here before anything under ``src/`` is imported: redirecting only the first once left ``data/`` and ``logs/`` inside a worktree.
"""

import argparse
import os
import runpy
import shutil
import sys
import tempfile
import time
from pathlib import Path

MAX_LISTED = 40
NOT_SEEDED = ("metrics", "__pycache__")


def module_name(target: str) -> str:
    """Turn ``src/etl/x/y.py`` into ``src.etl.x.y``; a dotted name only loses a ``.py`` suffix."""
    name = target.replace("\\", "/").removeprefix("./")
    if name.endswith(".py"):
        name = name[:-3]
    return name.replace("/", ".") if "/" in name else name


def files_written_since(root: Path, started: float) -> list[str]:
    """Every file below ``root`` created or rewritten since ``started``, as forward-slash paths relative to it."""
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.stat().st_mtime >= started)


def main() -> None:
    """Redirect the project root and run the ETL as ``__main__``."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", help="the ETL: a path under the repository or a dotted module")
    parser.add_argument("forward", nargs=argparse.REMAINDER, help="anything after the ETL goes to it untouched")
    parser.add_argument("--seed-data", type=Path, help="a data/ to copy into the temporary root first, for an ETL that keeps state in its output")
    options = parser.parse_args()

    root = Path.cwd()
    if not (root / "pyproject.toml").exists():
        raise SystemExit(f"Run this from the repository root: {root} has no pyproject.toml")
    temp_root = Path(tempfile.mkdtemp(prefix="watchtower-etl-"))
    print(f"Temporary project root: {temp_root}", flush=True)
    if options.seed_data is not None:
        if not options.seed_data.is_dir():
            raise SystemExit(f"--seed-data: no directory at {options.seed_data}")
        shutil.copytree(options.seed_data, temp_root / "data", ignore=shutil.ignore_patterns(*NOT_SEEDED))
        print(f"data/ seeded from {options.seed_data} (only read)", flush=True)

    sys.path.insert(0, str(root))
    os.environ["WATCHTOWER_PROJECT_ROOT"] = str(temp_root)

    import src.utils.file_system as file_system

    file_system.get_file_system_manager().project_root = temp_root

    module = module_name(options.target)
    sys.argv = [module, *options.forward]
    started = time.time()
    try:
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    finally:
        written = files_written_since(temp_root, started)
        print(f"\n{len(written)} file(s) created or rewritten under {temp_root}", flush=True)
        for name in written[:MAX_LISTED]:
            print(f"  {name}")
        if len(written) > MAX_LISTED:
            print(f"  ... and {len(written) - MAX_LISTED} more")


if __name__ == "__main__":
    main()
