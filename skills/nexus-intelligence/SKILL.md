---
name: nexus-intelligence
description: "Intelligence v2 API routes. Use when an OpenJarvis user wants to call Nexus intelligence (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: intelligence
  source_file: backend/routes/routes_intelligence.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus intelligence

Intelligence v2 API routes.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `intelligence` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/profiler/summary` |
| GET | `/profiler/ranking/{task_type}` |
| GET | `/profiler/compare/{agent_a}/{agent_b}/{task_type}` |
| POST | `/router/route` |
| POST | `/decomposer/decompose` |
| POST | `/evaluator/evaluate` |
| GET | `/health/status` |
| GET | `/health/advisories` |
| POST | `/optimizer/propose` |
| POST | `/meta/run` |
| GET | `/loop/status` |
| GET | `/flags` |
| POST | `/flags/{module}` |

## Install

```sh
jarvis skill install nexus:intelligence
```

Source of truth: `backend/routes/routes_intelligence.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
