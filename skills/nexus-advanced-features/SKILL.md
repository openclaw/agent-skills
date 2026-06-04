---
name: nexus-advanced-features
description: "Benchmark Comparison, Collaboration Templates, Review Analytics, Security Dashboard. Use when an OpenJarvis user wants to call Nexus advanced.features (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: advanced.features
  source_file: backend/routes/routes_advanced_features.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus advanced.features

Benchmark Comparison, Collaboration Templates, Review Analytics, Security Dashboard.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `advanced.features` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/benchmarks/compare` |
| GET | `/orchestration-templates` |
| POST | `/orchestration-templates` |
| POST | `/workspaces/{ws_id}/orchestration-templates/{tpl_id}/install` |
| GET | `/marketplace/review-analytics` |
| GET | `/admin/security-dashboard` |
| GET | `/admin/observability` |

## Install

```sh
jarvis skill install nexus:advanced-features
```

Source of truth: `backend/routes/routes_advanced_features.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
