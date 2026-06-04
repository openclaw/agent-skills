---
name: nexus-operator
description: "Nexus Operator Routes — Session management, execution, templates, analytics. Use when an OpenJarvis user wants to call Nexus operator (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: operator
  source_file: backend/routes/routes_operator.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus operator

Nexus Operator Routes — Session management, execution, templates, analytics.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `operator` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/operator/sessions` |
| GET | `/workspaces/{ws_id}/operator/sessions` |
| GET | `/operator/sessions/{session_id}` |
| POST | `/operator/sessions/{session_id}/approve-plan` |
| POST | `/operator/sessions/{session_id}/cancel` |
| POST | `/operator/sessions/{session_id}/pause` |
| POST | `/operator/sessions/{session_id}/resume` |
| GET | `/operator/sessions/{session_id}/tasks` |
| GET | `/operator/sessions/{session_id}/tasks/{task_id}` |
| GET | `/operator/sessions/{session_id}/observations` |
| POST | `/operator/sessions/{session_id}/inject` |
| POST | `/workspaces/{ws_id}/operator/quick` |
| GET | `/operator/sessions/{session_id}/screenshots` |
| GET | `/operator/sessions/{session_id}/live` |
| GET | `/workspaces/{ws_id}/operator/templates` |
| GET | `/workspaces/{ws_id}/operator/analytics` |

## Install

```sh
jarvis skill install nexus:operator
```

Source of truth: `backend/routes/routes_operator.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
