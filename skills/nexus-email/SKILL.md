---
name: nexus-email
description: "Email Notification Service — Resend-based transactional email for password resets, invitations, system notifications. Use when an OpenJarvis user wants to call Nexus email (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: email
  source_file: backend/routes/routes_email.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus email

Email Notification Service — Resend-based transactional email for password resets, invitations, system notifications

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `email` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/auth/forgot-password` |
| POST | `/auth/reset-password` |
| POST | `/email/invite` |
| POST | `/email/notify` |
| POST | `/email/notify-bulk` |
| GET | `/email/status` |
| POST | `/email/test` |
| GET | `/email/log` |

## Install

```sh
jarvis skill install nexus:email
```

Source of truth: `backend/routes/routes_email.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
