#!/usr/bin/env python
"""One-shot maintenance script for Watchtower.

Runs static code quality tools (Ruff, MyPy), test suite with coverage,
dead-code analysis with Vulture, and stale documentation detection.

Execute via:
    python scripts/maintenance.py

It prints colour-coded summaries and exits non-zero on any failure so it can
be wired into CI pipelines easily.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
SRC_DIR = ROOT / "src"


def run(cmd: list[str], description: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    """Run a shell command with echo and optional failure short-circuit."""
    print(f"\n🛠️  {description}\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if check and result.returncode != 0:
        print(f"❌ Command failed: {' '.join(cmd)} (exit {result.returncode})")
        sys.exit(result.returncode)
    return result


def find_stale_docs(days: int = 120) -> list[Path]:
    """Return markdown files in *docs* untouched for a given number of days."""
    import time

    cutoff_ts = time.time() - days * 24 * 60 * 60
    stale: list[Path] = []
    for md in DOCS_DIR.rglob("*.md"):
        try:
            mtime = md.stat().st_mtime
            if mtime < cutoff_ts:
                stale.append(md)
        except FileNotFoundError:  # file removed during scan
            continue
    return stale


def main() -> None:
    print("=== Watchtower One-Shot Maintenance ===")

    run(["ruff", "format", "src", "tests"], "Formatting source & tests")
    run(["ruff", "check", "src", "tests", "--fix"], "Static analysis (Ruff)")

    # MyPy strict type check
    run(["mypy", "src", "--install-types", "--non-interactive"], "Type checking (MyPy)")

    # Run the test suite with coverage
    run(["pytest", "-q", "--cov=src", "--cov-report=term-missing"], "Running test suite with coverage")

    # Dead code detection
    whitelist = ROOT / ".vulture_whitelist.py"
    run(
        [
            "vulture",
            str(SRC_DIR),
            "--exclude=tests",
            "--min-confidence",
            "80",
            "--make-whitelist",
            str(whitelist),
        ],
        "Scanning for dead code (Vulture)",
        check=False,
    )
    print(f"\n🕊️  Vulture whitelist saved to {whitelist}. Review it to decide what to delete.")

    # Stale documentation detection
    stale_docs = find_stale_docs()
    if stale_docs:
        print("\n📚 Stale documentation files (>120 days untouched):")
        for md in stale_docs:
            print(f" • {md.relative_to(ROOT)}")
    else:
        print("\n✅ No stale docs detected in the last 120 days.")

    print(
        textwrap.dedent(
            """
            ─────────────────────────────────────────────────────────────────
            All maintenance checks completed.
            • Inspect .vulture_whitelist.py for truly unused code and delete.
            • Update the stale docs listed above.
            • Stage changes, commit, and push.
            ─────────────────────────────────────────────────────────────────
            """
        )
    )


if __name__ == "__main__":
    main()
