---
name: nexus-mail-connections
description: "Mail connection management — connect Gmail, Microsoft, iCloud, IMAP accounts. Use when an OpenJarvis user wants to call Nexus mail.connections (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: mail.connections
  source_file: backend/routes/routes_mail_connections.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus mail.connections

Mail connection management — connect Gmail, Microsoft, iCloud, IMAP accounts.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `mail.connections` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/mail/connections` |
| POST | `/workspaces/{ws_id}/mail/connections` |
| PUT | `/workspaces/{ws_id}/mail/connections/{conn_id}` |
| DELETE | `/workspaces/{ws_id}/mail/connections/{conn_id}` |
| GET | `/workspaces/{ws_id}/mail/providers` |

## Install

```sh
jarvis skill install nexus:mail-connections
```

Source of truth: `backend/routes/routes_mail_connections.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
