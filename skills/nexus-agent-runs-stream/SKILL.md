---
name: nexus-agent-runs-stream
description: "SSE streaming variant of the agent-run execute-next endpoint. Use when an OpenJarvis user wants to call Nexus agent.runs.stream (POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: agent.runs.stream
  source_file: backend/routes/routes_agent_runs_stream.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
  flags: "streaming"
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus agent.runs.stream

SSE streaming variant of the agent-run execute-next endpoint.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `agent.runs.stream` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Flags

- `streaming`: surface uses streaming request/response handling.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/agent-runs/{run_id}/execute-next/stream` |

## Install

```sh
jarvis skill install nexus:agent-runs-stream
```

Source of truth: `backend/routes/routes_agent_runs_stream.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
