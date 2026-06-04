---
name: nexus-arena
description: "Nexus arena API surface. Use when an OpenJarvis user wants to call Nexus arena (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: arena
  source_file: backend/routes/routes_arena.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus arena

Nexus user-callable surface exposing the `arena` API.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `arena` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/arena/battle` |
| GET | `/workspaces/{ws_id}/arena/battles` |
| GET | `/arena/battles/{battle_id}` |
| POST | `/arena/battles/{battle_id}/vote` |
| GET | `/workspaces/{ws_id}/arena/leaderboard` |

## Install

```sh
jarvis skill install nexus:arena
```

Source of truth: `backend/routes/routes_arena.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
