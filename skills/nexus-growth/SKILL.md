---
name: nexus-growth
description: "Growth analytics HTTP surface — Pod H segment 7.A.1. Use when an OpenJarvis user wants to call Nexus growth (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: growth
  source_file: backend/routes/routes_growth.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus growth

Growth analytics HTTP surface — Pod H segment 7.A.1.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `growth` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/growth/funnel` |
| GET | `/growth/workspaces/{workspace_id}/health` |
| GET | `/growth/benchmarks/{cohort}` |
| POST | `/growth/events/funnel` |

## Install

```sh
jarvis skill install nexus:growth
```

Source of truth: `backend/routes/routes_growth.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
