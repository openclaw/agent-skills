---
name: nexus-workspace-agents
description: "Workspace Agents routes. Use when an OpenJarvis user wants to call Nexus workspace.agents (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: workspace.agents
  source_file: backend/routes/routes_workspace_agents.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus workspace.agents

Workspace Agents routes.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `workspace.agents` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/workspace-agents` |
| POST | `/workspaces/{workspace_id}/workspace-agents` |
| GET | `/workspace-agents/{agent_id}` |
| PUT | `/workspace-agents/{agent_id}` |
| DELETE | `/workspace-agents/{agent_id}` |
| POST | `/workspace-agents/{agent_id}/invoke` |
| POST | `/workspaces/{workspace_id}/agents/{agent_id}/test` |

## Install

```sh
jarvis skill install nexus:workspace-agents
```

Source of truth: `backend/routes/routes_workspace_agents.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
