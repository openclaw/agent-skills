---
name: nexus-task-checkpoints
description: "Task Checkpoints — replay parity for long-running AI tasks. Use when an OpenJarvis user wants to call Nexus task.checkpoints (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: task.checkpoints
  source_file: backend/routes/routes_task_checkpoints.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus task.checkpoints

Task Checkpoints — replay parity for long-running AI tasks.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `task.checkpoints` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/runs/{run_id}/checkpoints` |
| GET | `/workspaces/{workspace_id}/runs/{run_id}/checkpoints` |
| GET | `/workspaces/{workspace_id}/runs/{run_id}/checkpoints/{checkpoint_id}` |
| POST | `/workspaces/{workspace_id}/runs/{run_id}/checkpoints/{checkpoint_id}/restore` |
| DELETE | `/workspaces/{workspace_id}/runs/{run_id}/checkpoints/{checkpoint_id}` |

## Install

```sh
jarvis skill install nexus:task-checkpoints
```

Source of truth: `backend/routes/routes_task_checkpoints.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
