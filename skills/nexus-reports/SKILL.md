---
name: nexus-reports
description: "Gantt Charts, Planners, and Reports — workspace + org level. Use when an OpenJarvis user wants to call Nexus reports (GET) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: reports
  source_file: backend/routes/routes_reports.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus reports

Gantt Charts, Planners, and Reports — workspace + org level

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `reports` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/gantt` |
| GET | `/orgs/{org_id}/gantt` |
| GET | `/workspaces/{workspace_id}/planner` |
| GET | `/orgs/{org_id}/planner` |
| GET | `/workspaces/{workspace_id}/reports/summary` |
| GET | `/orgs/{org_id}/reports/summary` |
| GET | `/workspaces/{workspace_id}/reports/velocity` |

## Install

```sh
jarvis skill install nexus:reports
```

Source of truth: `backend/routes/routes_reports.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
