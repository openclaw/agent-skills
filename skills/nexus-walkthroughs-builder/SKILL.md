---
name: nexus-walkthroughs-builder
description: "Nexus walkthroughs.builder API surface. Use when an OpenJarvis user wants to call Nexus walkthroughs.builder (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: walkthroughs.builder
  source_file: backend/routes/routes_walkthroughs_builder.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus walkthroughs.builder

Nexus user-callable surface exposing the `walkthroughs.builder` API.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `walkthroughs.builder` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/walkthroughs/config` |
| POST | `/walkthroughs` |
| GET | `/walkthroughs` |
| GET | `/walkthroughs/{wt_id}` |
| PUT | `/walkthroughs/{wt_id}` |
| DELETE | `/walkthroughs/{wt_id}` |
| POST | `/walkthroughs/{wt_id}/steps` |
| PUT | `/walkthroughs/{wt_id}/steps/{step_id}` |
| DELETE | `/walkthroughs/{wt_id}/steps/{step_id}` |
| PUT | `/walkthroughs/{wt_id}/steps/reorder` |
| POST | `/walkthroughs/{wt_id}/publish` |
| POST | `/walkthroughs/{wt_id}/archive` |
| GET | `/walkthroughs/{wt_id}/versions` |
| POST | `/walkthroughs/{wt_id}/rollback/{version}` |
| GET | `/sdk/walkthroughs/active` |
| POST | `/sdk/events` |
| POST | `/sdk/progress` |
| GET | `/walkthroughs/{wt_id}/analytics` |
| GET | `/sdk/resource-center` |
| POST | `/walkthroughs/{wt_id}/validate` |

## Install

```sh
jarvis skill install nexus:walkthroughs-builder
```

Source of truth: `backend/routes/routes_walkthroughs_builder.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
