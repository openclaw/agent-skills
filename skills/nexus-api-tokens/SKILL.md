---
name: nexus-api-tokens
description: "Scoped API tokens — Stripe-style bearer tokens with scope grammar. Use when an OpenJarvis user wants to call Nexus api.tokens (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: api.tokens
  source_file: backend/routes/routes_api_tokens.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus api.tokens

Scoped API tokens — Stripe-style bearer tokens with scope grammar.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `api.tokens` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/api-tokens` |
| GET | `/api-tokens` |
| GET | `/api-tokens/{token_id}` |
| POST | `/api-tokens/{token_id}/rotate` |
| DELETE | `/api-tokens/{token_id}` |
| POST | `/users/me/tokens` |
| GET | `/users/me/tokens` |
| GET | `/users/me/tokens/{token_id}/usage` |
| POST | `/users/me/tokens/{token_id}/rotate` |
| DELETE | `/users/me/tokens/{token_id}` |

## Install

```sh
jarvis skill install nexus:api-tokens
```

Source of truth: `backend/routes/routes_api_tokens.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
