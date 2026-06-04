---
name: nexus-embed-chat
description: "White-Label & Embeddable Chat Widget routes. Use when an OpenJarvis user wants to call Nexus embed.chat (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: embed.chat
  source_file: backend/routes/routes_embed_chat.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus embed.chat

White-Label & Embeddable Chat Widget routes.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `embed.chat` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/embed-chat/widgets` |
| GET | `/workspaces/{ws_id}/embed-chat/widgets` |
| PUT | `/workspaces/{ws_id}/embed-chat/widgets/{widget_id}` |
| DELETE | `/workspaces/{ws_id}/embed-chat/widgets/{widget_id}` |
| GET | `/workspaces/{ws_id}/embed-chat/widgets/{widget_id}/analytics` |
| GET | `/embed/widget/{widget_id}/config` |
| POST | `/embed/widget/{widget_id}/message` |
| GET | `/embed/widget/{widget_id}/history` |

## Install

```sh
jarvis skill install nexus:embed-chat
```

Source of truth: `backend/routes/routes_embed_chat.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
