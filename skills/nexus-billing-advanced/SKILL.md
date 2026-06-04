---
name: nexus-billing-advanced
description: "Advanced Billing — Invoices, Statements, Account Management, Org Billing, Payment History. Use when an OpenJarvis user wants to call Nexus billing.advanced (GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: billing.advanced
  source_file: backend/routes/routes_billing_advanced.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus billing.advanced

Advanced Billing — Invoices, Statements, Account Management, Org Billing, Payment History

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `billing.advanced` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/billing/account` |
| PUT | `/billing/account/address` |
| GET | `/billing/invoices` |
| POST | `/billing/invoices/generate` |
| GET | `/billing/invoices/{invoice_id}` |
| GET | `/billing/invoices/{invoice_id}/export` |
| GET | `/billing/payments` |
| GET | `/billing/payments/{payment_id}/receipt` |
| GET | `/orgs/{org_id}/billing/account` |
| PUT | `/orgs/{org_id}/billing/address` |
| PUT | `/orgs/{org_id}/billing/spending-limit` |
| POST | `/orgs/{org_id}/billing/contacts` |
| GET | `/orgs/{org_id}/billing/cost-allocation` |
| GET | `/orgs/{org_id}/billing/invoices` |
| GET | `/billing/plan-history` |
| POST | `/billing/change-plan` |
| GET | `/billing/notifications` |
| GET | `/billing/usage-summary` |

## Install

```sh
jarvis skill install nexus:billing-advanced
```

Source of truth: `backend/routes/routes_billing_advanced.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
