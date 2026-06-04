---
name: nexus-modules
description: "Module Configuration Routes — CRUD for workspace modules, wizard, bundles. Use when an OpenJarvis user wants to call Nexus modules (GET, PATCH, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: modules
  source_file: backend/routes/routes_modules.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus modules

Module Configuration Routes — CRUD for workspace modules, wizard, bundles.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `modules` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/admin/platform-modules` |
| PUT | `/admin/platform-modules` |
| GET | `/modules/resolved` |
| GET | `/modules/catalog` |
| PATCH | `/orgs/{org_id}/modules` |
| PATCH | `/workspaces/{ws_id}/modules` |
| GET | `/users/me/effective-modules` |
| GET | `/modules/registry` |
| GET | `/modules/bundles` |
| GET | `/workspaces/{ws_id}/modules` |
| PUT | `/workspaces/{ws_id}/modules` |
| POST | `/workspaces/{ws_id}/modules/wizard` |
| GET | `/workspaces/{ws_id}/modules/usage` |
| GET | `/workspaces/{ws_id}/modules/dashboard` |
| GET | `/orgs/{org_id}/module-defaults` |
| PUT | `/orgs/{org_id}/module-defaults` |

## Install

```sh
jarvis skill install nexus:modules
```

Source of truth: `backend/routes/routes_modules.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
