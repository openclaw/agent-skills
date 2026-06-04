---
name: nexus-usage-metering
description: "Usage-Based Pricing Granularity — Fine-grained usage event recording, summaries,. Use when an OpenJarvis user wants to call Nexus usage.metering (GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: usage.metering
  source_file: backend/routes/routes_usage_metering.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus usage.metering

Usage-Based Pricing Granularity — Fine-grained usage event recording, summaries,

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `usage.metering` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/usage/record` |
| GET | `/workspaces/{ws_id}/usage/summary` |
| GET | `/workspaces/{ws_id}/usage/by-model` |
| GET | `/workspaces/{ws_id}/usage/by-user` |
| GET | `/workspaces/{ws_id}/usage/by-agent` |
| GET | `/workspaces/{ws_id}/usage/forecast` |
| GET | `/workspaces/{ws_id}/usage/limits` |
| PUT | `/workspaces/{ws_id}/usage/limits` |
| GET | `/orgs/{org_id}/usage/rollup` |

## Install

```sh
jarvis skill install nexus:usage-metering
```

Source of truth: `backend/routes/routes_usage_metering.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
