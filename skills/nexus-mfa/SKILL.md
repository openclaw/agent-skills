---
name: nexus-mfa
description: "MFA/TOTP Routes — Multi-factor authentication with TOTP, backup codes, and admin enforcement. Use when an OpenJarvis user wants to call Nexus mfa (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: mfa
  source_file: backend/routes/routes_mfa.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus mfa

MFA/TOTP Routes — Multi-factor authentication with TOTP, backup codes, and admin enforcement.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `mfa` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/auth/mfa/setup` |
| POST | `/auth/mfa/setup/confirm` |
| POST | `/auth/mfa/verify` |
| POST | `/auth/mfa/disable` |
| GET | `/auth/mfa/status` |
| POST | `/auth/mfa/regenerate-backup` |

## Install

```sh
jarvis skill install nexus:mfa
```

Source of truth: `backend/routes/routes_mfa.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
