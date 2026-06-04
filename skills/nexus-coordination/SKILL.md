---
name: nexus-coordination
description: "Nexus coordination API surface. Use when an OpenJarvis user wants to call Nexus coordination (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: coordination
  source_file: backend/routes/routes_coordination.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus coordination

Nexus user-callable surface exposing the `coordination` API.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `coordination` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/work-queue` |
| POST | `/workspaces/{ws_id}/work-queue` |
| PUT | `/work-queue/{item_id}/claim` |
| PUT | `/work-queue/{item_id}/complete` |
| GET | `/workspaces/{ws_id}/memory` |
| POST | `/workspaces/{ws_id}/memory` |
| DELETE | `/workspaces/{ws_id}/memory/{key}` |
| POST | `/workspaces/{ws_id}/check-duplicate` |
| GET | `/workspaces/{ws_id}/coordination-status` |
| GET | `/workspaces/{ws_id}/tpm-queue` |
| POST | `/workspaces/{ws_id}/tpm-queue` |
| PUT | `/workspaces/{ws_id}/tpm-queue/{directive_id}/complete` |
| POST | `/workspaces/{ws_id}/ask-tpm` |

## Install

```sh
jarvis skill install nexus:coordination
```

Source of truth: `backend/routes/routes_coordination.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
