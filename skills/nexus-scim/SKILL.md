---
name: nexus-scim
description: "SCIM 2.0 Provisioning Routes — User and group sync for enterprise identity providers. Use when an OpenJarvis user wants to call Nexus scim (DELETE, GET, PATCH, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: scim
  source_file: backend/routes/routes_scim.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus scim

SCIM 2.0 Provisioning Routes — User and group sync for enterprise identity providers.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `scim` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/scim/v2/Users` |
| GET | `/scim/v2/Users/{user_id}` |
| POST | `/scim/v2/Users` |
| PUT | `/scim/v2/Users/{user_id}` |
| PATCH | `/scim/v2/Users/{user_id}` |
| DELETE | `/scim/v2/Users/{user_id}` |
| GET | `/scim/v2/Groups` |
| POST | `/admin/scim/tokens` |
| GET | `/admin/scim/tokens` |
| DELETE | `/admin/scim/tokens/{token_id}` |

## Install

```sh
jarvis skill install nexus:scim
```

Source of truth: `backend/routes/routes_scim.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
