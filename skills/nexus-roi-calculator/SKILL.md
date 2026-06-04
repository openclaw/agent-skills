---
name: nexus-roi-calculator
description: "AI Agent Model ROI Calculator — Cost analysis, model comparison, and forecast. Use when an OpenJarvis user wants to call Nexus roi.calculator (GET) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: roi.calculator
  source_file: backend/routes/routes_roi_calculator.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus roi.calculator

AI Agent Model ROI Calculator — Cost analysis, model comparison, and forecast.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `roi.calculator` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/roi/summary` |
| GET | `/workspaces/{ws_id}/roi/by-model` |
| GET | `/workspaces/{ws_id}/roi/by-agent` |
| GET | `/workspaces/{ws_id}/roi/forecast` |

## Install

```sh
jarvis skill install nexus:roi-calculator
```

Source of truth: `backend/routes/routes_roi_calculator.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
