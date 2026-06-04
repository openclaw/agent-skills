---
name: nexus-custom-tools
description: "Custom Tools / API Gateway routes — CRUD, test, execute, catalog, OpenAPI import. Use when an OpenJarvis user wants to call Nexus custom.tools (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: custom.tools
  source_file: backend/routes/routes_custom_tools.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus custom.tools

Custom Tools / API Gateway routes — CRUD, test, execute, catalog, OpenAPI import.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `custom.tools` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/custom-tools` |
| POST | `/workspaces/{ws_id}/custom-tools` |
| PUT | `/workspaces/{ws_id}/custom-tools/{tool_id}` |
| GET | `/workspaces/{ws_id}/custom-tools/catalog` |
| POST | `/workspaces/{ws_id}/custom-tools/from-template` |
| POST | `/workspaces/{ws_id}/custom-tools/from-openapi` |
| GET | `/workspaces/{ws_id}/custom-tools/{tool_id}` |
| DELETE | `/workspaces/{ws_id}/custom-tools/{tool_id}` |
| POST | `/workspaces/{ws_id}/custom-tools/{tool_id}/test` |
| POST | `/workspaces/{ws_id}/custom-tools/{tool_id}/execute` |
| GET | `/workspaces/{ws_id}/custom-tools/{tool_id}/executions` |

## Install

```sh
jarvis skill install nexus:custom-tools
```

Source of truth: `backend/routes/routes_custom_tools.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
