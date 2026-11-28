"""Check the shape of the Watchtower task documents before they are committed.

Usage, from the repository root::

    python .agents/skills/task-board/scripts/board_check.py [--today YYYY-MM-DD]

It reads ``docs/TASK_BOARD.md``, ``docs/TASK_BOARD_ARCHIVE.md`` and ``docs/FEEDBACK.md`` and reports, with file and line: a row without its six cells or with a Status, Priority or Area outside the list; a ``done`` row on the board or more than one ``in-progress``; a board not sorted as its conventions say; an archive row that is not ``done``; an ID on both files; a changelog that is not newest first or still holds an entry older than two months. It then prints the counts and the next free ID.

Why: the SessionStart hook parses the board with a regex, and one stray pipe — or a ``|`` inside a cell that was not written ``\\|`` — breaks the digest of every session. It needs only the standard library and fixes nothing.
"""

import argparse
import re
import sys
from datetime import date, timedelta
from itertools import pairwise
from pathlib import Path

STATUSES = ("todo", "in-progress", "blocked", "done")
PRIORITIES = ("P0", "P1", "P2", "P3")
AREAS = ("etl", "dashboard", "api", "infra", "quality", "docs", "sec")
TABLES = {"TASK_BOARD.md": "## Board", "TASK_BOARD_ARCHIVE.md": "## Tareas cerradas"}
ROW_ID = re.compile(r"T-\d{3,}$")
CHANGELOG_LINE = re.compile(r"^- (\d{4}-\d{2}-\d{2}) — ")
TWO_MONTHS = timedelta(days=62)


def split_cells(line: str) -> list[str]:
    """The cells of a table row: split on the pipes that separate cells, not on an escaped one."""
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def well_formed(cells: list[str]) -> bool:
    """Whether a row can be judged without guessing: six cells and an ID in the first."""
    return len(cells) == 6 and bool(ROW_ID.match(cells[0]))


def section_rows(lines: list[str], heading: str) -> list[tuple[int, list[str]]]:
    """The table rows under ``heading``, with their line numbers; the header and its separator are left out."""
    rows: list[tuple[int, list[str]]] = []
    inside = False
    for number, line in enumerate(lines, start=1):
        if line.startswith("## "):
            inside = line.strip() == heading
            continue
        if inside and line.lstrip().startswith("|"):
            cells = split_cells(line)
            if cells and cells[0] != "ID" and not set(cells[0]) <= set(":-"):
                rows.append((number, cells))
    return rows


def check_row(file: str, number: int, cells: list[str], where: str, problems: list[str]) -> None:
    """Report what is wrong with one row."""
    place = f"docs/{file}:{number}"
    if len(cells) != 6:
        problems.append(f"{place}: row has {len(cells)} cells, expected 6 — an unescaped pipe?")
        return
    if not ROW_ID.match(cells[0]):
        problems.append(f"{place}: first cell is {cells[0]!r}, expected an ID like T-123")
        return
    task_id, status, priority, title, area, _notes = cells
    if status not in STATUSES:
        problems.append(f"{place}: {task_id} has Status {status!r}, expected one of {', '.join(STATUSES)}")
    if priority not in PRIORITIES:
        problems.append(f"{place}: {task_id} has Priority {priority!r}, expected one of {', '.join(PRIORITIES)}")
    if area not in AREAS:
        problems.append(f"{place}: {task_id} has Area {area!r}, expected one of {', '.join(AREAS)}")
    if not title:
        problems.append(f"{place}: {task_id} has an empty Title")
    if where == "board" and status == "done":
        problems.append(f"{place}: {task_id} is done on the board — move the whole row to the archive")
    if where == "archive" and status != "done":
        problems.append(f"{place}: {task_id} is in the archive with Status {status!r}")


