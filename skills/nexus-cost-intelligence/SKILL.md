---
name: nexus-cost-intelligence
description: "AI Cost Intelligence — Real-time cost tracking, budgets, alerts, and smart model routing. Use when an OpenJarvis user wants to call Nexus cost.intelligence (GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: cost.intelligence
  source_file: backend/routes/routes_cost_intelligence.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus cost.intelligence

AI Cost Intelligence — Real-time cost tracking, budgets, alerts, and smart model routing.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `cost.intelligence` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/costs` |
| GET | `/workspaces/{ws_id}/costs/actual` |
| POST | `/workspaces/{ws_id}/costs/refresh` |
| GET | `/workspaces/{ws_id}/costs/by-project` |
| GET | `/workspaces/{ws_id}/budget` |
| PUT | `/workspaces/{ws_id}/budget` |
| POST | `/prompts/{prompt_id}/rate` |

## Install

```sh
jarvis skill install nexus:cost-intelligence
```

Source of truth: `backend/routes/routes_cost_intelligence.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
