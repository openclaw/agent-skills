---
name: nexus-verticals
description: "Read-only API for the vertical scaffolding — Pod G segments 6.A.1 + 6.A.2. Use when an OpenJarvis user wants to call Nexus verticals (GET) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: verticals
  source_file: backend/routes/routes_verticals.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus verticals

Read-only API for the vertical scaffolding — Pod G segments 6.A.1 + 6.A.2.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `verticals` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/verticals` |
| GET | `/verticals/{vertical_id}` |
| GET | `/verticals/{vertical_id}/{asset_type}` |
| GET | `/verticals/{vertical_id}/{asset_type}/{name}` |

## Install

```sh
jarvis skill install nexus:verticals
```

Source of truth: `backend/routes/routes_verticals.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
