---
name: nexus-archimedes-debate
description: "SSE route for the multi-agent debate primitive. Use when an OpenJarvis user wants to call Nexus archimedes.debate (POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: archimedes.debate
  source_file: backend/routes/routes_archimedes_debate.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus archimedes.debate

SSE route for the multi-agent debate primitive.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `archimedes.debate` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/archimedes/debate/stream` |

## Install

```sh
jarvis skill install nexus:archimedes-debate
```

Source of truth: `backend/routes/routes_archimedes_debate.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
