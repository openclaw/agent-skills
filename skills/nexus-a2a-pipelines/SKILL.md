---
name: nexus-a2a-pipelines
description: "A2A Pipeline Routes — CRUD, triggering, run management, templates, analytics. Use when an OpenJarvis user wants to call Nexus a2a.pipelines (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: a2a.pipelines
  source_file: backend/routes/routes_a2a_pipelines.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus a2a.pipelines

A2A Pipeline Routes — CRUD, triggering, run management, templates, analytics.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `a2a.pipelines` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/a2a/pipelines` |
| GET | `/workspaces/{ws_id}/a2a/pipelines` |
| GET | `/a2a/pipelines/{pipeline_id}` |
| PUT | `/a2a/pipelines/{pipeline_id}` |
| DELETE | `/a2a/pipelines/{pipeline_id}` |
| POST | `/a2a/pipelines/{pipeline_id}/activate` |
| POST | `/a2a/pipelines/{pipeline_id}/pause` |
| POST | `/a2a/pipelines/{pipeline_id}/trigger` |
| GET | `/a2a/pipelines/{pipeline_id}/runs` |
| GET | `/a2a/runs/{run_id}` |
| GET | `/a2a/runs/{run_id}/steps` |
| POST | `/a2a/runs/{run_id}/cancel` |
| POST | `/a2a/runs/{run_id}/resume` |
| GET | `/workspaces/{ws_id}/a2a/templates` |
| GET | `/workspaces/{ws_id}/a2a/analytics` |

## Install

```sh
jarvis skill install nexus:a2a-pipelines
```

Source of truth: `backend/routes/routes_a2a_pipelines.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
