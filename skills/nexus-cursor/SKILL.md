---
name: nexus-cursor
description: "Nexus × Cursor 2 AI Integration — Cloud Agent API, MCP Server, AI Model Provider. Use when an OpenJarvis user wants to call Nexus cursor (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: cursor
  source_file: backend/routes/routes_cursor.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus cursor

Nexus × Cursor 2 AI Integration — Cloud Agent API, MCP Server, AI Model Provider.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `cursor` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/cursor/agent` |
| GET | `/workspaces/{ws_id}/cursor/sessions` |
| GET | `/cursor/sessions/{session_id}/artifacts` |
| GET | `/cursor/mcp/tools` |
| POST | `/cursor/mcp/invoke` |
| GET | `/cursor/mcp/config` |
| GET | `/workspaces/{ws_id}/cursor/analytics` |

## Install

```sh
jarvis skill install nexus:cursor
```

Source of truth: `backend/routes/routes_cursor.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
