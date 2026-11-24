# Watchtower — Documentation Index

Documentation for the Watchtower data intelligence platform (ETL → Watchers → Dashboard).
Python 3.10+ with UV. Data persists as timestamped JSON under `data/` (gitignored).

## Start here

| Doc | What it covers |
| :-- | :-- |
| [Quickstart](QUICKSTART.md) | Install and run in 10 minutes |
| [FAQ](FAQ.md) | Frequently asked questions |
| [Contributing](CONTRIBUTING.md) | How to contribute |
| [architecture.md](architecture.md) | System architecture (3 layers) |
| [CODEBASE_SUMMARY.md](../CODEBASE_SUMMARY.md) | What the platform is made of: layers, entry points, deployment |
| [PRD.md](PRD.md) | Product requirements |
| [ROADMAP.md](ROADMAP.md) | **Horizonte priorizado**: valor entregado, gaps, backlog y anti-backlog |
| [TASK_BOARD.md](TASK_BOARD.md) | **Single source of truth for actionable work** (solo tareas abiertas) |
| [TASK_BOARD_ARCHIVE.md](TASK_BOARD_ARCHIVE.md) | Tareas cerradas + changelog histórico (compactación del board) |
| [FEEDBACK.md](FEEDBACK.md) | Cajón de sastre del usuario — se triajea a tareas cada sesión |

## Technical guides (`docs/technical/`)

| Guide | What it covers |
| :-- | :-- |
| [Architecture Overview](technical/ARCHITECTURE_OVERVIEW.md) | System design and patterns |
| [ETL Development](technical/ETL_DEVELOPMENT_GUIDE.md) | Creating ETL pipelines |
| [Watchers](technical/WATCHERS_GUIDE.md) | Building watchers |
| [Dashboard Development](technical/DASHBOARD_DEVELOPMENT_GUIDE.md) | Building dashboard tabs |
| [Configuration](technical/CONFIGURATION_GUIDE.md) | Settings and env vars |
| [Deployment](technical/DEPLOYMENT_GUIDE.md) | Deploying (Unraid) |
| [Advanced Deployment](technical/ADVANCED_DEPLOYMENT_GUIDE.md) | Advanced deploy topics |

## Pattern references

| Doc | Pattern |
| :-- | :-- |
| [Repository Pattern](REPOSITORY_PATTERN.md) | Data repositories |
| [Data Models](data-models-main.md) | Pydantic model reference |

## Source research

| Doc | Topic |
| :-- | :-- |
| [potentialsources/](potentialsources/) | Cataloged candidate data sources |
| [future/](future/) | Future ideas and brainstorms |

## Root-level docs

| Doc | What it covers |
| :-- | :-- |
| [README](../README.md) | Project overview and install |
| [AGENTS.md](../AGENTS.md) | AI-agent workspace instructions |
| [CODEBASE_SUMMARY](../CODEBASE_SUMMARY.md) | Map of the codebase as it is today |
| [API_DOCS](../API_DOCS.md) | REST API reference |

## Archive

Historical material lives in [archive/](archive/) — phase reports, refactoring
guides, BMM/epic planning docs, validation reports, and superseded design
documents. Kept for reference; not maintained. Files moved there carry an
"Archived" note on their first line.
