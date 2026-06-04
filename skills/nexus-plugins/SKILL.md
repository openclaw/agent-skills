---
name: nexus-plugins
description: "Messaging & Meeting Platform Plugins — Slack, Discord, Teams, Mattermost, WhatsApp, Signal, Telegram, Zoom. Use when an OpenJarvis user wants to call Nexus plugins (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: plugins
  source_file: backend/routes/routes_plugins.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus plugins

Messaging & Meeting Platform Plugins — Slack, Discord, Teams, Mattermost, WhatsApp, Signal, Telegram, Zoom

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `plugins` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/plugins/platforms` |
| POST | `/plugins/{platform}/connect` |
| POST | `/plugins/{platform}/callback` |
| GET | `/plugins/connections` |
| DELETE | `/plugins/connections/{conn_id}` |
| POST | `/plugins/{platform}/map-channel` |
| GET | `/plugins/channel-mappings` |
| DELETE | `/plugins/channel-mappings/{mapping_id}` |
| POST | `/plugins/{platform}/send` |
| POST | `/plugins/{platform}/webhook` |
| POST | `/plugins/zoom/create-meeting` |
| POST | `/plugins/zoom/webhook` |
| GET | `/plugins/messages` |
| GET | `/plugins/status` |

## Install

```sh
jarvis skill install nexus:plugins
```

Source of truth: `backend/routes/routes_plugins.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
