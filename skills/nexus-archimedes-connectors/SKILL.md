---
name: nexus-archimedes-connectors
description: "HTTP surface for Archimedes external connectors. Use when an OpenJarvis user wants to call Nexus archimedes.connectors (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: archimedes.connectors
  source_file: backend/routes/routes_archimedes_connectors.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus archimedes.connectors

HTTP surface for Archimedes external connectors.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `archimedes.connectors` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/archimedes/connectors` |
| GET | `/archimedes/connectors/{name}/oauth/start` |
| GET | `/archimedes/connectors/{name}/oauth/callback` |
| POST | `/archimedes/connectors/{name}/disconnect` |

## Install

```sh
jarvis skill install nexus:archimedes-connectors
```

Source of truth: `backend/routes/routes_archimedes_connectors.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
