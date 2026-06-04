---
name: nexus-revenue-sharing
description: "Agent Marketplace Revenue Sharing — Stripe-based payments for agent marketplace. Use when an OpenJarvis user wants to call Nexus revenue.sharing (GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: revenue.sharing
  source_file: backend/routes/routes_revenue_sharing.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus revenue.sharing

Agent Marketplace Revenue Sharing — Stripe-based payments for agent marketplace.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `revenue.sharing` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| PUT | `/marketplace/agents/{agent_id}/pricing` |
| GET | `/marketplace/agents/{agent_id}/pricing` |
| POST | `/marketplace/agents/{agent_id}/purchase` |
| GET | `/marketplace/purchase/status/{session_id}` |
| POST | `/webhook/stripe-marketplace` |
| GET | `/marketplace/revenue/dashboard` |
| GET | `/marketplace/agents/{agent_id}/revenue` |

## Install

```sh
jarvis skill install nexus:revenue-sharing
```

Source of truth: `backend/routes/routes_revenue_sharing.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
