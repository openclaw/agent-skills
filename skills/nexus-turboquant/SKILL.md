---
name: nexus-turboquant
description: "NAVC (Nexus Adaptive Vector Compression) API Routes — Profiles, Runs, Promotions. Use when an OpenJarvis user wants to call Nexus turboquant (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: turboquant
  source_file: backend/routes/routes_turboquant.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus turboquant

NAVC (Nexus Adaptive Vector Compression) API Routes — Profiles, Runs, Promotions.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `turboquant` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/turboquant/profiles` |
| GET | `/workspaces/{ws_id}/turboquant/profiles` |
| GET | `/workspaces/{ws_id}/turboquant/profiles/{profile_id}` |
| PUT | `/workspaces/{ws_id}/turboquant/profiles/{profile_id}` |
| DELETE | `/workspaces/{ws_id}/turboquant/profiles/{profile_id}` |
| POST | `/workspaces/{ws_id}/turboquant/runs` |
| GET | `/workspaces/{ws_id}/turboquant/runs` |
| GET | `/workspaces/{ws_id}/turboquant/runs/{run_id}` |
| POST | `/workspaces/{ws_id}/turboquant/runs/{run_id}/cancel` |
| POST | `/workspaces/{ws_id}/turboquant/datasets` |
| GET | `/workspaces/{ws_id}/turboquant/datasets` |
| DELETE | `/workspaces/{ws_id}/turboquant/datasets/{dataset_id}` |
| GET | `/workspaces/{ws_id}/turboquant/kv-models` |
| POST | `/workspaces/{ws_id}/turboquant/promotions` |
| GET | `/workspaces/{ws_id}/turboquant/promotions` |
| POST | `/workspaces/{ws_id}/turboquant/promotions/{promo_id}/rollback` |
| GET | `/workspaces/{ws_id}/turboquant/compare` |
| POST | `/workspaces/{ws_id}/turboquant/bind` |
| GET | `/workspaces/{ws_id}/turboquant/binding` |
| DELETE | `/workspaces/{ws_id}/turboquant/binding` |

## Install

```sh
jarvis skill install nexus:turboquant
```

Source of truth: `backend/routes/routes_turboquant.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
