---
name: nexus-keystone
description: "Keystone Feature Routes — Consensus, Workspace-as-Code, Cost Arbitrage, GDPR, Key Rotation. Use when an OpenJarvis user wants to call Nexus keystone (GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: keystone
  source_file: backend/routes/routes_keystone.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus keystone

Keystone Feature Routes — Consensus, Workspace-as-Code, Cost Arbitrage, GDPR, Key Rotation.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `keystone` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/channels/{channel_id}/consensus/trigger` |
| GET | `/channels/{channel_id}/consensus/latest` |
| GET | `/consensus/{session_id}` |
| POST | `/workspaces/{ws_id}/export` |
| POST | `/workspaces/import` |
| GET | `/workspaces/{ws_id}/manifest` |
| GET | `/workspaces/{ws_id}/cost-arbitrage/config` |
| PUT | `/workspaces/{ws_id}/cost-arbitrage/config` |
| POST | `/workspaces/{ws_id}/cost-arbitrage/route` |
| POST | `/admin/gdpr/erase/{user_id}` |
| POST | `/account/request-deletion` |
| POST | `/developer/api-keys/{key_id}/rotate` |
| GET | `/admin/circuit-breaker` |
| GET | `/billing/usage-check` |

## Install

```sh
jarvis skill install nexus:keystone
```

Source of truth: `backend/routes/routes_keystone.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
