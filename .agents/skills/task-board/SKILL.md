---
name: task-board
description: Keep the Watchtower task documents true — add tasks from a list, a notebook or an agent's findings, triage feedback, close rows with evidence, write the changelog, reprioritize, or pick up the next task and run one iteration of the loop. Use whenever the user says "work on the board", "pick up the next task", "what's next", "iterate", "continue with tasks", "do a task", "add a task", "close T-NNN", or wants to add, complete or reprioritize tasks on docs/TASK_BOARD.md. Trigger on "next task", "task board", "tablero", "backlog", "what should I work on", "add a task", "cierra T-NNN", "reprioritize", "triajea el feedback".
---

# Task Board

Four documents divide the work. This skill drives one iteration of the loop:
**read → pick → claim → do → verify → close → commit**. It also covers adding
tasks, triaging feedback, a wave of parallel agents and reprioritizing.

| Document | Role |
| :--- | :--- |
| `docs/TASK_BOARD.md` | Open work only: one `## Board` table plus a short `## Changelog`. The single source of truth for what is actionable. |
| `docs/TASK_BOARD_ARCHIVE.md` | What is finished: closed rows under `## Tareas cerradas`, plus the historical changelog. |
| `docs/ROADMAP.md` | The prioritized horizon: value delivered, gaps and opportunities, what was evaluated and rejected. It cites task IDs and points to the board for execution. |
| `docs/FEEDBACK.md` | The user's raw notes (`## Entradas`) and the agent's notes for the user to review. |

The board is written in **Spanish**, for the user. One rule above the rest: a
row closes on evidence — a command that ran, or a deploy that was checked —
never on intention.

## Check the shape before committing

```bash
python .agents/skills/task-board/scripts/board_check.py
```

It reports a row with the wrong number of cells (a `|` inside a cell that was
not written `\|`), a Status, Priority or Area outside the lists, a `done` row
left on the board, two rows `in-progress`, a board out of order, an ID on both
files, a changelog that is not newest first or that still holds an entry older
than two months — each with file and line — and prints the counts and the
next free ID. Exit 1 when something is wrong. Run it after every edit: the
SessionStart hook parses `## Board` rows and the first dated changelog line
with a regex, and one stray pipe breaks the digest of every session.

## The board file

- One markdown table under `## Board`, columns in order:

  `| ID | Status | Priority | Title | Area | Notes |`

- **Status:** `todo` · `in-progress` · `blocked` · `done`.
- **Priority:** `P0` (blocker / production down) · `P1` (high) · `P2`
  (medium) · `P3` (nice to have).
- **Area:** `etl` · `dashboard` · `api` · `infra` · `quality` · `docs` · `sec`.
- **Sort:** `in-progress` first, then `todo` (by priority, oldest first), then
  `blocked`. No `done` row stays here — closing moves it to the archive.
- **ID:** `T-NNN` (zero-padded, never reused). Next free ID = the highest ID in
  the board **and** the archive, +1 — the check prints it. Closed rows live
  in the archive, so the board alone undercounts:
  ```bash
  grep -ohE 'T-[0-9]{3,}' docs/TASK_BOARD.md docs/TASK_BOARD_ARCHIVE.md | sort -u -t- -k2,2n | tail -n 1
  ```
- **Notes** carry what the next session needs to start: the finding (with
  its date and how it was found), what to do, and — when a doubt changes what
  gets built — the question, with the row saying it waits on the user. An
  agent's finding starts with `Hallazgo del agente YYYY-MM-DD`; a proposal
  with `Propuesta del agente`.

### The changelog

`## Changelog` is newest first. One line per wave, a deploy or a triage,
directly under the heading:

```markdown
- 2026-11-27 — **Título corto de la oleada.** `main` `<commit>` desplegado a las HH:MM CET (PR #NN; ciclo HH:MM → HH:MM, `Successful: N \| Failed: M`). Cerradas con evidencia: **T-NNN**, **T-NNN**. Abiertas: **T-NNN** (P2, qué es). Board: N abiertas + T-038 bloqueada, ninguna en curso.
```

- Every task the line touches is named as `**T-NNN**`, with its commit.
- A `|` inside the line is written `\|`.
- Entries older than two months move **verbatim** to `## Changelog histórico`
  in the archive; the check reports the ones that stayed.
- A mistake in an earlier line is corrected by a new line ("Corrección: …"),
  never by rewriting it.

## Iteration loop — "work on the next task"

1. **Read** `docs/TASK_BOARD.md`. The SessionStart hook
   (`.zcode/hooks/session_context.py`, wired in `.zcode/config.json`) has
   already printed a digest — the `in-progress` row, the open counts, the
   last changelog date, the untriaged feedback — but it is a summary: read
   the board before editing. If a row is already `in-progress`, resume it
   rather than starting something new — **one task in-progress at a time**.
2. **Pick** the next task: first `in-progress`; else the highest-priority `todo`
   (P0 beats P1…); on ties, the one with the lower ID (oldest). State which
   task you picked and why.
3. **Claim** it: set its Status to `in-progress` and re-sort the row to the top
   of the table.
4. **Do** the work. Follow the relevant domain skill if one applies
   (`etl-pipeline`, `dashboard-tab`, `unraid-deploy`). Branch off `main`
   first (per AGENTS.md).
5. **Verify before claiming done.** Mandatory — see
   `superpowers:verification-before-completion`. Run the actual commands and
   cite the output:
   - `uv run ruff check .` and `uv run ruff format --check .` → clean.
   - `uv run pytest -q` → green (or document exactly what failed and why it's
     pre-existing).
   - `uv run pre-commit run --all-files` → green (mypy is advisory; report its
     count if relevant).
   - Any task-specific check — for anything deployed, the whole list in
     `unraid-deploy`.

   The **pre-push hook** runs the full pytest suite (`pytest-check` in
   `.pre-commit-config.yaml`, about 8 minutes) when the push touches code, so
   a red suite blocks every push. A fresh clone has no hooks — the digest
   warns; install both stages with
   `uv run pre-commit install --hook-type pre-commit --hook-type pre-push`.
