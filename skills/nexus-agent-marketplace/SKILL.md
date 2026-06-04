---
name: nexus-agent-marketplace
description: "AI Agent Marketplace — uses JSONB adapter for backward compatibility. Use when an OpenJarvis user wants to call Nexus agent.marketplace (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: agent.marketplace
  source_file: backend/routes/routes_agent_marketplace.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus agent.marketplace

AI Agent Marketplace — uses JSONB adapter for backward compatibility.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `agent.marketplace` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/marketplace/agents` |
| GET | `/marketplace/agents/{agent_id}` |
| POST | `/marketplace/agents` |
| PUT | `/marketplace/agents/{agent_id}` |
| DELETE | `/marketplace/agents/{agent_id}` |
| POST | `/marketplace/agents/{agent_id}/rate` |
| POST | `/marketplace/agents/{agent_id}/install` |
| GET | `/marketplace/my-agents` |
| GET | `/marketplace/installed` |
| GET | `/marketplace/agent-stats` |

## Install

```sh
jarvis skill install nexus:agent-marketplace
```

Source of truth: `backend/routes/routes_agent_marketplace.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
