"""Snapshot retention pruner for Watchtower's timestamped data files.

The ~95 ETLs append a new ``{name}_{YYYYMMDD_HHMMSS}.json`` snapshot on every
run (roughly every 2h), so ``data/`` grows without bound on the server volume.
This module plans and applies a conservative keep-the-newest-N retention pass:

- Groups timestamped ``.json`` files by their prefix (the stable part before
  the filename timestamp) *and* their directory, so ``run_summary_*`` files
  under ``data/a/output/`` never compete with snapshots under ``data/b/``.
- Marks everything beyond the newest ``keep_last`` files per group for
  deletion.
- NEVER touches: ``*_latest.json`` (any filename containing ``latest``),
  ``state.json`` / ``etl_state.json``, anything under ``data/watchers/``
  (event history is append-only), files without a parseable timestamp, and
  anything that is not ``.json`` (e.g. timestamped ``.csv`` exports).

Deletion is opt-in: the CLI defaults to dry-run and only deletes when passed
``--apply`` (or ``--dry-run=false``).

Usage:
    uv run python -m src.utils.snapshot_retention --keep-last 30           # dry-run (default)
    uv run python -m src.utils.snapshot_retention --keep-last 30 --apply   # actually delete
"""

from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.utils.file_system import get_project_root

logger = logging.getLogger(f"watchtower.{__name__}")

#: Filename stems that hold mutable state and must never be pruned.
_PROTECTED_NAMES = {"state.json", "etl_state.json"}

#: Top-level data/ subdirectory that is skipped entirely (append-only history).
_SKIPPED_TOP_LEVEL_DIRS = {"watchers"}

#: Timestamp token shapes found in real data/ filenames, most specific first.
#: Each pattern must be delimited (no adjacent digits) so long digit runs
#: inside slugs or hashes never match partially.
_TIMESTAMP_PATTERNS: tuple[re.Pattern[str], ...] = (
    # 20260828_100626 — dominant ETL snapshot format
    re.compile(r"(?<!\d)(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})(?!\d)"),
    # 20260828104905 — compact format (watcher event style)
    re.compile(r"(?<!\d)(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?!\d)"),
    # 2026_08_28_100626 — underscore-separated full date
    re.compile(r"(?<!\d)(\d{4})_(\d{2})_(\d{2})_(\d{2})(\d{2})(\d{2})(?!\d)"),
    # 2026-08-28, 2026-08-28T10:06:26, 2026-08-28_100626 — ISO-ish
    re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?:[T _-](\d{2}):?(\d{2}):?(\d{2}))?(?!\d)"),
)


@dataclass(frozen=True)
class TimestampedFile:
    """A prunable ``.json`` file whose filename encodes a snapshot instant."""

    path: Path
    group: str
    timestamp: datetime
    size_bytes: int


@dataclass(frozen=True)
class PruneAction:
    """A single planned deletion produced by :func:`plan_prune`."""

    path: Path
    group: str
    timestamp: datetime
    size_bytes: int


