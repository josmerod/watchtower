---
description: Execute the BMM Develop Story Workflow
---

1.  **Prerequisites**:
    - Ensure you have activated the Dev agent (`/bmm_activate_dev`). If not, do so now (internally adopt the persona).
    - Read `/Users/jmejiasr/watchtower/.bmad/core/tasks/workflow.xml` to understand the execution engine rules.

2.  **Load Workflow**:
    - Read `/Users/jmejiasr/watchtower/.bmad/bmm/workflows/4-implementation/dev-story/workflow.yaml`.

3.  **Execute Workflow**:
    - Follow the steps in `workflow.yaml` EXACTLY as described in `workflow.xml`.
    - **Step 1**: Load Configuration.
    - **Step 2**: Process Instructions.
        - If the workflow asks to read a file, read it.
        - If the workflow asks for user input, ask the user.
        - If the workflow has a `template-output`, generate it and ask for review.

4.  **Completion**:
    - Once the workflow is done, report completion to the user.
