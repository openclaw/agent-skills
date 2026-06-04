---
name: nexus-agent-studio
description: "Agent Creator Studio routes — wizard, versioning, clone, publish, preview. Use when an OpenJarvis user wants to call Nexus agent.studio (PATCH, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: agent.studio
  source_file: backend/routes/routes_agent_studio.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus agent.studio

Agent Creator Studio routes — wizard, versioning, clone, publish, preview.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `agent.studio` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/agents/studio` |
| PUT | `/workspaces/{ws_id}/agents/{agent_id}/studio` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/rollback/{version}` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/clone` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/publish` |
| PATCH | `/workspaces/{ws_id}/agents/{agent_id}/status` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/preview` |

## Install

```sh
jarvis skill install nexus:agent-studio
```

Source of truth: `backend/routes/routes_agent_studio.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
