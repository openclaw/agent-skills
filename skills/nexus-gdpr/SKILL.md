---
name: nexus-gdpr
description: "HTTP surface for GDPR Art-17 erasure (segment 1.A.5). Use when an OpenJarvis user wants to call Nexus gdpr (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: gdpr
  source_file: backend/routes/routes_gdpr.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus gdpr

HTTP surface for GDPR Art-17 erasure (segment 1.A.5).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `gdpr` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/admin/gdpr/erasure-requests` |
| GET | `/admin/gdpr/erasure-requests` |
| GET | `/admin/gdpr/erasure-requests/{request_id}` |
| POST | `/admin/gdpr/erasure-requests/{request_id}/run` |
| GET | `/admin/gdpr/erasure-requests/{request_id}/audit` |

## Install

```sh
jarvis skill install nexus:gdpr
```

Source of truth: `backend/routes/routes_gdpr.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
