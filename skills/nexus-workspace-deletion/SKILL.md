---
name: nexus-workspace-deletion
description: "Nexus workspace.deletion API surface. Use when an OpenJarvis user wants to call Nexus workspace.deletion (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: workspace.deletion
  source_file: backend/routes/routes_workspace_deletion.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus workspace.deletion

Nexus user-callable surface exposing the `workspace.deletion` API.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `workspace.deletion` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| DELETE | `/workspaces/{ws_id}` |
| POST | `/workspaces/bulk-delete` |
| GET | `/workspaces/{ws_id}/delete-preview` |

## Install

```sh
jarvis skill install nexus:workspace-deletion
```

Source of truth: `backend/routes/routes_workspace_deletion.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
