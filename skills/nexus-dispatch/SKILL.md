---
name: nexus-dispatch
description: "Dispatch REST routes — phone↔desktop persistent thread per user. Use when an OpenJarvis user wants to call Nexus dispatch (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: dispatch
  source_file: backend/routes/routes_dispatch.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus dispatch

Dispatch REST routes — phone↔desktop persistent thread per user.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `dispatch` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/me/dispatch/thread` |
| GET | `/dispatch/threads/{thread_id}/messages` |
| POST | `/dispatch/threads/{thread_id}/messages` |
| POST | `/dispatch/threads/{thread_id}/spawn` |
| POST | `/dispatch/threads/{thread_id}/pair` |

## Install

```sh
jarvis skill install nexus:dispatch
```

Source of truth: `backend/routes/routes_dispatch.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
