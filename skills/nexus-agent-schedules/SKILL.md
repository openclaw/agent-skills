---
name: nexus-agent-schedules
description: "Agent Schedules - cron-like scheduled actions for AI agents in workspaces. Use when an OpenJarvis user wants to call Nexus agent.schedules (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: agent.schedules
  source_file: backend/routes/routes_agent_schedules.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus agent.schedules

Agent Schedules - cron-like scheduled actions for AI agents in workspaces

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `agent.schedules` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/schedules` |
| POST | `/workspaces/{workspace_id}/schedules` |
| PUT | `/schedules/{schedule_id}` |
| DELETE | `/schedules/{schedule_id}` |
| POST | `/schedules/{schedule_id}/run` |
| GET | `/schedules/{schedule_id}/history` |
| GET | `/schedules/action-types` |

## Install

```sh
jarvis skill install nexus:agent-schedules
```

Source of truth: `backend/routes/routes_agent_schedules.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
