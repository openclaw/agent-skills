---
name: nexus-orch-schedules
description: "Batch Orchestration Scheduling — Schedule orchestrations to run on cron intervals. Use when an OpenJarvis user wants to call Nexus orch.schedules (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: orch.schedules
  source_file: backend/routes/routes_orch_schedules.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus orch.schedules

Batch Orchestration Scheduling — Schedule orchestrations to run on cron intervals.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `orch.schedules` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/orchestration-schedules` |
| GET | `/workspaces/{ws_id}/orchestration-schedules` |
| PUT | `/workspaces/{ws_id}/orchestration-schedules/{sched_id}` |
| DELETE | `/workspaces/{ws_id}/orchestration-schedules/{sched_id}` |

## Install

```sh
jarvis skill install nexus:orch-schedules
```

Source of truth: `backend/routes/routes_orch_schedules.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
