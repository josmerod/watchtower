---
name: task-board
description: Iterate on the Watchtower task board — pick up the next task, do it, verify, and mark it done. Use whenever the user says "work on the board", "pick up the next task", "what's next", "iterate", "continue with tasks", "do a task", or wants to add/complete/reprioritize tasks on docs/TASK_BOARD.md. Trigger on "next task", "task board", "what should I work on", "add a task", "close T-NNN", "reprioritize".
---

# Task Board

`docs/TASK_BOARD.md` is the single source of truth for actionable work. This
skill drives one iteration of the loop: **read → pick → claim → do → verify →
close → commit**. It also covers adding new tasks and reprioritizing.

## The board file

- Path: `docs/TASK_BOARD.md` (always — never copy it elsewhere).
- Format: one markdown table under `## Board` with columns, in order:

  `| ID | Status | Priority | Title | Area | Notes |`

- **Status:** `todo` · `in-progress` · `blocked` · `done`.
- **Priority:** `P0` · `P1` · `P2` · `P3`.
- **Area:** `etl` · `dashboard` · `api` · `infra` · `quality` · `docs` · `sec`.
- **ID:** `T-NNN` (zero-padded, never reused). Next free ID = highest existing +1.
- Sort order: `in-progress` → `todo` (by priority asc, then oldest) → `blocked` →
  `done` (newest first).

## Iteration loop — "work on the next task"

Run these steps in order. Do not skip verification.

1. **Read** `docs/TASK_BOARD.md`. If a row is already `in-progress`, resume it
   (ask the user whether to continue or roll it back to `todo`) rather than
   starting something new — **one task in-progress at a time**.

2. **Pick** the next task: first `in-progress`; else the highest-priority `todo`
   (P0 beats P1…); on ties, the one with the lower ID (oldest). State which task
   you picked and why.

3. **Claim** it: set its Status to `in-progress` and re-sort the row to the top
   of the table. Commit is **not** required yet — keep working.

4. **Do** the work. Follow the relevant domain skill if one applies
   (`etl-pipeline`, `dashboard-tab`, `unraid-deploy`). Branch off `main` first if
   the change is non-trivial (per AGENTS.md).

5. **Verify before claiming done.** This is mandatory — see
   `superpowers:verification-before-completion`. Run the actual commands and cite
   the output. At minimum:
   - `uv run ruff check .` and `uv run ruff format --check .` → clean.
   - `uv run pytest -q` → green (or document exactly what failed and why it's
     pre-existing).
   - `uv run pre-commit run --all-files` → green (mypy is advisory; do not block
     on it, but report its count if relevant to the task).
   - Any task-specific check (e.g. a deploy health check for infra tasks).

6. **Close** it: set Status to `done`, move the row below all open tasks, and add
   a one-line result to `Notes` (what changed, the verifying command). Append a
   dated line to the `## Changelog` section.

7. **Commit** the code change **and** the board edit together (the board update
   and the work it records belong in one focused commit). Only commit when the
   user asks or when continuing an established commit-as-you-go workflow.

## Adding a task ("add a task")

1. Find the next free `T-NNN`.
2. Insert a row with Status `todo`, a sensible Priority (default `P2`), the right
   Area, a short Title, and enough Notes that the next reader can start.
3. Place it among the `todo` rows in priority/ID order.
4. Append a dated changelog line. No code change → commit the board alone.

## Closing/reprioritizing

- **Close (`close T-NNN`):** run the verify step above, then flip to `done` +
  re-sort + changelog. If verification fails, leave it `in-progress` or `blocked`
  and explain — never mark `done` on an unverified change.
- **Reprioritize:** change the Priority cell and re-sort; add a changelog line.
- **Block:** set Status `blocked`, put the blocker in Notes, move under `todo`.

## Editing rules

- Edit the table **in place** with the `Edit` tool — preserve column alignment
  (the table is pipe-delimited; keep the header separators intact).
- Never delete a `done` row — it's the history. Never reuse an ID.
- Keep `Notes` terse; link to a `docs/` design file or a commit for detail.

## Don't

- Don't mark a task `done` without running a verifying command and showing output.
- Don't have two rows `in-progress` at once.
- Don't move the board file or split it into per-task files.
- Don't commit secrets (the board is tracked — see AGENTS.md).
