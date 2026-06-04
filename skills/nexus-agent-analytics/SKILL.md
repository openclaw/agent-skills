---
name: nexus-agent-analytics
description: "Agent Analytics routes — performance dashboards, comparison, cost breakdown. Use when an OpenJarvis user wants to call Nexus agent.analytics (GET) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: agent.analytics
  source_file: backend/routes/routes_agent_analytics.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus agent.analytics

Agent Analytics routes — performance dashboards, comparison, cost breakdown.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `agent.analytics` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/analytics` |
| GET | `/workspaces/{ws_id}/agents/compare` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/cost-breakdown` |

## Install

```sh
jarvis skill install nexus:agent-analytics
```

Source of truth: `backend/routes/routes_agent_analytics.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
