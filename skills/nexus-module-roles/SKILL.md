---
name: nexus-module-roles
description: "Custom module-role CRUD routes (Agent A06). Use when an OpenJarvis user wants to call Nexus module.roles (DELETE, GET, PATCH, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: module.roles
  source_file: backend/routes/routes_module_roles.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus module.roles

Custom module-role CRUD routes (Agent A06).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `module.roles` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/orgs/{org_id}/roles` |
| POST | `/orgs/{org_id}/roles` |
| PATCH | `/orgs/{org_id}/roles/{role_id}` |
| DELETE | `/orgs/{org_id}/roles/{role_id}` |

## Install

```sh
jarvis skill install nexus:module-roles
```

Source of truth: `backend/routes/routes_module_roles.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
