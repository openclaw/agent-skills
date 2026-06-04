---
name: nexus-benchmarks
description: "Agent Performance Benchmarks — Automated test conversations to validate training. Use when an OpenJarvis user wants to call Nexus benchmarks (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: benchmarks
  source_file: backend/routes/routes_benchmarks.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus benchmarks

Agent Performance Benchmarks — Automated test conversations to validate training.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `benchmarks` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/benchmarks/suites` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/benchmarks/suites` |
| DELETE | `/workspaces/{ws_id}/agents/{agent_id}/benchmarks/suites/{suite_id}` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/benchmarks/run` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/benchmarks/runs` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/benchmarks/runs/{run_id}` |

## Install

```sh
jarvis skill install nexus:benchmarks
```

Source of truth: `backend/routes/routes_benchmarks.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
