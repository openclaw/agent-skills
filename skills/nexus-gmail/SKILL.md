---
name: nexus-gmail
description: "Gmail Connector — OAuth + Gmail REST API integration for Nexus. Use when an OpenJarvis user wants to call Nexus gmail (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: gmail
  source_file: backend/routes/routes_gmail.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus gmail

Gmail Connector — OAuth + Gmail REST API integration for Nexus.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `gmail` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/gmail/status` |
| POST | `/gmail/connect` |
| GET | `/gmail/callback` |
| GET | `/gmail/connections` |
| DELETE | `/gmail/connections/{connection_id}` |
| GET | `/gmail/messages` |
| GET | `/gmail/messages/{message_id}` |
| GET | `/gmail/threads/{thread_id}` |
| POST | `/gmail/messages/send` |
| POST | `/gmail/drafts` |
| GET | `/gmail/drafts` |
| POST | `/gmail/messages/{message_id}/modify` |
| GET | `/gmail/labels` |

## Install

```sh
jarvis skill install nexus:gmail
```

Source of truth: `backend/routes/routes_gmail.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
