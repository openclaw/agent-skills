---
name: nexus-error-tracking
description: "Error Tracking Routes — Self-hosted error capture and viewer for production errors. Use when an OpenJarvis user wants to call Nexus error.tracking (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: error.tracking
  source_file: backend/routes/routes_error_tracking.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus error.tracking

Error Tracking Routes — Self-hosted error capture and viewer for production errors.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `error.tracking` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/errors/report` |
| GET | `/admin/errors` |
| PUT | `/admin/errors/{error_id}/resolve` |
| DELETE | `/admin/errors/{error_id}` |
| GET | `/admin/errors/stats` |

## Install

```sh
jarvis skill install nexus:error-tracking
```

Source of truth: `backend/routes/routes_error_tracking.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
