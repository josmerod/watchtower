# Backups in production

`run_backup.py` ships and the orchestrator runs it after every cycle with
`--max-age-hours 20`: an archive is made only when the newest verified one is
older than that — about one a day. It zips `data/` and `logs/` into the
`backups` volume (`BACKUP_VOLUME` in `deployment/deploy.py`, mounted at
`/app/backups`), verifies it — the zip opens, `*_latest.json` outputs are
present, JSON samples parse — and keeps the last 7. **Same disk as the
data:** a copy against a mistake, not against a disk failure. There is no
off-site copy (the Google Drive path needs a folder id and credentials the
user has not provided).

## Read the result

- The scheduler log ends each cycle with a `Backup …` line: `created <archive>
  (<size> MiB, <n> files, verified)`, `skipped: the newest verified archive
  is N h old`, or `failed: …` — then read `logs/backup_process.log` in the
  container. A cycle without the line means the script did not run at all.
- On the server, `ls -la` the backups volume: the archives and
  `last_verification.json`. Every `backup_data_logs_*.zip` there verified
  when it was made. A `*.zip.failed` is one that did not (kept for
  inspection until the next run); a `*.part` is an interrupted run.
- Do not report backups as working from a green test alone: after a deploy
  that touches `run_backup.py`, the orchestrator's backup step or the
  volumes, read the `Backup …` line of the first cycle.

## Restore

The dashboard and the API stay down while it runs:

1. Unzip with the image's Python into a staging folder on the array (not
   `/tmp`, which is a RAM disk, and not the volume itself):
   ```bash
   docker run --rm --name watchtower-restore \
      -v /mnt/user/appdata/watchtower/backups:/backup:ro \
      -v /mnt/user/appdata/watchtower-restore:/restore \
      --entrypoint python watchtower:latest \
      -m zipfile -e /backup/backup_data_logs_<timestamp>.zip /restore
   ```
   The archive holds `data/` and `logs/` at its root; `/restore` must show
   the two before going on.
2. `docker stop watchtower`.
3. Move the damaged folder aside, never delete it:
   `mv /mnt/user/appdata/watchtower/data /mnt/user/appdata/watchtower/data.broken-$(date +%F)`.
4. `mv /mnt/user/appdata/watchtower-restore/data /mnt/user/appdata/watchtower/data`
   (same disk, so it is a rename). Restore `logs` the same way only when
   that folder is damaged too.
5. `docker start watchtower`, wait for `healthy`, open one tab. The start
   launches a full cycle, which rewrites the `*_latest.json` outputs.
6. Remove the staging folder once the tab shows data.
