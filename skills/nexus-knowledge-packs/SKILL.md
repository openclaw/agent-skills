---
name: nexus-knowledge-packs
description: "Export/Import Agent Knowledge Packs — Download and upload agent knowledge as JSON. Use when an OpenJarvis user wants to call Nexus knowledge.packs (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: knowledge.packs
  source_file: backend/routes/routes_knowledge_packs.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus knowledge.packs

Export/Import Agent Knowledge Packs — Download and upload agent knowledge as JSON.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `knowledge.packs` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/knowledge/export` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/knowledge/import` |

## Install

```sh
jarvis skill install nexus:knowledge-packs
```

Source of truth: `backend/routes/routes_knowledge_packs.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
