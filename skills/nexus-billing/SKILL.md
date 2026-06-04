---
name: nexus-billing
description: "Billing Routes — Direct Stripe SDK for checkout, status, and webhooks. Use when an OpenJarvis user wants to call Nexus billing (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: billing
  source_file: backend/routes/routes_billing.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus billing

Billing Routes — Direct Stripe SDK for checkout, status, and webhooks.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `billing` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/billing/plans` |
| GET | `/billing/my-plan` |
| GET | `/billing/subscription` |
| POST | `/billing/checkout` |
| GET | `/billing/checkout/status/{session_id}` |
| POST | `/webhook/stripe` |
| GET | `/billing/transactions` |

## Install

```sh
jarvis skill install nexus:billing
```

Source of truth: `backend/routes/routes_billing.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
