---
name: nexus-content-gen
description: "Content Generation Suite — AI docs, slides, sheets with export and templates. Use when an OpenJarvis user wants to call Nexus content.gen (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: content.gen
  source_file: backend/routes/routes_content_gen.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus content.gen

Content Generation Suite — AI docs, slides, sheets with export and templates

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `content.gen` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/content/documents/create` |
| POST | `/content/documents/{content_id}/edit` |
| GET | `/content/documents/{content_id}` |
| GET | `/content/documents` |
| DELETE | `/content/documents/{content_id}` |
| POST | `/content/documents/{content_id}/export` |
| POST | `/content/slides/create` |
| POST | `/content/sheets/create` |
| POST | `/content/from-chat` |
| GET | `/content/templates` |

## Install

```sh
jarvis skill install nexus:content-gen
```

Source of truth: `backend/routes/routes_content_gen.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
