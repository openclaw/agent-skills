---
name: nexus-federated-search
description: "Federated search API — fan out across enterprise connectors. Use when an OpenJarvis user wants to call Nexus federated.search (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: federated.search
  source_file: backend/routes/routes_federated_search.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus federated.search

Federated search API — fan out across enterprise connectors.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `federated.search` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/federated-search/connectors` |
| POST | `/workspaces/{ws_id}/federated-search` |

## Install

```sh
jarvis skill install nexus:federated-search
```

Source of truth: `backend/routes/routes_federated_search.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
