---
name: nexus-qbr
description: "QBR auto-report routes — quarterly summary + PDF endpoint. Use when an OpenJarvis user wants to call Nexus qbr (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: qbr
  source_file: backend/routes/routes_qbr.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus qbr

QBR auto-report routes — quarterly summary + PDF endpoint.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `qbr` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/v1/orgs/{org_id}/qbr/{quarter}` |
| GET | `/v1/orgs/{org_id}/qbr/{quarter}/pdf` |
| POST | `/v1/orgs/{org_id}/qbr/{quarter}/regenerate-narrative` |

## Install

```sh
jarvis skill install nexus:qbr
```

Source of truth: `backend/routes/routes_qbr.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
