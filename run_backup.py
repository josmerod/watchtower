#!/usr/bin/env python3
"""Local backup with restore verification (T-090, T-106).

"Un backup no verificado no es un backup" — this script does four things:

1. Zips ``data/`` + ``logs/`` into ``backups/backup_data_logs_{ts}.zip``
   (``backups/`` is gitignored; in the container it is a volume of its own).
   The archive is written under ``.part`` and renamed once it is closed, so
   a run that is interrupted leaves no half archive behind.
2. **Verifies** the archive can actually be restored: the zip opens, the
   critical ``*_latest.json`` outputs are present, and sampled JSON files
   parse. Writes the report to ``backups/last_verification.json``. An
   archive that does not verify is renamed ``.zip.failed`` and kept for
   inspection until the next run: every ``backup_data_logs_*.zip`` in the
   folder has verified.
3. Prunes old local backups (keep ``--keep``, default 7: a week at one
   archive a day).
4. Prints a last line ``BACKUP_RESULT {...}`` with what happened, which the
   ETL orchestrator repeats in its own log.

With ``--max-age-hours N`` the run is skipped (exit 0) when the newest
archive verified and is younger than N hours; ``--force`` runs anyway. The
orchestrator calls this script that way after every full cycle, so an
archive is made about once a day.

If Google Drive is fully configured (``google_drive.backup_folder_id``,
credentials file and pydrive2 present) the legacy
:meth:`src.utils.backup_utils.BackupManager.run_backup_process` upload flow
also runs — best-effort, never fatal to the local backup.

Exit codes: 0 when the archive verified or the run was skipped, 1 when
there was nothing to back up, 2 when the archive did not verify.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.backup_utils import add_folder_to_zip
from src.utils.file_system import get_project_root
from src.utils.logging import get_logger

logger = get_logger("RunBackup")

BACKUP_DIR_NAME = "backups"
ARCHIVE_PREFIX = "backup_data_logs"
VERIFICATION_FILE = "last_verification.json"
DEFAULT_FOLDERS = ("data", "logs")
DEFAULT_KEEP = 7
# Sample at most this many .json entries per archive for the parse check.
MAX_JSON_SAMPLES = 20
# An archive is written under this suffix and renamed once it is closed.
PART_SUFFIX = ".part"
# An archive that did not verify: kept for inspection, never counted as a backup.
FAILED_SUFFIX = ".zip.failed"
# The orchestrator reads the last line that starts with this.
RESULT_PREFIX = "BACKUP_RESULT "


def finished_archives(backup_dir: Path) -> list[Path]:
    """The archives under ``backup_dir``, newest first; partial and failed files are not archives."""
    return sorted(backup_dir.glob(f"{ARCHIVE_PREFIX}_*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)


def remove_stale_files(backup_dir: Path) -> None:
    """Drop what earlier runs left: an interrupted archive, and the failed archive of the last run."""
    for stale in [*backup_dir.glob(f"{ARCHIVE_PREFIX}_*{PART_SUFFIX}"), *backup_dir.glob(f"{ARCHIVE_PREFIX}_*{FAILED_SUFFIX}")]:
        stale.unlink(missing_ok=True)


def read_report(report_path: Path) -> dict[str, Any]:
    """The last verification report, or ``{}`` when there is none or it cannot be read."""
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return report if isinstance(report, dict) else {}


def skip_reason(project_root: Path, max_age_hours: float) -> str:
    """Why a run with ``--max-age-hours`` can do nothing; ``""`` when it cannot.

    Only an archive that verified counts: the run is skipped when the newest
    one is younger than ``max_age_hours`` and the last report names it.

    Args:
        project_root: Root whose ``backups/`` folder is looked at.
        max_age_hours: Age from which a new archive is due.

    Returns:
        Human-readable reason, or ``""`` when a backup has to be made.
    """
    archives = finished_archives(project_root / BACKUP_DIR_NAME)
    if not archives:
        return ""
    age_hours = (time.time() - archives[0].stat().st_mtime) / 3600
    if age_hours >= max_age_hours:
        return ""
    report = read_report(project_root / BACKUP_DIR_NAME / VERIFICATION_FILE)
    if not (report.get("ok") is True and report.get("archive") == archives[0].name):
        return ""
    return f"the newest verified archive is {age_hours:.1f} h old (limit {max_age_hours:g} h)"


def create_local_backup(project_root: Path, folders: tuple[str, ...] = DEFAULT_FOLDERS) -> Path | None:
    """Zip the given folders into ``backups/backup_data_logs_{ts}.zip``.

    The archive only gets that name once it is closed: while it is being
    written it ends in ``.part``, and the stale files of earlier runs go
    first.

    Args:
        project_root: Root whose folders are archived (arcnames stay relative).
        folders: Folder names relative to the project root.

    Returns:
        Path to the created archive, or None when nothing could be added.
    """
    backup_dir = project_root / BACKUP_DIR_NAME
    backup_dir.mkdir(parents=True, exist_ok=True)
    remove_stale_files(backup_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = backup_dir / f"{ARCHIVE_PREFIX}_{timestamp}.zip"
    partial_path = archive_path.with_name(archive_path.name + PART_SUFFIX)

    file_count = 0
    with zipfile.ZipFile(partial_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zipf:
        for folder in folders:
            file_count += add_folder_to_zip(zipf, Path(folder), project_root)

    if file_count == 0:
        logger.warning(f"Backup archive {archive_path.name} is empty — no files under {folders}")
        partial_path.unlink(missing_ok=True)
        return None

    partial_path.replace(archive_path)
    size_mb = archive_path.stat().st_size / (1024 * 1024)
    logger.info(f"Created {archive_path.name}: {file_count} files, {size_mb:.1f} MiB")
    return archive_path


def verify_backup(archive_path: Path, max_json_samples: int = MAX_JSON_SAMPLES) -> dict:
    """Smoke-verify that the archive can be restored ("un backup no verificado no es un backup").

    Checks, in order: the zip opens (CRC check on read), it contains at least
    one ``*_latest.json`` critical output, and sampled ``.json`` entries parse.

    Args:
        archive_path: The backup archive to verify.
        max_json_samples: Cap on how many .json entries are parsed.

    Returns:
        Report dict: ``ok`` plus the evidence fields (file counts, critical
        files found, samples validated, errors).
    """
    report: dict = {"archive": archive_path.name, "ok": False, "errors": []}
    try:
        with zipfile.ZipFile(archive_path) as zipf:
            bad_file = zipf.testzip()
            if bad_file is not None:
                report["errors"].append(f"CRC check failed on {bad_file}")
                return report
            names = zipf.namelist()
    except (zipfile.BadZipFile, OSError) as exc:
        report["errors"].append(f"Cannot open archive: {exc}")
        return report

    report["file_count"] = len(names)
    critical = [n for n in names if n.endswith("_latest.json")]
    report["critical_latest_count"] = len(critical)
    report["critical_latest_sample"] = critical[:5]
    if not critical:
        report["errors"].append("no *_latest.json outputs found — backup of an empty/stale data tree")

    validated = 0
    with zipfile.ZipFile(archive_path) as zipf:
        for name in [n for n in names if n.endswith(".json")][:max_json_samples]:
            try:
                json.loads(zipf.read(name).decode("utf-8"))
                validated += 1
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                report["errors"].append(f"invalid JSON in {name}: {exc}")
    report["json_samples_validated"] = validated
    report["ok"] = not report["errors"]
    return report


def prune_local_backups(backup_dir: Path, keep: int = DEFAULT_KEEP) -> int:
    """Keep only the newest ``keep`` ``backup_data_logs_*.zip`` archives.

    Args:
        backup_dir: Directory holding the local backups.
        keep: How many archives to keep.

    Returns:
        Number of archives deleted.
    """
    removed = 0
    for old in finished_archives(backup_dir)[keep:]:
        old.unlink(missing_ok=True)
        removed += 1
        logger.info(f"Pruned old backup {old.name}")
    return removed


def upload_to_gdrive_best_effort(project_root: Path) -> bool:
    """Run the legacy Google-Drive upload when fully configured; never fatal.

    Args:
        project_root: Project root (credentials are resolved from settings).

    Returns:
        True when the upload ran and succeeded, False otherwise (including
        "not configured", which is logged at INFO, not as an error).
    """
    try:
        from src.config.settings import get_settings
        from src.utils.backup_utils import BackupManager
    except ImportError as exc:
        logger.info(f"GDrive upload skipped (import failure): {exc}")
        return False

    try:
        settings = get_settings()
        folder_id = settings.google_drive.backup_folder_id
        credentials = Path(settings.google_drive.credentials_file)
        if not credentials.is_absolute():
            credentials = project_root / credentials
        if not folder_id or not credentials.exists():
            logger.info("GDrive upload skipped (no backup_folder_id or credentials file)")
            return False

        manager = BackupManager(settings)
        return bool(manager.run_backup_process(list(DEFAULT_FOLDERS)))
    except Exception as exc:  # upload must never fail the local backup
        logger.warning(f"GDrive upload failed (local verified backup is unaffected): {exc}")
        return False


def report_result(status: str, **fields: Any) -> None:
    """Print the line the orchestrator reads: one JSON object, its status first."""
    print(RESULT_PREFIX + json.dumps({"status": status, **fields}, ensure_ascii=False), flush=True)


def main(argv: list[str] | None = None) -> int:
    """Run the backup + verification cycle.

    Args:
        argv: CLI arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code: 0 when the archive verified or the run was
        skipped, 1 when there was nothing to back up, 2 when the archive
        did not verify.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP, help=f"local archives to keep (default {DEFAULT_KEEP})")
    parser.add_argument("--max-age-hours", type=float, default=0.0, help="do nothing when the newest verified archive is younger than this many hours (default: always back up)")
    parser.add_argument("--force", action="store_true", help="back up even when --max-age-hours would skip")
    parser.add_argument("--no-gdrive", action="store_true", help="skip the best-effort Google Drive upload")
    args = parser.parse_args(argv)

    project_root = Path(get_project_root())
    backup_dir = project_root / BACKUP_DIR_NAME

    if not args.force and args.max_age_hours > 0:
        reason = skip_reason(project_root, args.max_age_hours)
        if reason:
            logger.info(f"Backup skipped: {reason}")
            report_result("skipped", reason=reason)
            return 0

    logger.info(f"Starting local backup of {DEFAULT_FOLDERS} under {project_root}")

    archive = create_local_backup(project_root)
    if archive is None:
        logger.error("Backup aborted: no files to back up")
        report_result("failed", reason="no files to back up")
        return 1

    report = verify_backup(archive)
    if not report["ok"]:
        # Out of the way of the next run and of a restore, but there to look at.
        failed_path = archive.with_name(archive.name + FAILED_SUFFIX)
        archive.replace(failed_path)
        report["kept_as"] = failed_path.name
    (backup_dir / VERIFICATION_FILE).write_text(json.dumps(report, indent=2), encoding="utf-8")

    pruned = prune_local_backups(backup_dir, keep=args.keep)
    logger.info(
        f"Verification {'PASSED' if report['ok'] else 'FAILED'} ({report.get('file_count', 0)} files, "
        f"{report.get('critical_latest_count', 0)} _latest outputs, "
        f"{report.get('json_samples_validated', 0)} JSON samples OK); pruned {pruned} old archives"
    )

    if report["ok"]:
        report_result("created", archive=archive.name, size_mib=round(archive.stat().st_size / (1024 * 1024), 1), files=report.get("file_count"), verified=True)
    else:
        report_result("failed", archive=report["archive"], errors=report["errors"][:3], kept_as=report.get("kept_as"))

    if not args.no_gdrive:
        upload_to_gdrive_best_effort(project_root)

    return 0 if report["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
