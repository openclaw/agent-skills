---
name: nexus-agent-leaderboard
description: "Cross-Workspace Agent Leaderboard + Knowledge Deduplication & Quality Scoring. Use when an OpenJarvis user wants to call Nexus agent.leaderboard (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: agent.leaderboard
  source_file: backend/routes/routes_agent_leaderboard.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus agent.leaderboard

Cross-Workspace Agent Leaderboard + Knowledge Deduplication & Quality Scoring.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `agent.leaderboard` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/leaderboard/agents` |
| GET | `/leaderboard/skills` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/knowledge/deduplicate` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/knowledge/deduplicate/apply` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/knowledge/rescore` |
| GET | `/leaderboard/snapshots` |
| POST | `/leaderboard/snapshot` |

## Install

```sh
jarvis skill install nexus:agent-leaderboard
```

Source of truth: `backend/routes/routes_agent_leaderboard.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
