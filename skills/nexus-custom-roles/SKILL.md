---
name: nexus-custom-roles
description: "HTTP surface for custom roles (org-defined permission bundles). Use when an OpenJarvis user wants to call Nexus custom.roles (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: custom.roles
  source_file: backend/routes/routes_custom_roles.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus custom.roles

HTTP surface for custom roles (org-defined permission bundles).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `custom.roles` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/custom-roles` |
| GET | `/custom-roles` |
| GET | `/custom-roles/{role_id}` |
| PUT | `/custom-roles/{role_id}` |
| DELETE | `/custom-roles/{role_id}` |
| POST | `/custom-roles/{role_id}/assignments` |
| DELETE | `/custom-roles/{role_id}/assignments/{user_id}` |
| GET | `/users/{target_user_id}/effective-scopes` |

## Install

```sh
jarvis skill install nexus:custom-roles
```

Source of truth: `backend/routes/routes_custom_roles.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
