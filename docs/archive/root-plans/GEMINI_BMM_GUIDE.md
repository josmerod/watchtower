# Gemini BMM Guide

This guide explains how to use the **BMad Method (BMM)** within the Gemini environment. We have adapted the core BMM agents and workflows into Gemini-compatible **Slash Commands**.

## 🚀 Quick Start

### 1. Activate an Agent
Before running any workflows, you must adopt an agent persona.

- **Developer**: `/bmm_activate_dev`
  - *Use when:* Implementing stories, writing code, fixing bugs.
- **Product Manager**: `/bmm_activate_pm` (Coming Soon)
  - *Use when:* Planning features, writing PRDs.

### 2. Run a Workflow
Once an agent is active, use the corresponding slash commands to execute workflows.

#### Developer Workflows
- **Develop Story**: `/bmm_develop_story`
  - *Description:* The core development loop. Reads the active story and implements it.
  - *Prerequisite:* You must have a story selected or be ready to select one.

#### Planning Workflows
- **Create PRD**: `/bmm_create_prd`
  - *Description:* interactive workflow to create a Product Requirements Document.
- **Workflow Status**: `/bmm_status`
  - *Description:* Checks the current status of the project workflows.

## 📂 Workflow Mapping

| BMM Command | Gemini Command | Description |
|-------------|----------------|-------------|
| `*develop-story` | `/bmm_develop_story` | Execute Dev Story workflow |
| `*create-prd` | `/bmm_create_prd` | Create a PRD |
| `*workflow-status` | `/bmm_status` | Check status |
| `*workflow-init` | `/bmm_init` | Initialize project (Coming Soon) |

## ⚠️ Important Notes

- **Context is Key**: Gemini relies on the context provided by these workflows. When you run a command like `/bmm_activate_dev`, it loads the specific instructions for that agent.
- **Strict Adherence**: These workflows are designed to follow the BMM protocols strictly. Please follow the instructions provided by the agent.
- **File Paths**: The workflows automatically handle path resolution for the `watchtower` project.

## 🛠 Troubleshooting

If a workflow fails or gets stuck:
1.  **Check your active agent**: Did you run `/bmm_activate_...`?
2.  **Check `task.md`**: Ensure your current task is clear.
3.  **Manual Override**: You can always manually read the BMM files in `.bmad/bmm/` if needed.
