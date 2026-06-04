---
name: nexus-pam
description: "HTTP surface for Privileged Access Management (PAM). Use when an OpenJarvis user wants to call Nexus pam (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: pam
  source_file: backend/routes/routes_pam.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus pam

HTTP surface for Privileged Access Management (PAM).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `pam` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/pam/elevations` |
| POST | `/pam/elevations/{elevation_id}/approve` |
| POST | `/pam/elevations/{elevation_id}/deny` |
| POST | `/pam/elevations/{elevation_id}/revoke` |
| GET | `/pam/elevations/me` |
| GET | `/pam/elevations/pending` |
| GET | `/pam/elevations/{elevation_id}` |
| GET | `/pam/elevations/{elevation_id}/sessions` |

## Install

```sh
jarvis skill install nexus:pam
```

Source of truth: `backend/routes/routes_pam.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
