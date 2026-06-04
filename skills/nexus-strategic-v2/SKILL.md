---
name: nexus-strategic-v2
description: "Strategic Features v2 — Usage billing, scheduled jobs, audit export, tenant API,. Use when an OpenJarvis user wants to call Nexus strategic.v2 (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: strategic.v2
  source_file: backend/routes/routes_strategic_v2.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus strategic.v2

Strategic Features v2 — Usage billing, scheduled jobs, audit export, tenant API,

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `strategic.v2` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/billing/usage/{workspace_id}` |
| GET | `/billing/usage/invoice/{workspace_id}` |
| POST | `/workspaces/{ws_id}/scheduled-jobs` |
| GET | `/workspaces/{ws_id}/scheduled-jobs` |
| PUT | `/scheduled-jobs/{job_id}` |
| DELETE | `/scheduled-jobs/{job_id}` |
| POST | `/scheduled-jobs/{job_id}/run-now` |
| GET | `/admin/audit-export` |
| GET | `/admin/compliance-report` |
| POST | `/developer/api-keys` |
| GET | `/developer/api-keys` |
| DELETE | `/developer/api-keys/{key_id}` |
| GET | `/developer/docs` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/learning` |
| GET | `/workspaces/{ws_id}/activity-feed` |
| GET | `/orgs/{org_id}/branding` |
| PUT | `/orgs/{org_id}/branding` |
| POST | `/marketplace/agents/{agent_id}/publish` |
| GET | `/marketplace/strategic-agents` |
| POST | `/marketplace/agents/{listing_id}/install` |

## Install

```sh
jarvis skill install nexus:strategic-v2
```

Source of truth: `backend/routes/routes_strategic_v2.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
