---
name: nexus-sovereign
description: "HTTP surface for the Sovereign AI bundle — Pod I segment 8.A.3. Use when an OpenJarvis user wants to call Nexus sovereign (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: sovereign
  source_file: backend/routes/routes_sovereign.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus sovereign

HTTP surface for the Sovereign AI bundle — Pod I segment 8.A.3.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `sovereign` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/admin/sovereign/profiles` |
| GET | `/admin/sovereign/active` |
| POST | `/admin/sovereign/apply/{profile_name}` |
| POST | `/admin/sovereign/validate/{profile_name}` |

## Install

```sh
jarvis skill install nexus:sovereign
```

Source of truth: `backend/routes/routes_sovereign.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
