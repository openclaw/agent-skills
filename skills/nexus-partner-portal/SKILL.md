---
name: nexus-partner-portal
description: "Partner portal — deal registration, quoting, commissions, resources. Use when an OpenJarvis user wants to call Nexus partner.portal (GET, PATCH, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: partner.portal
  source_file: backend/routes/routes_partner_portal.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus partner.portal

Partner portal — deal registration, quoting, commissions, resources.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `partner.portal` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/v1/partner-portal/deals` |
| POST | `/v1/partner-portal/deals` |
| GET | `/v1/partner-portal/deals/{deal_id}` |
| PATCH | `/v1/partner-portal/deals/{deal_id}` |
| GET | `/v1/partner-portal/quotes` |
| POST | `/v1/partner-portal/quotes` |
| POST | `/v1/partner-portal/quotes/{quote_id}/status` |
| GET | `/v1/partner-portal/commissions/summary` |
| GET | `/v1/partner-portal/resources` |

## Install

```sh
jarvis skill install nexus:partner-portal
```

Source of truth: `backend/routes/routes_partner_portal.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
