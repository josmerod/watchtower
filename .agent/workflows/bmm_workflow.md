---
description: How to use the BMAD Method (BMM) workflow in Watchtower
---

# BMAD Method (BMM) Workflow

This workflow outlines how to develop features using the BMAD methodology in the Watchtower project.

## Prerequisites

- Ensure you have `uv` installed.
- Ensure you are in the project root.

## 1. Activate Agent Persona

Before starting work, activate the appropriate agent persona.

- **Developer**: `/bmm_activate_dev`
  - Use for implementing stories, writing code, fixing bugs.
- **Product Manager**: `/bmm_activate_pm`
  - Use for planning features, writing PRDs.

## 2. Select a Story

1.  Check `docs/epics.md` or `task.md` to identify the next story to implement.
2.  Read the story details, including Acceptance Criteria and Technical Notes.

## 3. Develop Story (`/bmm_develop_story`)

1.  **Plan**: Create an `implementation_plan.md` detailing the changes.
    - Identify new files to create (ETLs, Models, Dashboard Components).
    - Identify existing files to modify.
    - Define the verification plan (tests, manual checks).
2.  **Review**: Request user review of the plan using `notify_user`.
3.  **Implement**: Execute the plan.
    - Create Pydantic models in `src/models/`.
    - Create ETL classes in `src/etl/`.
    - Create Dashboard components in `src/web/dashboard/components/`.
    - Update `src/config/settings.py` if needed.
4.  **Verify**: Run tests and verify the implementation.
    - Run `uv run pytest`.
    - Run the dashboard: `uv run python run_watchtower_dashboard.py`.
5.  **Document**: Update `walkthrough.md` with results.

## 4. Status Check (`/bmm_status`)

- Check the status of workflows and tasks.

## Key Locations

- **Epics/Stories**: `docs/epics.md`
- **Readiness Reports**: `docs/*readiness-report.md`
- **Source Code**: `src/`
- **Tests**: `Tests/`
- **Data**: `data/`

## Common Commands

- Run Dashboard: `uv run python run_watchtower_dashboard.py`
- Run Tests: `uv run pytest`
- Run ETLs: `./run_all_etl.bat` (Windows) or `./run_all_etl.sh` (Linux/Mac)
