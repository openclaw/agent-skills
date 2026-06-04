---
name: nexus-observability
description: "LLM Observability routes — Trace explorer, stats dashboard, anomaly detection, config. Use when an OpenJarvis user wants to call Nexus observability (GET, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: observability
  source_file: backend/routes/routes_observability.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus observability

LLM Observability routes — Trace explorer, stats dashboard, anomaly detection, config.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `observability` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/observability/traces` |
| GET | `/workspaces/{ws_id}/observability/traces/{trace_id}` |
| GET | `/workspaces/{ws_id}/observability/stats` |
| GET | `/workspaces/{ws_id}/observability/anomalies` |
| GET | `/workspaces/{ws_id}/observability/models` |
| GET | `/workspaces/{ws_id}/observability/timeline` |
| GET | `/workspaces/{ws_id}/observability/config` |
| PUT | `/workspaces/{ws_id}/observability/config` |

## Install

```sh
jarvis skill install nexus:observability
```

Source of truth: `backend/routes/routes_observability.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
