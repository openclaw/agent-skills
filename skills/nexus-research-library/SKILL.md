---
name: nexus-research-library
description: "Research Library Routes — CRUD, ingestion, chat, compare, lit-review, search, annotations, connectors. Use when an OpenJarvis user wants to call Nexus research.library (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: research.library
  source_file: backend/routes/routes_research_library.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus research.library

Research Library Routes — CRUD, ingestion, chat, compare, lit-review, search, annotations, connectors.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `research.library` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/research-libraries` |
| GET | `/workspaces/{ws_id}/research-libraries` |
| GET | `/research-libraries/{lib_id}` |
| DELETE | `/research-libraries/{lib_id}` |
| POST | `/research-libraries/{lib_id}/documents` |
| GET | `/research-libraries/{lib_id}/documents` |
| GET | `/research-documents/{doc_id}` |
| GET | `/research-documents/{doc_id}/chunks` |
| DELETE | `/research-documents/{doc_id}` |
| POST | `/research-libraries/{lib_id}/chat` |
| POST | `/research-libraries/{lib_id}/search` |
| POST | `/research-libraries/{lib_id}/compare` |
| POST | `/research-libraries/{lib_id}/lit-review` |
| GET | `/research-libraries/{lib_id}/graph` |
| POST | `/research-documents/{doc_id}/annotations` |
| GET | `/research-documents/{doc_id}/annotations` |
| DELETE | `/annotations/{ann_id}` |
| POST | `/connectors/zotero/sync` |

## Install

```sh
jarvis skill install nexus:research-library
```

Source of truth: `backend/routes/routes_research_library.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
