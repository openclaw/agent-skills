---
name: nexus-nx-features
description: "NX-001: Transparent Model Routing Engine — Visible, controllable model routing. Use when an OpenJarvis user wants to call Nexus nx.features (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: nx.features
  source_file: backend/routes/routes_nx_features.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus nx.features

NX-001: Transparent Model Routing Engine — Visible, controllable model routing.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `nx.features` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/routing/active` |
| GET | `/workspaces/{ws_id}/routing/logs` |
| POST | `/workspaces/{ws_id}/routing/override` |
| POST | `/workspaces/{ws_id}/routing/compare` |
| GET | `/workspaces/{ws_id}/routing/rules` |
| POST | `/workspaces/{ws_id}/routing/rules` |
| DELETE | `/workspaces/{ws_id}/routing/rules/{rule_id}` |
| POST | `/workspaces/{ws_id}/branch` |
| POST | `/workspaces/{ws_id}/snapshots` |
| GET | `/workspaces/{ws_id}/snapshots` |
| GET | `/workspaces/{ws_id}/context-summary` |
| POST | `/workspaces/{ws_id}/cost/estimate` |
| GET | `/workspaces/{ws_id}/cost/budgets` |
| POST | `/workspaces/{ws_id}/cost/budgets` |
| DELETE | `/workspaces/{ws_id}/cost/budgets/{budget_id}` |
| GET | `/workspaces/{ws_id}/cost/attribution` |
| GET | `/mcp/connectors` |
| POST | `/workspaces/{ws_id}/mcp/connect` |
| GET | `/workspaces/{ws_id}/mcp/connections` |
| GET | `/workspaces/{ws_id}/mcp/debug/{connection_id}` |
| GET | `/workspaces/{ws_id}/execution-traces` |
| GET | `/workspaces/{ws_id}/execution-traces/{trace_id}` |
| POST | `/workspaces/{ws_id}/execution-traces/{trace_id}/replay/{step_id}` |
| POST | `/workspaces/{ws_id}/execution-traces/{trace_id}/fork/{step_id}` |
| GET | `/workspaces/{ws_id}/execution-traces/{trace_id}/export` |
| GET | `/workspaces/{ws_id}/execution-traces/diff` |

## Install

```sh
jarvis skill install nexus:nx-features
```

Source of truth: `backend/routes/routes_nx_features.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
