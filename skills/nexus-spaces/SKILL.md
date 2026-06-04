---
name: nexus-spaces
description: "HTTP surface for Spaces (WebRTC voice/video rooms) + presence — Pod F 5.C.2. Use when an OpenJarvis user wants to call Nexus spaces (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: spaces
  source_file: backend/routes/routes_spaces.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus spaces

HTTP surface for Spaces (WebRTC voice/video rooms) + presence — Pod F 5.C.2.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `spaces` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/channels/{channel_id}/spaces` |
| GET | `/channels/{channel_id}/spaces` |
| POST | `/spaces/{space_id}/join` |
| POST | `/spaces/{space_id}/leave` |
| POST | `/presence/heartbeat` |
| GET | `/presence/{workspace_id}` |

## Install

```sh
jarvis skill install nexus:spaces
```

Source of truth: `backend/routes/routes_spaces.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
