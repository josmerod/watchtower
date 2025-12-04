"""Post-run sanity check for ETL outputs.

Reads expected `*_latest.json` artifacts and writes a compact summary to
`data/metrics/etl_runs_latest.json` for the dashboard and ops visibility.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ArtifactStatus:
    name: str
    exists: bool
    record_count: int
    modified_utc: str | None
    path: str
    notes: str | None = None


def _safe_stat_mtime(path: Path) -> str | None:
    try:
        return datetime.utcfromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
    except Exception:
        return None


def _count_records(data: Any) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("items", "articles", "results", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return len(value)
    return 0


def _read_json(path: Path) -> Any | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def build_summary() -> dict[str, Any]:
    base = Path("data")
    expected = {
        "product_hunt": base / "product_hunt" / "product_hunt_latest.json",
        "github_trends": base / "github_trends" / "github_trends_latest.json",
        "arxiv_papers": base / "arxiv" / "arxiv_papers_latest.json",
        "free_games": base / "giveaways" / "free_games_latest.json",
    }

    statuses: list[ArtifactStatus] = []
    for name, path in expected.items():
        exists = path.exists()
        modified = _safe_stat_mtime(path) if exists else None
        count = 0
        notes = None
        if exists:
            data = _read_json(path)
            if data is None:
                count = -1
                notes = "json_error"
            else:
                count = _count_records(data)
        statuses.append(
            ArtifactStatus(
                name=name,
                exists=exists,
                record_count=count,
                modified_utc=modified,
                path=str(path),
                notes=notes,
            )
        )

    summary = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
        "artifacts": [asdict(s) for s in statuses],
    }
    return summary


def write_summary(summary: dict[str, Any]) -> Path:
    out_dir = Path("data/metrics")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "etl_runs_latest.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return out_path


def main() -> None:
    summary = build_summary()
    out_path = write_summary(summary)
    print(f"Wrote ETL sanity summary to {out_path}")


if __name__ == "__main__":
    main()
