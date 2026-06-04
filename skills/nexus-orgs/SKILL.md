---
name: nexus-orgs
description: "Organization / Multi-Tenant routes for Nexus platform. Use when an OpenJarvis user wants to call Nexus orgs (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: orgs
  source_file: backend/routes/routes_orgs.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus orgs

Organization / Multi-Tenant routes for Nexus platform

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `orgs` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/orgs/by-slug/{slug}` |
| POST | `/orgs/register` |
| POST | `/orgs/check-slug` |
| GET | `/orgs/my-orgs` |
| GET | `/orgs/{org_id}` |
| PUT | `/orgs/{org_id}` |
| GET | `/orgs/{org_id}/members` |
| POST | `/orgs/{org_id}/members` |
| PUT | `/orgs/{org_id}/members/{user_id}/role` |
| DELETE | `/orgs/{org_id}/members/{user_id}` |
| GET | `/orgs/{org_id}/workspaces` |
| POST | `/orgs/{org_id}/workspaces` |
| GET | `/orgs/{org_id}/admin/stats` |
| GET | `/orgs/{org_id}/admin/members` |
| GET | `/orgs/{org_id}/admin/activity` |
| GET | `/orgs/{org_id}/admin/analytics` |
| GET | `/orgs/{org_id}/billing` |
| GET | `/admin/organizations` |
| PUT | `/admin/organizations/{org_id}/plan` |
| PUT | `/admin/organizations/{org_id}/nexus-ai` |
| PUT | `/orgs/{org_id}/custom-domain` |
| GET | `/orgs/{org_id}/login-config` |
| GET | `/orgs/{org_id}/projects` |
| GET | `/orgs/{org_id}/tasks` |
| GET | `/orgs/{org_id}/workflows` |
| GET | `/orgs/{org_id}/analytics/summary` |
| GET | `/orgs/{org_id}/admin/audit-log` |
| GET | `/orgs/{org_id}/admin/audit-log/actions` |
| GET | `/orgs/{org_id}/admin/budget-audit` |
| GET | `/orgs/{org_id}/admin/export/csv` |
| GET | `/orgs/{org_id}/admin/member-activity` |
| POST | `/orgs/{org_id}/knowledge-graph/consent` |
| GET | `/orgs/{org_id}/knowledge-graph/consent` |

## Install

```sh
jarvis skill install nexus:orgs
```

Source of truth: `backend/routes/routes_orgs.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
