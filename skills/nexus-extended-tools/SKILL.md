---
name: nexus-extended-tools
description: "Extended Tool API Routes — Expose manifesto tools as REST endpoints. Use when an OpenJarvis user wants to call Nexus extended.tools (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: extended.tools
  source_file: backend/routes/routes_extended_tools.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus extended.tools

Extended Tool API Routes — Expose manifesto tools as REST endpoints.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `extended.tools` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/tools/web-search` |
| POST | `/tools/ask-human` |
| POST | `/tools/read-file` |
| POST | `/workspaces/{ws_id}/decisions` |
| GET | `/workspaces/{ws_id}/decisions` |
| POST | `/tools/search-channels` |
| POST | `/tools/send-alert` |
| POST | `/channels/{ch_id}/branch` |
| GET | `/workspaces/{ws_id}/agent-skills/{agent_key}` |
| POST | `/tools/web-fetch` |
| POST | `/tools/web-search-train` |
| GET | `/workspaces/{ws_id}/web-training-runs` |
| POST | `/tools/spawn-workers` |
| GET | `/workspaces/{ws_id}/worker-spawns` |
| GET | `/workspaces/{ws_id}/worker-spawns/{spawn_id}` |

## Install

```sh
jarvis skill install nexus:extended-tools
```

Source of truth: `backend/routes/routes_extended_tools.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
