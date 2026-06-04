---
name: nexus-org-branding
description: "Per-organization white-label branding routes. Use when an OpenJarvis user wants to call Nexus org.branding (GET, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: org.branding
  source_file: backend/routes/routes_org_branding.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus org.branding

Per-organization white-label branding routes.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `org.branding` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/orgs/{org_id}/branding` |
| PUT | `/orgs/{org_id}/branding` |

## Install

```sh
jarvis skill install nexus:org-branding
```

Source of truth: `backend/routes/routes_org_branding.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
