---
name: nexus-memgraph
description: "Memgraph Native Graph Engine — REST API Routes. Use when an OpenJarvis user wants to call Nexus memgraph (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: memgraph
  source_file: backend/routes/routes_memgraph.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus memgraph

Memgraph Native Graph Engine — REST API Routes.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `memgraph` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/graph/initialize` |
| GET | `/workspaces/{ws_id}/graph/stats` |
| GET | `/workspaces/{ws_id}/graph/schema` |
| GET | `/workspaces/{ws_id}/graph/info` |
| POST | `/workspaces/{ws_id}/graph/nodes` |
| GET | `/workspaces/{ws_id}/graph/nodes/{node_id}` |
| PUT | `/workspaces/{ws_id}/graph/nodes/{node_id}` |
| DELETE | `/workspaces/{ws_id}/graph/nodes/{node_id}` |
| GET | `/workspaces/{ws_id}/graph/nodes` |
| POST | `/workspaces/{ws_id}/graph/nodes/merge` |
| GET | `/workspaces/{ws_id}/graph/nodes/{node_id}/neighbors` |
| POST | `/workspaces/{ws_id}/graph/edges` |
| GET | `/workspaces/{ws_id}/graph/edges/{edge_id}` |
| PUT | `/workspaces/{ws_id}/graph/edges/{edge_id}` |
| DELETE | `/workspaces/{ws_id}/graph/edges/{edge_id}` |
| GET | `/workspaces/{ws_id}/graph/edges` |
| POST | `/workspaces/{ws_id}/graph/edges/merge` |
| POST | `/workspaces/{ws_id}/graph/query` |
| POST | `/workspaces/{ws_id}/graph/algorithms/{algorithm}` |
| GET | `/workspaces/{ws_id}/graph/algorithms` |
| POST | `/workspaces/{ws_id}/graph/indexes` |
| GET | `/workspaces/{ws_id}/graph/indexes` |
| DELETE | `/workspaces/{ws_id}/graph/indexes/{index_name}` |
| POST | `/workspaces/{ws_id}/graph/indexes/vector/search` |
| POST | `/workspaces/{ws_id}/graph/indexes/text/search` |
| POST | `/workspaces/{ws_id}/graph/indexes/point/search` |
| POST | `/workspaces/{ws_id}/graph/analyze` |
| POST | `/workspaces/{ws_id}/graph/constraints` |
| GET | `/workspaces/{ws_id}/graph/constraints` |
| DELETE | `/workspaces/{ws_id}/graph/constraints` |
| POST | `/workspaces/{ws_id}/graph/triggers` |
| GET | `/workspaces/{ws_id}/graph/triggers` |
| DELETE | `/workspaces/{ws_id}/graph/triggers/{trigger_name}` |
| POST | `/workspaces/{ws_id}/graph/streams` |
| GET | `/workspaces/{ws_id}/graph/streams` |
| POST | `/workspaces/{ws_id}/graph/streams/{stream_name}/start` |
| POST | `/workspaces/{ws_id}/graph/streams/{stream_name}/stop` |
| POST | `/workspaces/{ws_id}/graph/streams/{stream_name}/ingest` |
| DELETE | `/workspaces/{ws_id}/graph/streams/{stream_name}` |
| POST | `/workspaces/{ws_id}/graph/import` |
| POST | `/workspaces/{ws_id}/graph/export` |
| POST | `/workspaces/{ws_id}/graph/bulk/nodes` |
| POST | `/workspaces/{ws_id}/graph/bulk/edges` |
| POST | `/workspaces/{ws_id}/graph/procedures/{proc_name}` |
| GET | `/workspaces/{ws_id}/graph/procedures` |
| POST | `/workspaces/{ws_id}/graph/snapshots` |
| GET | `/workspaces/{ws_id}/graph/snapshots` |
| GET | `/workspaces/{ws_id}/graph/visualization` |
| POST | `/workspaces/{ws_id}/graph/clear` |

## Install

```sh
jarvis skill install nexus:memgraph
```

Source of truth: `backend/routes/routes_memgraph.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
