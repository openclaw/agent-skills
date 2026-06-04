---
name: nexus-rag
description: "RAG Pipeline API — Document ingestion, hybrid search, and configuration. Use when an OpenJarvis user wants to call Nexus rag (DELETE, GET, PATCH, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: rag
  source_file: backend/routes/routes_rag.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus rag

RAG Pipeline API — Document ingestion, hybrid search, and configuration.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `rag` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/rag/ingest` |
| GET | `/workspaces/{ws_id}/rag/documents` |
| PATCH | `/workspaces/{ws_id}/rag/documents/{doc_id}` |
| POST | `/workspaces/{ws_id}/rag/ingest_url` |
| DELETE | `/workspaces/{ws_id}/rag/documents/{doc_id}` |
| POST | `/workspaces/{ws_id}/rag/search` |
| GET | `/workspaces/{ws_id}/rag/config` |
| PUT | `/workspaces/{ws_id}/rag/config` |

## Install

```sh
jarvis skill install nexus:rag
```

Source of truth: `backend/routes/routes_rag.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