@dataclass
class PruneReport:
    """Outcome of a retention pass (dry-run or apply)."""

    dry_run: bool
    keep_last: int = 0
    planned: int = 0
    deleted: int = 0
    failed: int = 0
    skipped_unparseable: int = 0
    bytes_planned: int = 0
    bytes_freed: int = 0
    planned_at: datetime | None = None
    per_prefix: dict[str, dict[str, int]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def parse_snapshot_filename(filename: str) -> tuple[datetime, str, str] | None:
    """Extract the snapshot timestamp from a filename.

    Supported token shapes (delimited by non-digits): ``YYYYMMDD_HHMMSS``,
    ``YYYYMMDDHHMMSS``, ``YYYY_MM_DD_HHMMSS``, ``YYYY-MM-DD`` and
    ``YYYY-MM-DD[THH:MM:SS]``. The first pattern that matches *and* yields a
    valid calendar date wins; a regex match with an impossible date (e.g.
    month 13) is discarded and later patterns are tried.

    Args:
        filename: Bare filename (no directories), e.g.
            ``stack_releases_20260828_100626.json``.

    Returns:
        Tuple of ``(timestamp, prefix, suffix)`` where *prefix* is the stable
        part before the timestamp token and *suffix* everything after it
        (including the extension), or ``None`` when no valid timestamp is
        found.
    """
    for pattern in _TIMESTAMP_PATTERNS:
        match = pattern.search(filename)
        if not match:
            continue
        parts = [int(group) if group else 0 for group in match.groups()]
        year, month, day = parts[0], parts[1], parts[2]
        hour, minute, second = (parts[3], parts[4], parts[5]) if len(parts) >= 6 and parts[3] else (0, 0, 0)
        try:
            timestamp = datetime(year, month, day, hour, minute, second)
        except ValueError:
            continue
        prefix = filename[: match.start()].rstrip("_-. ")
        suffix = filename[match.end() :]
        return timestamp, prefix, suffix
    return None


def _safe_size(path: Path) -> int:
    """Return the file size in bytes, or 0 when the file cannot be stat'ed.

    Args:
        path: File to measure.

    Returns:
        Size in bytes (0 on OSError).
    """
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _scan_timestamped_files(data_dir: Path) -> tuple[list[TimestampedFile], int]:
    """Walk ``data_dir`` and collect every prunable timestamped JSON file.

    Skips (without counting as skipped) everything that is protected by
    design: non-``.json`` files, ``data/watchers/**``, filenames containing
    ``latest``, and state files. Files that look timestamped but carry an
    unparseable/invalid token are counted as skipped so the report can flag
    them.

    Args:
        data_dir: Root data directory to walk (already resolved).

    Returns:
        Tuple of (timestamped files, unparseable-skip count).
    """
    files: list[TimestampedFile] = []
    skipped_unparseable = 0
    if not data_dir.is_dir():
        logger.warning("Data directory %s does not exist; nothing to scan.", data_dir)
        return files, skipped_unparseable

    for path in sorted(data_dir.rglob("*.json")):
        if not path.is_file():
            continue
        relative = path.relative_to(data_dir)
        if relative.parts[0].lower() in _SKIPPED_TOP_LEVEL_DIRS:
            continue
        name = path.name
        if "latest" in name.lower():
            continue
        if name.lower() in _PROTECTED_NAMES:
            continue
        parsed = parse_snapshot_filename(name)
        if parsed is None:
            skipped_unparseable += 1
            logger.debug("Skipping file without parseable timestamp: %s", relative.as_posix())
            continue
        timestamp, prefix, suffix = parsed
        group = f"{relative.parent.as_posix()}::{prefix}::{suffix}"
        files.append(TimestampedFile(path=path, group=group, timestamp=timestamp, size_bytes=_safe_size(path)))
    return files, skipped_unparseable


def _plan_from_files(files: list[TimestampedFile], keep_last: int) -> list[PruneAction]:
    """Build prune actions keeping the newest ``keep_last`` files per group.

    Args:
        files: Timestamped files collected by the scanner.
        keep_last: Number of newest files to retain per group (>= 1).

    Returns:
        Sorted list of prune actions, oldest first within each group.

    Raises:
        ValueError: If ``keep_last`` is less than 1 (deleting all history is
            never allowed).
    """
    if keep_last < 1:
        raise ValueError(f"keep_last must be >= 1 (got {keep_last}); refusing to plan a full purge")
    groups: dict[str, list[TimestampedFile]] = {}
    for snapshot_file in files:
        groups.setdefault(snapshot_file.group, []).append(snapshot_file)

    actions: list[PruneAction] = []
    for group, members in groups.items():
        members.sort(key=lambda f: (f.timestamp, f.path.name), reverse=True)
        for member in members[keep_last:]:
            actions.append(PruneAction(path=member.path, group=group, timestamp=member.timestamp, size_bytes=member.size_bytes))
    actions.sort(key=lambda action: (action.group, action.timestamp))
    return actions


def plan_prune(data_dir: str | Path, keep_last: int = 30, now: datetime | None = None) -> list[PruneAction]:
    """Plan (but do not execute) a keep-the-newest-N prune of ``data_dir``.

    Pure planning function: it only reads the filesystem, never deletes.
    Everything that is protected by design (``*_latest.json``, run summaries
    marked latest, state files, ``data/watchers/**``, non-JSON files, files
    without a parseable timestamp) is never considered and never appears in
    the returned actions.

    Args:
        data_dir: Root data directory to walk (e.g. ``<project_root>/data``).
        keep_last: Number of newest files to retain per prefix group (>= 1).
        now: Optional reference time, recorded for logging/reporting only;
            selection is purely by per-group newest-N ranking.

    Returns:
        List of :class:`PruneAction` describing the files that would be
        deleted.

    Raises:
        ValueError: If ``keep_last`` is less than 1 (deleting all history is
            never allowed).
    """
    if keep_last < 1:
        raise ValueError(f"keep_last must be >= 1 (got {keep_last}); refusing to plan a full purge")
    files, _skipped = _scan_timestamped_files(Path(data_dir).resolve())
    actions = _plan_from_files(files, keep_last)
    logger.info(
        "Planned prune of %d file(s) across %d group(s) with keep_last=%d (scanned %d timestamped file(s))",
        len(actions),
        len({action.group for action in actions}),
        keep_last,
        len(files),
    )
    return actions


def apply_prune(actions: list[PruneAction], dry_run: bool = True) -> PruneReport:
    """Execute (or simulate) a list of prune actions.

    Each action is re-checked before deletion — defense in depth against
    hand-built action lists: only ``.json`` files whose name does not contain
    ``latest`` are ever unlinked. Deletion errors are recorded in the report
    instead of aborting the pass.

    Args:
        actions: Actions returned by :func:`plan_prune`.
        dry_run: When True (default) nothing is deleted; actions are only
            counted and sized.

    Returns:
        :class:`PruneReport` with per-prefix breakdown, file counts and bytes.
    """
    report = PruneReport(dry_run=dry_run)
    for action in actions:
        name = action.path.name.lower()
        if not name.endswith(".json") or "latest" in name:
            report.failed += 1
            report.errors.append(f"Refused unsafe prune target: {action.path}")
            continue

        group_stats = report.per_prefix.setdefault(action.group, {"planned": 0, "deleted": 0, "bytes_planned": 0, "bytes_freed": 0})
        report.planned += 1
        group_stats["planned"] += 1
        size_bytes = action.size_bytes
        if dry_run:
            report.bytes_planned += size_bytes
            group_stats["bytes_planned"] += size_bytes
            continue

        try:
            if action.path.exists():
                size_bytes = action.path.stat().st_size
            action.path.unlink(missing_ok=True)
            report.deleted += 1
            report.bytes_freed += size_bytes
            group_stats["deleted"] += 1
            group_stats["bytes_freed"] += size_bytes
        except OSError as exc:
            report.failed += 1
            report.errors.append(f"Failed to delete {action.path}: {exc}")
            logger.warning("Failed to delete %s: %s", action.path, exc)
    return report


def run_retention(data_dir: str | Path, keep_last: int = 30, dry_run: bool = True, now: datetime | None = None) -> PruneReport:
    """Convenience wrapper: scan, plan and apply one retention pass.

    Args:
        data_dir: Root data directory to prune.
        keep_last: Number of newest files to retain per prefix group (>= 1).
        dry_run: When True (default) nothing is deleted.
        now: Optional reference time recorded in the report.

    Returns:
        :class:`PruneReport` including the unparseable-skip count.

    Raises:
        ValueError: If ``keep_last`` is less than 1.
    """
    resolved = Path(data_dir).resolve()
    files, skipped_unparseable = _scan_timestamped_files(resolved)
    actions = _plan_from_files(files, keep_last)
    report = apply_prune(actions, dry_run=dry_run)
    report.keep_last = keep_last
    report.skipped_unparseable = skipped_unparseable
    report.planned_at = now or datetime.now()
    return report


def _format_bytes(size_bytes: int) -> str:
    """Format a byte count for humans (e.g. ``1.5 MB``).

    Args:
        size_bytes: Byte count.

    Returns:
        Human-readable size string.
    """
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def _str2bool(value: str | bool) -> bool:
    """Parse a CLI boolean flag value.

    Args:
        value: Raw argument such as ``true``, ``false``, ``1``, ``0``, ``yes``.

    Returns:
        Parsed boolean.

    Raises:
        argparse.ArgumentTypeError: If the value is not recognized.
    """
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True
    if normalized in {"false", "0", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Expected a boolean value, got {value!r}")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the snapshot retention pruner.

    Args:
        argv: Argument vector (defaults to ``sys.argv[1:]``); injectable for
            tests.

    Returns:
        Process exit code: 0 on success, 1 if any deletion failed.
    """
    parser = argparse.ArgumentParser(
        prog="python -m src.utils.snapshot_retention",
        description="Prune old timestamped JSON snapshots under data/, keeping the newest N per prefix. Dry-run by default; deletion requires --apply.",
    )
    parser.add_argument("--data-dir", type=Path, default=None, help="Data directory to prune (default: <project_root>/data).")
    parser.add_argument("--keep-last", type=int, default=30, help="Number of newest timestamped files to keep per prefix group (default: 30).")
    parser.add_argument("--dry-run", type=_str2bool, nargs="?", const=True, default=True, help="Dry-run switch, true by default. Pass --dry-run=false to delete.")
    parser.add_argument("--apply", action="store_true", help="Shorthand for --dry-run=false: actually delete pruned files.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    dry_run = args.dry_run and not args.apply
    data_dir = args.data_dir if args.data_dir is not None else Path(get_project_root()) / "data"
    if not dry_run:
        logger.info("APPLY mode: files beyond the newest %d per prefix under %s WILL be deleted.", args.keep_last, data_dir)
    else:
        logger.info("DRY-RUN mode (default): no files will be deleted. Pass --apply to prune for real.")

    try:
        report = run_retention(data_dir, keep_last=args.keep_last, dry_run=dry_run)
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    mode = "dry-run" if report.dry_run else "APPLY"
    logger.info("Snapshot retention (%s): keep_last=%d, data_dir=%s", mode, report.keep_last, data_dir)
    logger.info(
        "Prune candidates: %d file(s) (%s) | deleted: %d (%s freed) | failed: %d | skipped (no parseable timestamp): %d",
        report.planned,
        _format_bytes(report.bytes_planned),
        report.deleted,
        _format_bytes(report.bytes_freed),
        report.failed,
        report.skipped_unparseable,
    )
    if report.per_prefix:
        ranked = sorted(report.per_prefix.items(), key=lambda item: item[1]["bytes_planned"] or item[1]["bytes_freed"], reverse=True)
        logger.info("Per-prefix breakdown (top %d of %d group(s)):", min(10, len(ranked)), len(ranked))
        for group, stats in ranked[:10]:
            size = stats["bytes_freed"] if not report.dry_run else stats["bytes_planned"]
            logger.info("  %s: %d file(s), %s", group, stats["deleted"] if not report.dry_run else stats["planned"], _format_bytes(size))
    for error in report.errors:
        logger.error("  %s", error)
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
