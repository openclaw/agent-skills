---
name: nexus-service-accounts
description: "Org-level Service Accounts surface (Agent A12, spec §8.8). Use when an OpenJarvis user wants to call Nexus service.accounts (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: service.accounts
  source_file: backend/routes/routes_service_accounts.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus service.accounts

Org-level Service Accounts surface (Agent A12, spec §8.8).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `service.accounts` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/orgs/{org_id}/service-accounts` |
| POST | `/orgs/{org_id}/service-accounts` |
| GET | `/orgs/{org_id}/service-accounts/{sa_id}/tokens` |
| POST | `/orgs/{org_id}/service-accounts/{sa_id}/tokens` |
| POST | `/orgs/{org_id}/service-accounts/{sa_id}/disable` |
| DELETE | `/orgs/{org_id}/tokens/{token_id}` |
| GET | `/orgs/{org_id}/tokens/audit` |

## Install

```sh
jarvis skill install nexus:service-accounts
```

Source of truth: `backend/routes/routes_service_accounts.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
