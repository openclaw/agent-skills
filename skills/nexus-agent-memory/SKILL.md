---
name: nexus-agent-memory
description: "Agent Memory — uses JSONB adapter for backward compatibility. Use when an OpenJarvis user wants to call Nexus agent.memory (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: agent.memory
  source_file: backend/routes/routes_agent_memory.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus agent.memory

Agent Memory — uses JSONB adapter for backward compatibility.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `agent.memory` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/agent-memory` |
| POST | `/workspaces/{ws_id}/agent-memory` |
| PUT | `/agent-memory/{mem_id}` |
| DELETE | `/agent-memory/{mem_id}` |
| GET | `/workspaces/{ws_id}/agent-memory/search` |
| GET | `/workspaces/{ws_id}/agent-memory/context` |
| POST | `/workspaces/{ws_id}/agent-memory/auto-extract` |
| GET | `/workspaces/{ws_id}/agent-memory/relevant` |
| DELETE | `/workspaces/{ws_id}/agent-memory/{memory_id}` |
| PUT | `/workspaces/{ws_id}/agent-memory/{memory_id}` |
| POST | `/workspaces/{ws_id}/agent-memory/prune` |

## Install

```sh
jarvis skill install nexus:agent-memory
```

Source of truth: `backend/routes/routes_agent_memory.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
