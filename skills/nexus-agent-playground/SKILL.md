---
name: nexus-agent-playground
description: "Nexus agent.playground API surface. Use when an OpenJarvis user wants to call Nexus agent.playground (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: agent.playground
  source_file: backend/routes/routes_agent_playground.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus agent.playground

Nexus user-callable surface exposing the `agent.playground` API.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `agent.playground` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/playground` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/playground/{session_id}` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/playground-sessions` |
| DELETE | `/workspaces/{ws_id}/agents/{agent_id}/playground/{session_id}` |
| POST | `/workspaces/{ws_id}/playground/multi-agent` |

## Install

```sh
jarvis skill install nexus:agent-playground
```

Source of truth: `backend/routes/routes_agent_playground.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
