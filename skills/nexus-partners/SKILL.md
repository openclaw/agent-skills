---
name: nexus-partners
description: "Partner onboarding + portal routes (Pod E segment 4.C.2). Use when an OpenJarvis user wants to call Nexus partners (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: partners
  source_file: backend/routes/routes_partners.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus partners

Partner onboarding + portal routes (Pod E segment 4.C.2).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `partners` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/partners/connect/start` |
| POST | `/partners/connect/return` |
| GET | `/partners/me` |
| GET | `/partners/me/earnings` |
| GET | `/partners/me/payouts` |
| POST | `/partners/me/tax-form` |
| GET | `/partners/me/tax-form` |
| GET | `/admin/partners` |
| POST | `/admin/partners/payouts/run` |
| POST | `/admin/partners/{partner_id}/tax-form/decision` |
| GET | `/admin/partners/{partner_id}/payouts` |

## Install

```sh
jarvis skill install nexus:partners
```

Source of truth: `backend/routes/routes_partners.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
