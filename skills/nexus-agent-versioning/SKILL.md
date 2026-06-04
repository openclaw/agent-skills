---
name: nexus-agent-versioning
description: "Agent Versioning & Rollback — Snapshot and restore agent configurations + knowledge. Use when an OpenJarvis user wants to call Nexus agent.versioning (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: agent.versioning
  source_file: backend/routes/routes_agent_versioning.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus agent.versioning

Agent Versioning & Rollback — Snapshot and restore agent configurations + knowledge.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `agent.versioning` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/versions` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/versions` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/versions/{version_id}` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/versions/{version_id}/rollback` |
| DELETE | `/workspaces/{ws_id}/agents/{agent_id}/versions/{version_id}` |

## Install

```sh
jarvis skill install nexus:agent-versioning
```

Source of truth: `backend/routes/routes_agent_versioning.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
