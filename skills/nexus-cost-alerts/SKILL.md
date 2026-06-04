---
name: nexus-cost-alerts
description: "Nexus cost.alerts API surface. Use when an OpenJarvis user wants to call Nexus cost.alerts (GET, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: cost.alerts
  source_file: backend/routes/routes_cost_alerts.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus cost.alerts

Nexus user-callable surface exposing the `cost.alerts` API.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `cost.alerts` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/cost-alerts` |
| PUT | `/workspaces/{ws_id}/cost-alerts/acknowledge` |
| PUT | `/workspaces/{ws_id}/budget/thresholds` |

## Install

```sh
jarvis skill install nexus:cost-alerts
```

Source of truth: `backend/routes/routes_cost_alerts.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
