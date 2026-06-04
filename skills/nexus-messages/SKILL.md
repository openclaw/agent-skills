---
name: nexus-messages
description: "Message management routes — uses JSONB adapter for backward compatibility. Use when an OpenJarvis user wants to call Nexus messages (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: messages
  source_file: backend/routes/routes_messages.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus messages

Message management routes — uses JSONB adapter for backward compatibility.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `messages` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/channels/{channel_id}/messages` |
| POST | `/messages/{message_id}/react` |
| POST | `/messages/{message_id}/pin` |
| GET | `/channels/{channel_id}/search-messages` |
| GET | `/channels/{channel_id}/pinned` |
| POST | `/channels/{channel_id}/messages` |
| PUT | `/messages/{message_id}` |
| DELETE | `/messages/{message_id}` |

## Install

```sh
jarvis skill install nexus:messages
```

Source of truth: `backend/routes/routes_messages.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
