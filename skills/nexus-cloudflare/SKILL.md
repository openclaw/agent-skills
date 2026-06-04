---
name: nexus-cloudflare
description: "Nexus cloudflare API surface. Use when an OpenJarvis user wants to call Nexus cloudflare (GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: cloudflare
  source_file: backend/routes/routes_cloudflare.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus cloudflare

Nexus user-callable surface exposing the `cloudflare` API.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `cloudflare` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/cloudflare/config` |
| PUT | `/cloudflare/config` |
| GET | `/cloudflare/ai-gateway/stats` |
| POST | `/cloudflare/r2/presign` |
| POST | `/cloudflare/r2/confirm` |
| GET | `/cloudflare/r2/files/{workspace_id}` |
| GET | `/cloudflare/kv/sync/auth` |
| GET | `/cloudflare/kv/sync/config` |
| GET | `/cloudflare/tunnels` |
| POST | `/cloudflare/tunnels/register` |
| GET | `/cloudflare/health` |

## Install

```sh
jarvis skill install nexus:cloudflare
```

Source of truth: `backend/routes/routes_cloudflare.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
