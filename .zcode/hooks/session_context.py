"""SessionStart hook for ZCode: print a short digest of the repository state.

Wired in ``.zcode/config.json``. ZCode runs it on ``startup``, ``resume``,
``clear`` and ``compact`` and injects what it prints as context, so every
session starts knowing the same things without relying on agent memory:

- which branch is checked out and how far it is from ``origin/main``
- whether this clone has the git hooks installed (a fresh clone has not)
- the task ``docs/TASK_BOARD.md`` marks ``in-progress``
- entries of ``docs/FEEDBACK.md`` still waiting to be triaged

Fail-open by contract: read-only, standard library only, and on any problem it
prints nothing and exits 0 — a broken digest must never block or slow down a
session. The only output it ever produces is the SessionStart JSON or nothing.
ZCode validates that JSON strictly, so nothing else may reach stdout.

Run it by hand with::

    uv run --no-project python .zcode/hooks/session_context.py .
"""

import json
import os
import re
import subprocess
import sys

GIT_TIMEOUT_SECONDS = 3
BOARD_ROW = re.compile(r"^\|\s*(T-\d+)\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|\s*(.+?)\s*\|")
UNCHECKED = re.compile(r"^\s*[-*] \[ \]")
PRE_COMMIT_HOOKS = ("pre-commit", "pre-push")


def git(root: str, *args: str) -> str | None:
    """Return the stdout of a read-only git command, or None when it fails.

    Nothing is stripped: ``git status --porcelain`` encodes the state in the
    first two columns, so leading blanks are part of the answer.
    """
    command = ["git", "--no-optional-locks", "-C", root, *args]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT_SECONDS, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def count(total: int, singular: str, plural: str) -> str:
    """Return ``"1 entry"`` or ``"2 entries"``: English plurals are not mechanical."""
    return f"{total} {singular if total == 1 else plural}"


def parse_status(status: str | None) -> list[str]:
    """Return the ``XY path`` entries of ``git status --porcelain -z``.

    The ``-z`` form never quotes a path. A rename or a copy adds a second entry
    holding the original path, which is skipped here.
    """
    changed = []
    fields = status.split("\0") if status else []
    index = 0
    while index < len(fields) and fields[index]:
        changed.append(fields[index])
        index += 2 if fields[index][0] in "RC" else 1
    return changed


def git_lines(root: str) -> list[str]:
    """Branch, distance to the integration branch and uncommitted changes."""
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch is None:
        return ["Not a git repository."]
    branch = branch.strip()
    lines = ["Detached HEAD: no branch is checked out." if branch == "HEAD" else f"On branch {branch}."]

    base = next((name for name in ("origin/main", "main") if git(root, "rev-parse", "--verify", "--quiet", name) is not None), None)
    counts = git(root, "rev-list", "--left-right", "--count", f"{base}...HEAD") if base else None
    if counts is not None:
        behind, ahead = counts.split()
        lines.append(f"{count(int(ahead), 'commit', 'commits')} ahead of and {behind} behind {base}.")

    status = git(root, "status", "--porcelain", "-z")
    changed = parse_status(status)
    if changed:
        names = ", ".join(entry[3:] for entry in changed[:5]) + (f" (+{len(changed) - 5} more)" if len(changed) > 5 else "")
        tracked = [entry for entry in changed if not entry.startswith("??")]
        noise = " — tracked files differ only in line endings (CRLF noise)" if tracked and git(root, "diff", "--ignore-cr-at-eol", "--quiet") is not None else ""
        lines.append(f"{count(len(changed), 'uncommitted change', 'uncommitted changes')}{noise}: {names}")
    else:
        lines.append("Working tree clean.")

    git_dir = git(root, "rev-parse", "--absolute-git-dir")
    common_dir = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if git_dir and common_dir and git_dir.strip() != common_dir.strip():
        lines.append("This is a git worktree, not the main clone.")
    return lines


def hook_lines(root: str) -> list[str]:
    """Warn when the pre-commit hooks are not installed in this clone."""
    if not os.path.isfile(os.path.join(root, ".pre-commit-config.yaml")):
        return []
    hooks_dir = git(root, "rev-parse", "--path-format=absolute", "--git-path", "hooks")
    if hooks_dir is None:
        return []
    hooks_dir = hooks_dir.strip()
    missing = [name for name in PRE_COMMIT_HOOKS if not os.path.isfile(os.path.join(hooks_dir, name))]
    if not missing:
        return []
    install = "uv run pre-commit install --hook-type pre-commit --hook-type pre-push"
    return [f"Git hooks not installed in this clone ({', '.join(missing)}): run `{install}` before committing."]


def board_lines(root: str) -> list[str]:
    """The in-progress task, the open counts and the age of the task board."""
    path = os.path.join(root, "docs", "TASK_BOARD.md")
    if not os.path.isfile(path):
        return []
    section, rows, last_entry = "", [], ""
    for line in read(path).splitlines():
        if line.startswith("## "):
            section = line
        elif section == "## Board":
            match = BOARD_ROW.match(line)
            if match:
                rows.append(match.groups())
        elif section == "## Changelog" and not last_entry:
            match = re.match(r"^- (\d{4}-\d{2}-\d{2})", line)
            if match:
                last_entry = match.group(1)
    if not rows:
        return ["docs/TASK_BOARD.md has no open rows."]
    lines = [f"In progress on the board: {task_id} ({priority}) {title}" for task_id, status, priority, title in rows if status == "in-progress"]
    counts = ", ".join(f"{sum(1 for row in rows if row[1] == status)} {status}" for status in ("todo", "blocked") if any(row[1] == status for row in rows))
    lines.append(f"Open on the board: {counts}." if counts else "Nothing else open on the board.")
    if last_entry:
        lines.append(f"The board changelog was last updated on {last_entry}.")
    return lines


def feedback_lines(root: str) -> list[str]:
    """Entries of the feedback notebook that have not been triaged into the board yet."""
    path = os.path.join(root, "docs", "FEEDBACK.md")
    if not os.path.isfile(path):
        return []
    pending = []
    in_comment = False
    for line in read(path).splitlines():
        if in_comment or "<!--" in line:  # the template examples live in an HTML comment
            in_comment = "-->" not in line
        elif UNCHECKED.match(line):
            pending.append(line.strip())
    if not pending:
        return []
    first = UNCHECKED.sub("", pending[0]).strip()[:90]
    return [f"{count(len(pending), 'entry', 'entries')} in docs/FEEDBACK.md not triaged yet (first: {first})"]


def read(path: str) -> str:
    """Return the text of a UTF-8 file."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def digest(root: str) -> str:
    """Return the digest, or an empty string when nothing could be gathered."""
    lines: list[str] = []
    for section in (git_lines, hook_lines, board_lines, feedback_lines):
        try:
            lines.extend(section(root))
        except Exception:  # a digest must never break a session
            continue
    if not lines:
        return ""
    return "<repo-state>\n" + "\n".join(f"- {line}" for line in lines) + "\n</repo-state>"


def main() -> int:
    """Print the SessionStart context, or nothing; always exit 0."""
    try:
        text = digest(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())
        if text:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}))
    except Exception:  # fail-open
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
