---
name: nexus-task-sessions
description: "Task Sessions - Independent AI task sessions with their own logs. Use when an OpenJarvis user wants to call Nexus task.sessions (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: task.sessions
  source_file: backend/routes/routes_task_sessions.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus task.sessions

Task Sessions - Independent AI task sessions with their own logs

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `task.sessions` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/task-sessions` |
| POST | `/workspaces/{workspace_id}/task-sessions` |
| GET | `/task-sessions/{session_id}` |
| GET | `/task-sessions/{session_id}/messages` |
| POST | `/task-sessions/{session_id}/messages` |
| POST | `/task-sessions/{session_id}/run` |
| PUT | `/task-sessions/{session_id}/status` |
| DELETE | `/task-sessions/{session_id}` |
| GET | `/workspaces/{workspace_id}/task-queue` |
| PUT | `/task-sessions/{session_id}/schedule` |
| PUT | `/task-sessions/{session_id}/complete` |

## Install

```sh
jarvis skill install nexus:task-sessions
```

Source of truth: `backend/routes/routes_task_sessions.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
