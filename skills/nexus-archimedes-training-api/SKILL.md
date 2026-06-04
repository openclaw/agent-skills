---
name: nexus-archimedes-training-api
description: "External Training Pipeline API — API-key-authenticated endpoints that let. Use when an OpenJarvis user wants to call Nexus archimedes.training.api (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: archimedes.training.api
  source_file: backend/routes/routes_archimedes_training_api.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus archimedes.training.api

External Training Pipeline API — API-key-authenticated endpoints that let

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `archimedes.training.api` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/external-training/keys` |
| GET | `/external-training/keys` |
| DELETE | `/external-training/keys/{key_id}` |
| POST | `/external-training/ingest` |
| POST | `/external-training/ingest/batch` |
| GET | `/external-training/activity` |
| GET | `/external-training/stats` |

## Install

```sh
jarvis skill install nexus:archimedes-training-api
```

Source of truth: `backend/routes/routes_archimedes_training_api.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
