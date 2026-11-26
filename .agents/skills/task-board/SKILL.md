---
name: task-board
description: Iterate on the Watchtower task board — pick up the next task, do it, verify, and mark it done. Use whenever the user says "work on the board", "pick up the next task", "what's next", "iterate", "continue with tasks", "do a task", or wants to add/complete/reprioritize tasks on docs/TASK_BOARD.md. Trigger on "next task", "task board", "what should I work on", "add a task", "close T-NNN", "reprioritize".
---

# Task Board

Four documents divide the work. This skill drives one iteration of the loop:
**read → pick → claim → do → verify → close → commit**. It also covers adding
tasks, triaging feedback and reprioritizing.

| Document | Role |
| :--- | :--- |
| `docs/TASK_BOARD.md` | Open work only: one `## Board` table plus a short `## Changelog`. The single source of truth for what is actionable. |
| `docs/TASK_BOARD_ARCHIVE.md` | What is finished: closed rows under `## Tareas cerradas`, plus the historical changelog. |
| `docs/ROADMAP.md` | The prioritized horizon: value delivered, gaps and opportunities, what was evaluated and rejected. It cites task IDs and points to the board for execution. |
| `docs/FEEDBACK.md` | The user's raw notes (`## Entradas`) and what triaging turned them into (`## Triajeado (archivo histórico)`). |

## The board file

- One markdown table under `## Board`, columns in order:

  `| ID | Status | Priority | Title | Area | Notes |`

- **Status:** `todo` · `in-progress` · `blocked` · `done`.
- **Priority:** `P0` · `P1` · `P2` · `P3`.
- **Area:** `etl` · `dashboard` · `api` · `infra` · `quality` · `docs` · `sec`.
- **Sort:** `in-progress` first, then `todo` (by priority, oldest first), then
  `blocked`. No `done` row stays here — closing moves it to the archive.
- **ID:** `T-NNN` (zero-padded, never reused). Next free ID = the highest ID in
  the board **and** the archive, +1. Closed rows live in the archive, so the
  board alone undercounts:
  ```bash
  grep -ohE 'T-[0-9]{3,}' docs/TASK_BOARD.md docs/TASK_BOARD_ARCHIVE.md | sort -u -t- -k2,2n | tail -n 1
  ```
- **`## Changelog`** is newest first: a new line goes directly under the
  heading, as `- YYYY-MM-DD — **T-NNN …**`.
- Keep the row shape exact: the SessionStart hook parses `## Board` rows and
  the first dated changelog line with a regex.

## Iteration loop — "work on the next task"

Run these steps in order. Do not skip verification.

1. **Read** `docs/TASK_BOARD.md`. The SessionStart hook
   (`.zcode/hooks/session_context.py`, wired in `.zcode/config.json`) has
   already printed a digest — the `in-progress` row, the open `todo`/`blocked`
   counts, the last changelog date, the untriaged `FEEDBACK.md` entries — but
   it is a summary: read the board before editing. If a row is already
   `in-progress`, resume it (ask whether to continue or roll it back to
   `todo`) rather than starting something new — **one task in-progress at a
   time**.

2. **Pick** the next task: first `in-progress`; else the highest-priority `todo`
   (P0 beats P1…); on ties, the one with the lower ID (oldest). State which task
   you picked and why.

3. **Claim** it: set its Status to `in-progress` and re-sort the row to the top
   of the table. Commit is **not** required yet — keep working.

4. **Do** the work. Follow the relevant domain skill if one applies
   (`etl-pipeline`, `dashboard-tab`, `unraid-deploy`). Branch off `main` first if
   the change is non-trivial (per AGENTS.md).

5. **Verify before claiming done.** Mandatory — see
   `superpowers:verification-before-completion`. Run the actual commands and
   cite the output:
   - `uv run ruff check .` and `uv run ruff format --check .` → clean.
   - `uv run pytest -q` → green (or document exactly what failed and why it's
     pre-existing).
   - `uv run pre-commit run --all-files` → green (mypy is advisory; report its
     count if relevant).
   - Any task-specific check (e.g. a deploy health check for infra tasks).

   The **pre-push hook** runs the full pytest suite (`pytest-check` in
   `.pre-commit-config.yaml`), so a red suite blocks every push. A fresh clone
   has no hooks — the digest warns; install both stages with
   `uv run pre-commit install --hook-type pre-commit --hook-type pre-push`.

6. **Close** it: set Status to `done`, add a one-line result to `Notes` (what
   changed, the verifying command), move the **whole row** to the top of
   `## Tareas cerradas` in `docs/TASK_BOARD_ARCHIVE.md`, and add the changelog
   line. The board keeps no `done` row.

7. **Commit** the code change **and** the board edit together (the work and the
   row that records it belong in one focused commit). Only commit when the user
   asks or in an established commit-as-you-go workflow.

## Triaging `docs/FEEDBACK.md`

Each unchecked `- [ ]` line under `## Entradas` is a note not triaged yet (the
SessionStart hook counts them). Turn it into a board row with a new `T-NNN` —
bug → `P1`/`P2` task, idea → proposal, missing source → research task — then
record it: tick the line, move it under `## Triajeado (archivo histórico)` and
append the outcome.

```markdown
- [x] YYYY-MM-DD — <the note> → **T-NNN** (<one-line outcome>)
```

## Adding, blocking, reprioritizing

- **Add**: next free `T-NNN` (command above) → a `todo` row (default `P2`, the
  right Area, Notes enough to start) among the `todo` rows in priority order,
  plus a changelog line.
- **Block**: Status `blocked`, the blocker in Notes, below the `todo` rows.
- **Reprioritize**: change the Priority cell and re-sort; add a changelog line.
- **Close before verification passes**: leave it `in-progress` or `blocked`
  and explain — never mark `done` on an unverified change.

## Editing rules

- Edit the table **in place** with the `Edit` tool; keep the pipe alignment and
  the header separators intact.
- Never delete or rewrite an archived row. Never reuse an ID.
- Keep `Notes` terse; long design goes in a `docs/` file or a commit.

## Don't

- Don't mark a task `done` without running a verifying command and showing output.
- Don't have two rows `in-progress` at once.
- Don't leave a `done` row on the board or add one at the bottom of the archive.
- Don't move the board file or split it into per-task files.
- Don't commit secrets or private addresses (these documents are tracked — see
  AGENTS.md).