def sort_key(cells: list[str]) -> tuple[int, int, int]:
    """The position a well-formed open row should have: in-progress, then todo by priority and oldest first, then blocked."""
    rank = {"in-progress": 0, "todo": 1, "blocked": 2}
    return rank.get(cells[1], 3), PRIORITIES.index(cells[2]) if cells[2] in PRIORITIES else 9, int(cells[0][2:])


def check_sort(board: list[tuple[int, list[str]]], problems: list[str]) -> None:
    """Report the first open row that sits below one it should precede."""
    judged = [(number, cells) for number, cells in board if well_formed(cells) and cells[1] in ("in-progress", "todo", "blocked")]
    for (_, previous), (number, cells) in pairwise(judged):
        if sort_key(cells) < sort_key(previous):
            problems.append(f"docs/TASK_BOARD.md:{number}: {cells[0]} sits below {previous[0]} — sort in-progress, then todo by priority and oldest first, then blocked")
            return


def check_changelog(lines: list[str], today: date, problems: list[str]) -> None:
    """The board's changelog: dated lines, newest first, nothing older than two months."""
    inside = False
    previous: str | None = None
    for number, line in enumerate(lines, start=1):
        if line.startswith("## "):
            inside = line.strip() == "## Changelog"
            continue
        if not inside or not line.startswith("- "):
            continue
        match = CHANGELOG_LINE.match(line)
        if not match:
            problems.append(f"docs/TASK_BOARD.md:{number}: changelog line does not start with '- YYYY-MM-DD — '")
            continue
        if previous is not None and match[1] > previous:
            problems.append(f"docs/TASK_BOARD.md:{number}: changelog is not newest first ({match[1]} after {previous})")
        if date.fromisoformat(match[1]) < today - TWO_MONTHS:
            problems.append(f"docs/TASK_BOARD.md:{number}: entry of {match[1]} is older than two months — move it verbatim to '## Changelog histórico' in the archive")
        previous = match[1]


def main() -> int:
    """Check the documents and print what is wrong; exit 1 when something is."""
    # A message carries what a row holds, and a pipe on Windows encodes it with the code page of the machine: a
    # character outside it would stop the check on the very row it reports. Write UTF-8 whatever the locale is.
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--today", default=date.today().isoformat(), help="the date to judge the changelog against (default: today)")
    options = parser.parse_args()
    docs = Path("docs")
    problems: list[str] = []
    seen: dict[str, str] = {}
    open_rows: list[tuple[int, list[str]]] = []
    archived = 0

    for file, heading in TABLES.items():
        lines = (docs / file).read_text(encoding="utf-8").splitlines()
        where = "board" if file == "TASK_BOARD.md" else "archive"
        rows = section_rows(lines, heading)
        if not rows:
            problems.append(f"docs/{file}: no table found under '{heading}'")
        for number, cells in rows:
            check_row(file, number, cells, where, problems)
            if not well_formed(cells):
                continue
            if cells[0] in seen:
                problems.append(f"docs/{file}:{number}: {cells[0]} is also on docs/{seen[cells[0]]}")
            seen[cells[0]] = file
        if where == "board":
            open_rows = rows
            if sum(cells[1] == "in-progress" for _number, cells in rows) > 1:
                problems.append(f"docs/{file}: more than one row is in-progress — one at a time")
            check_sort(rows, problems)
            check_changelog(lines, date.fromisoformat(options.today), problems)
        else:
            archived = len(rows)

    for problem in problems:
        print(problem)
    statuses = [cells[1] for _number, cells in open_rows if well_formed(cells)]
    highest = max((int(task_id[2:]) for task_id in seen), default=0)
    verdict = "OK" if not problems else f"{len(problems)} problem(s)"
    print(
        f"\n{verdict} — board: {len(open_rows)} open ({statuses.count('todo')} todo, {statuses.count('in-progress')} in-progress, "
        f"{statuses.count('blocked')} blocked) · archive: {archived} rows · next free ID T-{highest + 1:03d}"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
