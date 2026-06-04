---
name: nexus-openclaw
description: "Nexus × OpenClaw Bidirectional Integration — Bridge endpoints for messaging gateway. Use when an OpenJarvis user wants to call Nexus openclaw (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: openclaw
  source_file: backend/routes/routes_openclaw.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus openclaw

Nexus × OpenClaw Bidirectional Integration — Bridge endpoints for messaging gateway.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `openclaw` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/openclaw/health` |
| POST | `/openclaw/message` |
| GET | `/openclaw/session` |
| POST | `/openclaw/session/reset` |
| GET | `/openclaw/agents` |
| POST | `/openclaw/pipelines/trigger` |
| GET | `/openclaw/pipelines/{run_id}` |
| GET | `/openclaw/deployments` |
| POST | `/openclaw/knowledge/search` |
| GET | `/openclaw/analytics` |
| POST | `/openclaw/notify` |
| POST | `/openclaw/media` |
| GET | `/openclaw/media/{media_id}` |
| POST | `/openclaw/tokens` |
| GET | `/openclaw/tokens` |
| DELETE | `/openclaw/tokens/{token_id}` |
| GET | `/openclaw/mappings/{workspace_id}` |
| POST | `/openclaw/mappings` |
| DELETE | `/openclaw/mappings/{mapping_id}` |
| GET | `/openclaw/activity/{workspace_id}` |

## Install

```sh
jarvis skill install nexus:openclaw
```

Source of truth: `backend/routes/routes_openclaw.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
