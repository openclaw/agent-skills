---
name: nexus-sso
description: "SSO Routes — SAML 2.0 SP and OIDC authorization code flow for enterprise SSO. Use when an OpenJarvis user wants to call Nexus sso (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: sso
  source_file: backend/routes/routes_sso.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus sso

SSO Routes — SAML 2.0 SP and OIDC authorization code flow for enterprise SSO.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `sso` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/admin/sso/config` |
| GET | `/admin/sso/configs` |
| PUT | `/admin/sso/config/{config_id}` |
| DELETE | `/admin/sso/config/{config_id}` |
| GET | `/sso/saml/metadata/{config_id}` |
| GET | `/sso/saml/login/{config_id}` |
| POST | `/sso/saml/acs/{config_id}` |
| GET | `/sso/oidc/login/{config_id}` |
| GET | `/sso/oidc/callback/{config_id}` |
| GET | `/sso/providers` |

## Install

```sh
jarvis skill install nexus:sso
```

Source of truth: `backend/routes/routes_sso.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
