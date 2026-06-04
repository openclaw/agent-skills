---
name: nexus-marketplace-payouts
description: "Marketplace payout HTTP surface (Pod E 4.C.2). Use when an OpenJarvis user wants to call Nexus marketplace.payouts (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: marketplace.payouts
  source_file: backend/routes/routes_marketplace_payouts.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus marketplace.payouts

Marketplace payout HTTP surface (Pod E 4.C.2).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `marketplace.payouts` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/marketplace/payouts/partners/onboard` |
| GET | `/marketplace/payouts/partners/me/balance` |
| GET | `/marketplace/payouts/partners/me/payouts` |
| POST | `/marketplace/payouts/admin/batches/{period}/prepare` |
| POST | `/marketplace/payouts/admin/batches/{period}/execute` |
| POST | `/marketplace/payouts/partners/me/tax-form` |

## Install

```sh
jarvis skill install nexus:marketplace-payouts
```

Source of truth: `backend/routes/routes_marketplace_payouts.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
