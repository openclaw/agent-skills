---
name: nexus-cost-dashboard
description: "Cost Dashboard — Read-only aggregation routes for the workspace cost UI. Use when an OpenJarvis user wants to call Nexus cost.dashboard (GET) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: cost.dashboard
  source_file: backend/routes/routes_cost_dashboard.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus cost.dashboard

Cost Dashboard — Read-only aggregation routes for the workspace cost UI.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `cost.dashboard` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/cost/summary` |
| GET | `/workspaces/{ws_id}/cost/timeseries` |
| GET | `/workspaces/{ws_id}/cost/recent-calls` |
| GET | `/workspaces/{ws_id}/cost/export` |

## Install

```sh
jarvis skill install nexus:cost-dashboard
```

Source of truth: `backend/routes/routes_cost_dashboard.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
