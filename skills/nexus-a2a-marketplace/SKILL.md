---
name: nexus-a2a-marketplace
description: "A2A Autonomous Workflow Marketplace — publish, sell, share, install. Use when an OpenJarvis user wants to call Nexus a2a.marketplace (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: a2a.marketplace
  source_file: backend/routes/routes_a2a_marketplace.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus a2a.marketplace

A2A Autonomous Workflow Marketplace — publish, sell, share, install.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `a2a.marketplace` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/marketplace/a2a` |
| GET | `/marketplace/a2a/featured` |
| GET | `/marketplace/a2a/org/{org_id}` |
| GET | `/marketplace/a2a/my-listings` |
| GET | `/marketplace/a2a/my-purchases` |
| GET | `/marketplace/a2a/my-analytics` |
| GET | `/marketplace/a2a/notifications` |
| POST | `/marketplace/a2a/notifications/{notification_id}/read` |
| GET | `/marketplace/a2a/bundles` |
| GET | `/marketplace/a2a/promo-codes` |
| GET | `/marketplace/a2a/{marketplace_id}` |
| POST | `/marketplace/a2a/publish` |
| PUT | `/marketplace/a2a/{marketplace_id}` |
| DELETE | `/marketplace/a2a/{marketplace_id}` |
| POST | `/marketplace/a2a/{marketplace_id}/purchase` |
| POST | `/marketplace/a2a/{marketplace_id}/subscribe` |
| GET | `/marketplace/a2a/purchase/status/{session_id}` |
| POST | `/marketplace/a2a/{marketplace_id}/refund` |
| POST | `/marketplace/a2a/{marketplace_id}/install` |
| POST | `/marketplace/a2a/{marketplace_id}/dry-run` |
| POST | `/marketplace/a2a/{marketplace_id}/install/resolve-agents` |
| POST | `/marketplace/a2a/{marketplace_id}/rate` |
| POST | `/marketplace/a2a/{marketplace_id}/report` |
| POST | `/marketplace/a2a/bundles` |
| POST | `/marketplace/a2a/bundles/{bundle_id}/purchase` |
| POST | `/marketplace/a2a/promo-codes` |
| DELETE | `/marketplace/a2a/promo-codes/{code_id}` |
| GET | `/marketplace/a2a/{marketplace_id}/export` |
| POST | `/marketplace/a2a/import` |
| POST | `/marketplace/a2a/admin/{marketplace_id}/feature` |
| POST | `/marketplace/a2a/admin/{marketplace_id}/verify` |
| GET | `/marketplace/a2a/admin/reports` |
| POST | `/marketplace/a2a/admin/reports/{report_id}/resolve` |

## Install

```sh
jarvis skill install nexus:a2a-marketplace
```

Source of truth: `backend/routes/routes_a2a_marketplace.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
