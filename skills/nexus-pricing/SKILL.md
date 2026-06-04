---
name: nexus-pricing
description: "Pricing Engine — Credits-based billing, overage calculations, free tier management, usage tracking. Use when an OpenJarvis user wants to call Nexus pricing (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: pricing
  source_file: backend/routes/routes_pricing.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus pricing

Pricing Engine — Credits-based billing, overage calculations, free tier management, usage tracking

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `pricing` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/billing/credits` |
| GET | `/billing/credits/history` |
| GET | `/billing/credit-costs` |
| GET | `/billing/credits/transactions` |
| GET | `/billing/free-tier/status` |
| POST | `/billing/check-limit` |
| GET | `/billing/overage-estimate` |
| GET | `/billing/plans-v2` |
| POST | `/billing/check-feature` |

## Install

```sh
jarvis skill install nexus:pricing
```

Source of truth: `backend/routes/routes_pricing.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
