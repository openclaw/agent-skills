---
name: nexus-legal
description: "Legal compliance routes — ToS, Privacy, AUP, GDPR, account deletion, data export. Use when an OpenJarvis user wants to call Nexus legal (GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: legal
  source_file: backend/routes/routes_legal.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus legal

Legal compliance routes — ToS, Privacy, AUP, GDPR, account deletion, data export

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `legal` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/legal/tos-version` |
| POST | `/legal/accept-tos` |
| GET | `/legal/tos-status` |
| POST | `/legal/cookie-consent` |
| POST | `/user/export-data` |
| POST | `/user/delete-account` |
| POST | `/content/flag` |
| GET | `/admin/content-flags` |
| PUT | `/admin/content-flags/{flag_id}` |
| POST | `/billing/cancel` |
| POST | `/legal/voice-consent` |
| POST | `/orgs/{org_id}/accept-dpa` |

## Install

```sh
jarvis skill install nexus:legal
```

Source of truth: `backend/routes/routes_legal.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
