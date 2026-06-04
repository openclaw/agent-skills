---
name: nexus-transparency
description: "Per-tenant usage transparency dashboard — Pod D segment 3.C.1. Use when an OpenJarvis user wants to call Nexus transparency (GET) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: transparency
  source_file: backend/routes/routes_transparency.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus transparency

Per-tenant usage transparency dashboard — Pod D segment 3.C.1.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `transparency` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/transparency/summary` |
| GET | `/transparency/recent-completions` |
| GET | `/transparency/by-provider` |

## Install

```sh
jarvis skill install nexus:transparency
```

Source of truth: `backend/routes/routes_transparency.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
