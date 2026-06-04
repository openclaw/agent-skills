---
name: nexus-archimedes-personas
description: "Archimedes custom-persona routes. Use when an OpenJarvis user wants to call Nexus archimedes.personas (DELETE, GET, PATCH, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: archimedes.personas
  source_file: backend/routes/routes_archimedes_personas.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus archimedes.personas

Archimedes custom-persona routes.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `archimedes.personas` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/archimedes/personas` |
| GET | `/archimedes/personas` |
| GET | `/archimedes/personas/{persona_id}` |
| PATCH | `/archimedes/personas/{persona_id}` |
| DELETE | `/archimedes/personas/{persona_id}` |

## Install

```sh
jarvis skill install nexus:archimedes-personas
```

Source of truth: `backend/routes/routes_archimedes_personas.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
