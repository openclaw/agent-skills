---
name: nexus-permission-audit
description: "Permission audit-trail + retention routes (Agent A08). Use when an OpenJarvis user wants to call Nexus permission.audit (GET, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: permission.audit
  source_file: backend/routes/routes_permission_audit.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus permission.audit

Permission audit-trail + retention routes (Agent A08).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `permission.audit` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/admin/audit-trail/permissions` |
| GET | `/orgs/{org_id}/audit-retention` |
| PUT | `/orgs/{org_id}/audit-retention` |

## Install

```sh
jarvis skill install nexus:permission-audit
```

Source of truth: `backend/routes/routes_permission_audit.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
