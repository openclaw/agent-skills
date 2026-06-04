---
name: nexus-agent-teams
description: "Agent Teams API — Start, monitor, and govern autonomous agent team sessions. Use when an OpenJarvis user wants to call Nexus agent.teams (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: agent.teams
  source_file: backend/routes/routes_agent_teams.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus agent.teams

Agent Teams API — Start, monitor, and govern autonomous agent team sessions.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `agent.teams` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/agent-teams/start` |
| GET | `/workspaces/{ws_id}/agent-teams/{session_id}` |
| POST | `/workspaces/{ws_id}/agent-teams/{session_id}/approve` |
| GET | `/workspaces/{ws_id}/agent-teams` |
| GET | `/workspaces/{ws_id}/agent-team-templates` |
| POST | `/workspaces/{ws_id}/agent-team-templates` |
| DELETE | `/workspaces/{ws_id}/agent-team-templates/{template_id}` |
| POST | `/workspaces/{ws_id}/agent-teams/start-from-template` |

## Install

```sh
jarvis skill install nexus:agent-teams
```

Source of truth: `backend/routes/routes_agent_teams.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
