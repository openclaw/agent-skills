---
name: nexus-auth-email
description: "Nexus auth.email API surface. Use when an OpenJarvis user wants to call Nexus auth.email (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: auth.email
  source_file: backend/routes/routes_auth_email.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus auth.email

Nexus user-callable surface exposing the `auth.email` API.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `auth.email` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/auth/register` |
| POST | `/auth/login` |
| POST | `/auth/forgot-password-legacy` |
| GET | `/auth/verify-email` |
| GET | `/user/sessions` |
| DELETE | `/user/sessions/{session_id}` |
| DELETE | `/user/sessions` |
| POST | `/auth/reset-password-legacy` |

## Install

```sh
jarvis skill install nexus:auth-email
```

Source of truth: `backend/routes/routes_auth_email.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
