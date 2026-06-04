---
name: nexus-plan-management
description: "Plan Management Routes — Self-service plan changes, trials, seat management, annual savings. Use when an OpenJarvis user wants to call Nexus plan.management (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: plan.management
  source_file: backend/routes/routes_plan_management.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus plan.management

Plan Management Routes — Self-service plan changes, trials, seat management, annual savings.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `plan.management` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/billing/plans/compare` |
| POST | `/billing/trial/start` |
| GET | `/billing/trial/status` |
| POST | `/billing/plan/change` |
| GET | `/billing/plan/current` |
| POST | `/billing/seats/add` |
| POST | `/billing/seats/remove` |
| GET | `/billing/seats` |
| GET | `/billing/annual-savings` |

## Install

```sh
jarvis skill install nexus:plan-management
```

Source of truth: `backend/routes/routes_plan_management.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
