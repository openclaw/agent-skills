---
name: nexus-agent-runs
description: "Agent-run HTTP surface — Cursor \"agent mode\" parity. Use when an OpenJarvis user wants to call Nexus agent.runs (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: agent.runs
  source_file: backend/routes/routes_agent_runs.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus agent.runs

Agent-run HTTP surface — Cursor "agent mode" parity.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `agent.runs` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/code-repo/agent-runs` |
| GET | `/workspaces/{workspace_id}/code-repo/agent-runs` |
| GET | `/agent-runs/{run_id}` |
| POST | `/agent-runs/{run_id}/execute-next` |
| POST | `/agent-runs/{run_id}/steps/{idx}/accept` |
| POST | `/agent-runs/{run_id}/steps/{idx}/reject` |
| POST | `/agent-runs/{run_id}/cancel` |

## Install

```sh
jarvis skill install nexus:agent-runs
```

Source of truth: `backend/routes/routes_agent_runs.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
