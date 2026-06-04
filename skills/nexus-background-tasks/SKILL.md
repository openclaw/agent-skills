---
name: nexus-background-tasks
description: "Background tasks REST routes — unified task registry. Use when an OpenJarvis user wants to call Nexus background.tasks (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: background.tasks
  source_file: backend/routes/routes_background_tasks.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus background.tasks

Background tasks REST routes — unified task registry.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `background.tasks` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/me/tasks` |
| POST | `/me/tasks/{task_id}/cancel` |
| GET | `/workspaces/{workspace_id}/tasks` |

## Install

```sh
jarvis skill install nexus:background-tasks
```

Source of truth: `backend/routes/routes_background_tasks.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
