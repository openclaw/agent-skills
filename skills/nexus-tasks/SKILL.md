---
name: nexus-tasks
description: "Task management routes — uses JSONB adapter for backward compatibility. Use when an OpenJarvis user wants to call Nexus tasks (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: tasks
  source_file: backend/routes/routes_tasks.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus tasks

Task management routes — uses JSONB adapter for backward compatibility.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `tasks` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/tasks` |
| GET | `/workspaces/{workspace_id}/all-tasks` |
| POST | `/workspaces/{workspace_id}/tasks` |
| POST | `/tasks/{task_id}/prompt-agent` |
| PUT | `/tasks/{task_id}` |
| DELETE | `/tasks/{task_id}` |
| GET | `/workspaces/{workspace_id}/reports` |

## Install

```sh
jarvis skill install nexus:tasks
```

Source of truth: `backend/routes/routes_tasks.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
