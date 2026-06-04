---
name: nexus-nexus-agents
description: "Nexus Agent routes - custom workspace-specific AI agents. Use when an OpenJarvis user wants to call Nexus nexus.agents (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: nexus.agents
  source_file: backend/routes/routes_nexus_agents.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus nexus.agents

Nexus Agent routes - custom workspace-specific AI agents

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `nexus.agents` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/agents` |
| POST | `/workspaces/{workspace_id}/agents` |
| GET | `/workspaces/{workspace_id}/agents/{agent_id}` |
| PUT | `/workspaces/{workspace_id}/agents/{agent_id}` |
| DELETE | `/workspaces/{workspace_id}/agents/{agent_id}` |
| GET | `/workspaces/{workspace_id}/available-models` |

## Install

```sh
jarvis skill install nexus:nexus-agents
```

Source of truth: `backend/routes/routes_nexus_agents.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