6. **Close** it: see "Closing a row" below.
7. **Commit** the code change; commit and push only when the user asks or in an
   established commit-as-you-go workflow.

## Closing a row

1. Move the **whole row** to the top of `## Tareas cerradas` in
   `docs/TASK_BOARD_ARCHIVE.md`: Status `done`, and Notes prefixed with the
   evidence, the original text kept after it —
   `Done 2026-11-27. PR #43 (`main` `50e639f`, desplegado a las 20:35 CET): what changed (commits). In production: what was checked and how. | the original Notes …`
   A row closed without a deploy says so ("Verificado en local: …") and why
   that is enough.
2. Add the changelog line.
3. Run the check. The board keeps no `done` row.

Never rewrite an archived row afterwards. A correction goes into a new
changelog line, and the user gets it in `FEEDBACK.md` as a correction.

The one exception is a repair of the row's **shape** that changes no
content: an Area cell a row from before the column lacks, a value outside
its list (`security` → `sec`, `P4` → `P3`). Name it in the changelog line
of the wave that does it, so the repair is on record.

**Code first, board after.** A code change is merged and deployed through its
own PR; the rows are then closed in a docs PR, with the production evidence
in them. A docs-only push skips the test suite, but it still goes through a
PR — never a direct push to `main`.

## `docs/FEEDBACK.md`

- **The user's notes** are unchecked `- [ ]` lines under `## Entradas`; the
  hook counts them. Turn each into a board row with a new `T-NNN` — bug →
  `P1`/`P2`, idea → proposal, missing source → a research task that needs no
  key — then tick the line and append the outcome:
  ```markdown
  - [x] YYYY-MM-DD — <the note> → **T-NNN** (<one-line outcome>)
  ```
  Add to the list everything related that comes up while triaging: the user
  asked for too much rather than too little ("mejor que sobre a que falte").
- **The agent's notes for the user** are what they read after a session. A
  dated section goes right under `## Entradas`, newest first:
  ```markdown
  ## 2026-11-27 (noche) — Backups en producción, News y Games con datos de hoy

  > Notas del agente para tu revisión. Cada punto ya está triajeado (tarea en el board), por eso van marcados.

  - [x] **Desplegado dos veces, entre ciclos y con exit 0:** `main` `<commit>` a las HH:MM CET …
  - [x] **Lo que se usa ya en producción:** …
  - [x] **Pendiente de tu decisión, no bloquea:** **T-NNN** …
  ```
  Plain Spanish, no jargon the user did not use, one claim per bullet, each
  one checked before it is written: what was deployed and when, what they now
  see in the dashboard, what was found (with the task IDs), what waits on
  their decision (with the IDs, so they can answer by number), the suite
  result. A correction to an earlier note is a new bullet ("Corrección a la
  nota anterior: …"), never an edit of the old one.

## A doubt that changes what gets built

Write it into the row's Notes as the question and say that the row waits on
the user; do not decide it. Keep working on what does not depend on the
answer, and ask all the questions in one batch when that work is done —
grouped, a few at a time, the recommended option first.

## A wave of parallel agents

- **Disjoint file scopes.** The integrator keeps the shared files:
  `run_all_etl_orchestrator.py`, `src/services/data_loader.py`,
  `src/web/dashboard/app.py`, `Tests/unit/test_tab_render.py`,
  `src/watchers/data_freshness_watcher.py` and every document in `docs/`.
- **Only the integrator edits the task documents.** Agents report their
  findings; the integrator turns them into rows and closes them with evidence.
- **No `git stash`, `git restore`, `git checkout` or `git reset`** outside
  one's own files, and no commit while agents hold uncommitted tracked files.
- **Few agents at a time.** With ten running, this machine took 13–16 minutes
  to start a shell command (2026-11-27); five plus the integrator's own work
  held. Agents run only their own test files; the integrator runs the full
  suite once per branch. When the machine saturates, tell them to wrap up and
  report what is complete and what is partial, and resume the partial ones on
  a calm machine.
- **Order per branch:** review the diffs → wire what the agents reported →
  full suite → commits per task → push → PR → CI → merge → deploy between
  cycles → validate → close the rows in a docs PR.

## Adding, blocking, reprioritizing

- **Add**: next free `T-NNN` → a `todo` row (default `P2`, the right Area,
  Notes enough to start) among the `todo` rows in priority order, plus a
  changelog line.
- **Block**: Status `blocked`, the blocker in Notes, below the `todo` rows.
- **Reprioritize**: change the Priority cell and re-sort; add a changelog line.
- **Close before verification passes**: leave it `in-progress` or `blocked`
  and explain — never mark `done` on an unverified change.

## Editing rules

- Edit the tables **in place** with the `Edit` tool`; keep the pipe alignment
  and the header separators intact. A long wave is easier as a script: one
  row per ID, the checks of `board_check.py`, then a diff that shows only the
  intended lines.
- Never delete or rewrite an archived row. Never reuse an ID.
- Keep `Notes` terse; long design goes in a `docs/` file or a commit.
- These files are tracked in a public repository: no address, hostname or
  credential (write `<host>`).

## Don't

- Don't mark a task `done` without running a verifying command and showing
  its output — and, for anything deployed, without the production evidence.
- Don't have two rows `in-progress` at once.
- Don't leave a `done` row on the board or add one at the bottom of the archive.
- Don't move the board file or split it into per-task files.
