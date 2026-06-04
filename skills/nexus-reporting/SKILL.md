---
name: nexus-reporting
description: "Enterprise Reporting Engine — Event ingestion, analytics aggregation, and reporting. Use when an OpenJarvis user wants to call Nexus reporting (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: reporting
  source_file: backend/routes/routes_reporting.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus reporting

Enterprise Reporting Engine — Event ingestion, analytics aggregation, and reporting.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `reporting` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/reports/platform/health` |
| GET | `/reports/platform/business` |
| GET | `/reports/org/{org_id}/usage` |
| GET | `/reports/org/{org_id}/users` |
| GET | `/reports/me/usage` |
| GET | `/reports/export` |
| GET | `/reports/alerts` |
| POST | `/reports/alerts/{alert_id}/resolve` |
| PUT | `/reports/org/{org_id}/budget` |
| GET | `/reports/org/{org_id}/budget` |
| POST | `/reports/schedules` |
| GET | `/reports/schedules` |
| DELETE | `/reports/schedules/{schedule_id}` |
| POST | `/reports/webhooks` |
| GET | `/reports/webhooks` |
| DELETE | `/reports/webhooks/{webhook_id}` |
| POST | `/reports/query` |
| PUT | `/reports/org/{org_id}/cost-tags` |
| GET | `/reports/org/{org_id}/cost-tags` |

## Install

```sh
jarvis skill install nexus:reporting
```

Source of truth: `backend/routes/routes_reporting.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
