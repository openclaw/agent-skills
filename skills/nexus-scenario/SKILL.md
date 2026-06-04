---
name: nexus-scenario
description: "Scenario Engine Routes — REST API for multi-agent simulation. Use when an OpenJarvis user wants to call Nexus scenario (DELETE, GET, PATCH, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: scenario
  source_file: backend/routes/routes_scenario.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus scenario

Scenario Engine Routes — REST API for multi-agent simulation.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `scenario` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/scenario/projects` |
| GET | `/workspaces/{ws_id}/scenario/projects` |
| GET | `/workspaces/{ws_id}/scenario/projects/{pid}` |
| PATCH | `/workspaces/{ws_id}/scenario/projects/{pid}` |
| DELETE | `/workspaces/{ws_id}/scenario/projects/{pid}` |
| POST | `/workspaces/{ws_id}/scenario/projects/{pid}/analyze` |
| GET | `/workspaces/{ws_id}/scenario/projects/{pid}/graph` |
| PATCH | `/workspaces/{ws_id}/scenario/projects/{pid}/entities/{eid}` |
| DELETE | `/workspaces/{ws_id}/scenario/projects/{pid}/entities/{eid}` |
| POST | `/workspaces/{ws_id}/scenario/projects/{pid}/personas` |
| GET | `/workspaces/{ws_id}/scenario/projects/{pid}/agents` |
| PATCH | `/workspaces/{ws_id}/scenario/projects/{pid}/agents/{aid}` |
| POST | `/workspaces/{ws_id}/scenario/projects/{pid}/run` |
| POST | `/workspaces/{ws_id}/scenario/projects/{pid}/pause` |
| POST | `/workspaces/{ws_id}/scenario/projects/{pid}/resume` |
| POST | `/workspaces/{ws_id}/scenario/projects/{pid}/inject` |
| GET | `/workspaces/{ws_id}/scenario/projects/{pid}/rounds` |
| GET | `/workspaces/{ws_id}/scenario/projects/{pid}/rounds/{round_number}/actions` |
| GET | `/workspaces/{ws_id}/scenario/projects/{pid}/stream` |
| POST | `/workspaces/{ws_id}/scenario/projects/{pid}/report` |
| GET | `/workspaces/{ws_id}/scenario/projects/{pid}/reports` |
| POST | `/workspaces/{ws_id}/scenario/projects/{pid}/interview/{aid}` |

## Install

```sh
jarvis skill install nexus:scenario
```

Source of truth: `backend/routes/routes_scenario.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
