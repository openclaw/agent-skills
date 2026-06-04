---
name: nexus-repository
description: "Repository — Org-level file store with indexing, search, and preview. Use when an OpenJarvis user wants to call Nexus repository (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: repository
  source_file: backend/routes/routes_repository.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus repository

Repository — Org-level file store with indexing, search, and preview.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `repository` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/orgs/{org_id}/repository/upload` |
| GET | `/orgs/{org_id}/repository` |
| GET | `/repository/{file_id}` |
| GET | `/repository/{file_id}/data` |
| GET | `/repository/{file_id}/preview` |
| PUT | `/repository/{file_id}` |
| DELETE | `/repository/{file_id}` |
| GET | `/orgs/{org_id}/repository/folders` |
| GET | `/admin/integrations` |
| POST | `/admin/integrations` |
| POST | `/admin/integrations/test` |
| GET | `/orgs/{org_id}/integrations` |
| POST | `/orgs/{org_id}/integrations` |
| DELETE | `/orgs/{org_id}/integrations/{key_name}` |
| GET | `/orgs/{org_id}/encryption-status` |
| POST | `/orgs/{org_id}/encryption/generate-key` |

## Install

```sh
jarvis skill install nexus:repository
```

Source of truth: `backend/routes/routes_repository.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
