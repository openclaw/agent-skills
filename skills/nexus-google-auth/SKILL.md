---
name: nexus-google-auth
description: "Extracted from server.py — auto-generated module. Use when an OpenJarvis user wants to call Nexus google.auth (GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: google.auth
  source_file: backend/routes/routes_google_auth.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus google.auth

Extracted from server.py — auto-generated module.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `google.auth` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/auth/google/status` |
| GET | `/auth/google/login` |
| GET | `/auth/google/callback` |
| POST | `/auth/session` |
| GET | `/auth/me` |
| PUT | `/auth/profile` |
| POST | `/auth/logout` |

## Install

```sh
jarvis skill install nexus:google-auth
```

Source of truth: `backend/routes/routes_google_auth.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
