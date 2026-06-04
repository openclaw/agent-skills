---
name: nexus-training-analytics
description: "Training Analytics — Knowledge effectiveness, gap detection, time-series metrics. Use when an OpenJarvis user wants to call Nexus training.analytics (GET) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: training.analytics
  source_file: backend/routes/routes_training_analytics.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus training.analytics

Training Analytics — Knowledge effectiveness, gap detection, time-series metrics.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `training.analytics` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/analytics/effectiveness` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/analytics/gaps` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/analytics/timeseries` |

## Install

```sh
jarvis skill install nexus:training-analytics
```

Source of truth: `backend/routes/routes_training_analytics.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
