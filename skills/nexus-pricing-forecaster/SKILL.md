---
name: nexus-pricing-forecaster
description: "Pricing forecaster routes — read-only burn-rate projections. Use when an OpenJarvis user wants to call Nexus pricing.forecaster (GET) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: pricing.forecaster
  source_file: backend/routes/routes_pricing_forecaster.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus pricing.forecaster

Pricing forecaster routes — read-only burn-rate projections.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `pricing.forecaster` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/v1/orgs/{org_id}/pricing-forecast` |
| GET | `/v1/workspaces/{ws_id}/pricing-forecast` |

## Install

```sh
jarvis skill install nexus:pricing-forecaster
```

Source of truth: `backend/routes/routes_pricing_forecaster.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
