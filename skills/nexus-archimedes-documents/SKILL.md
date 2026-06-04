---
name: nexus-archimedes-documents
description: "Archimedes — rich document upload (Phase 1 ChatGPT-parity). Use when an OpenJarvis user wants to call Nexus archimedes.documents (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: archimedes.documents
  source_file: backend/routes/routes_archimedes_documents.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus archimedes.documents

Archimedes — rich document upload (Phase 1 ChatGPT-parity).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `archimedes.documents` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/archimedes/documents/extractors` |
| POST | `/archimedes/documents/upload` |

## Install

```sh
jarvis skill install nexus:archimedes-documents
```

Source of truth: `backend/routes/routes_archimedes_documents.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
