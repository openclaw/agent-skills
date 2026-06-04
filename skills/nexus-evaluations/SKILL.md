---
name: nexus-evaluations
description: "AI Evaluation & Testing Framework — Golden dataset management and multi-agent eval runs. Use when an OpenJarvis user wants to call Nexus evaluations (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: evaluations
  source_file: backend/routes/routes_evaluations.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus evaluations

AI Evaluation & Testing Framework — Golden dataset management and multi-agent eval runs.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `evaluations` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/eval/datasets` |
| POST | `/workspaces/{ws_id}/eval/datasets` |
| PUT | `/workspaces/{ws_id}/eval/datasets/{ds_id}` |
| DELETE | `/workspaces/{ws_id}/eval/datasets/{ds_id}` |
| POST | `/workspaces/{ws_id}/eval/datasets/{ds_id}/items` |
| POST | `/workspaces/{ws_id}/eval/runs` |
| GET | `/workspaces/{ws_id}/eval/runs` |
| GET | `/workspaces/{ws_id}/eval/runs/{run_id}` |
| GET | `/workspaces/{ws_id}/eval/runs/{run_id}/compare` |

## Install

```sh
jarvis skill install nexus:evaluations
```

Source of truth: `backend/routes/routes_evaluations.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
