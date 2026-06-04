---
name: nexus-deployments
description: "Autonomous Deployments — AI agent deployment management with triggers, runs, and governance. Use when an OpenJarvis user wants to call Nexus deployments (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: deployments
  source_file: backend/routes/routes_deployments.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus deployments

Autonomous Deployments — AI agent deployment management with triggers, runs, and governance.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `deployments` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/deployments` |
| POST | `/workspaces/{ws_id}/deployments` |
| GET | `/deployments/{dep_id}` |
| PUT | `/deployments/{dep_id}` |
| DELETE | `/deployments/{dep_id}` |
| POST | `/deployments/{dep_id}/activate` |
| POST | `/deployments/{dep_id}/pause` |
| POST | `/deployments/{dep_id}/trigger` |
| GET | `/deployments/{dep_id}/runs` |
| GET | `/deployment-runs/{run_id}` |
| GET | `/deployment-runs/{run_id}/actions` |
| POST | `/deployment-runs/{run_id}/approve` |
| POST | `/deployment-runs/{run_id}/reject` |
| POST | `/deployment-runs/{run_id}/cancel` |
| POST | `/webhooks/deployments/{webhook_token}` |
| POST | `/deployments/{dep_id}/webhooks` |
| GET | `/deployments/{dep_id}/webhooks` |
| DELETE | `/deployment-webhooks/{wh_id}` |
| POST | `/deployments/{dep_id}/schedules` |
| GET | `/deployments/{dep_id}/schedules` |
| DELETE | `/deployment-schedules/{sched_id}` |
| GET | `/deployment-templates` |
| POST | `/workspaces/{ws_id}/deployments/from-template` |
| GET | `/workspaces/{ws_id}/deployment-limits` |

## Install

```sh
jarvis skill install nexus:deployments
```

Source of truth: `backend/routes/routes_deployments.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
