---
name: nexus-contracts
description: "Contracts routes — CRUD + e-sign for org-level legal docs. Use when an OpenJarvis user wants to call Nexus contracts (GET, PATCH, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: contracts
  source_file: backend/routes/routes_contracts.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus contracts

Contracts routes — CRUD + e-sign for org-level legal docs.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `contracts` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/v1/orgs/{org_id}/contracts` |
| POST | `/v1/orgs/{org_id}/contracts` |
| GET | `/v1/orgs/{org_id}/contracts/{contract_id}` |
| PATCH | `/v1/orgs/{org_id}/contracts/{contract_id}` |
| POST | `/v1/orgs/{org_id}/contracts/{contract_id}/transition` |
| POST | `/v1/orgs/{org_id}/contracts/{contract_id}/send-for-signature` |
| POST | `/v1/orgs/{org_id}/contracts/{contract_id}/record-signature` |
| GET | `/v1/orgs/{org_id}/contracts/{contract_id}/renewals` |
| GET | `/v1/orgs/{org_id}/contracts-meta` |

## Install

```sh
jarvis skill install nexus:contracts
```

Source of truth: `backend/routes/routes_contracts.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
