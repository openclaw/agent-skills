---
name: nexus-build
description: "Nexus Build API. Use when an OpenJarvis user wants to call Nexus build (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: build
  source_file: backend/routes/routes_build.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus build

Nexus Build API.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `build` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/build/apps` |
| GET | `/workspaces/{ws_id}/build/apps` |
| GET | `/workspaces/{ws_id}/build/apps/{app_id}` |
| POST | `/workspaces/{ws_id}/build/apps/{app_id}/iterate` |
| POST | `/workspaces/{ws_id}/build/apps/{app_id}/deploy` |
| DELETE | `/workspaces/{ws_id}/build/apps/{app_id}` |
| GET | `/workspaces/{ws_id}/build/apps/{app_id}/files` |
| GET | `/workspaces/{ws_id}/build/apps/{app_id}/files/{path:path}` |
| GET | `/workspaces/{ws_id}/build/apps/{app_id}/events` |
| POST | `/workspaces/{ws_id}/build/apps/{app_id}/edit` |
| GET | `/build/playbooks` |

## Install

```sh
jarvis skill install nexus:build
```

Source of truth: `backend/routes/routes_build.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
