---
name: nexus-knowledge-graph
description: "Knowledge Graph API — Browse, search, correct, and manage institutional knowledge. Use when an OpenJarvis user wants to call Nexus knowledge.graph (GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: knowledge.graph
  source_file: backend/routes/routes_knowledge_graph.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus knowledge.graph

Knowledge Graph API — Browse, search, correct, and manage institutional knowledge.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `knowledge.graph` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/knowledge` |
| GET | `/workspaces/{ws_id}/knowledge/graph` |
| GET | `/workspaces/{ws_id}/knowledge/{entity_id}` |
| POST | `/workspaces/{ws_id}/knowledge/{entity_id}/feedback` |
| POST | `/workspaces/{ws_id}/knowledge/edges` |
| POST | `/workspaces/{ws_id}/knowledge/{entity_id}/supersede` |
| GET | `/workspaces/{ws_id}/knowledge/{entity_id}/neighborhood` |
| PUT | `/workspaces/{ws_id}/knowledge-graph/settings` |
| GET | `/workspaces/{ws_id}/knowledge-graph/consent-summary` |
| GET | `/workspaces/{ws_id}/knowledge-graph/snapshot` |
| GET | `/workspaces/{ws_id}/knowledge-graph/timeline` |
| GET | `/workspaces/{ws_id}/knowledge-graph/ontology` |
| PUT | `/workspaces/{ws_id}/knowledge-graph/ontology` |
| GET | `/workspaces/{ws_id}/knowledge-graph/ontology/suggestions` |

## Install

```sh
jarvis skill install nexus:knowledge-graph
```

Source of truth: `backend/routes/routes_knowledge_graph.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
