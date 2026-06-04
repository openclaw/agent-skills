---
name: nexus-module-assignments
description: "Role-assignment + per-user override routes for Profile/Permissions (Agent A07). Use when an OpenJarvis user wants to call Nexus module.assignments (DELETE, GET, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: module.assignments
  source_file: backend/routes/routes_module_assignments.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus module.assignments

Role-assignment + per-user override routes for Profile/Permissions (Agent A07).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `module.assignments` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/users/{user_id}/role` |
| PUT | `/workspaces/{ws_id}/users/{user_id}/role` |
| GET | `/workspaces/{ws_id}/users/{user_id}/overrides` |
| PUT | `/workspaces/{ws_id}/users/{user_id}/overrides/{module_id}` |
| DELETE | `/workspaces/{ws_id}/users/{user_id}/overrides/{module_id}` |

## Install

```sh
jarvis skill install nexus:module-assignments
```

Source of truth: `backend/routes/routes_module_assignments.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
