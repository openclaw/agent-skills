---
name: nexus-integrations
description: "External Integration Stubs — Email, Microsoft/Meta OAuth, PayPal. Use when an OpenJarvis user wants to call Nexus integrations (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: integrations
  source_file: backend/routes/routes_integrations.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus integrations

External Integration Stubs — Email, Microsoft/Meta OAuth, PayPal

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `integrations` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/integrations/email/status` |
| GET | `/integrations/microsoft/status` |
| POST | `/auth/microsoft` |
| GET | `/integrations/meta/status` |
| POST | `/auth/meta` |
| GET | `/auth/microsoft/callback` |
| GET | `/auth/meta/callback` |
| GET | `/integrations/paypal/status` |
| POST | `/billing/paypal/create-order` |
| GET | `/integrations/status` |

## Install

```sh
jarvis skill install nexus:integrations
```

Source of truth: `backend/routes/routes_integrations.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
