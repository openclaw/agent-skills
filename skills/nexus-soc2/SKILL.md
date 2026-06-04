---
name: nexus-soc2
description: "SOC 2 Compliance — Audit trail endpoints and documentation. Use when an OpenJarvis user wants to call Nexus soc2 (GET) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: soc2
  source_file: backend/routes/routes_soc2.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus soc2

SOC 2 Compliance — Audit trail endpoints and documentation.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `soc2` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/compliance/audit-trail` |
| GET | `/compliance/audit-trail/export` |
| GET | `/compliance/soc2-summary` |
| GET | `/compliance/data-map` |

## Install

```sh
jarvis skill install nexus:soc2
```

Source of truth: `backend/routes/routes_soc2.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
