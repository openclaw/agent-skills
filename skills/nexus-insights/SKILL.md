---
name: nexus-insights
description: "Insights-at-3-scopes routes (Agent A19, spec §6.4). Use when an OpenJarvis user wants to call Nexus insights (GET) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: insights
  source_file: backend/routes/routes_insights.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus insights

Insights-at-3-scopes routes (Agent A19, spec §6.4).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `insights` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/insights` |
| GET | `/orgs/{org_id}/insights` |
| GET | `/platform/insights` |

## Install

```sh
jarvis skill install nexus:insights
```

Source of truth: `backend/routes/routes_insights.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
