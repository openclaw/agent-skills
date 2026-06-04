---
name: nexus-managed-keys
description: "Routes for Nexus Managed Keys — platform-provided AI keys with credit billing. Use when an OpenJarvis user wants to call Nexus managed.keys (GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: managed.keys
  source_file: backend/routes/routes_managed_keys.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus managed.keys

Routes for Nexus Managed Keys — platform-provided AI keys with credit billing.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `managed.keys` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/admin/managed-keys` |
| GET | `/admin/managed-keys` |
| GET | `/admin/managed-keys/budgets` |
| PUT | `/admin/managed-keys/budgets` |
| GET | `/admin/managed-keys/dashboard` |
| GET | `/admin/managed-keys/alerts` |
| GET | `/admin/managed-keys/health` |
| GET | `/orgs/{org_id}/nexus-ai/budgets` |
| PUT | `/orgs/{org_id}/nexus-ai/budgets` |
| GET | `/orgs/{org_id}/nexus-ai/dashboard` |
| GET | `/orgs/{org_id}/nexus-ai/alerts` |
| GET | `/workspaces/{workspace_id}/nexus-ai/budgets` |
| PUT | `/workspaces/{workspace_id}/nexus-ai/budgets` |
| GET | `/workspaces/{workspace_id}/nexus-ai/dashboard` |
| GET | `/workspaces/{workspace_id}/nexus-ai/alerts` |
| GET | `/admin/managed-keys/alerts/history` |
| PUT | `/admin/managed-keys/alerts/{alert_key}/dismiss` |
| POST | `/settings/managed-keys/toggle` |
| GET | `/settings/managed-keys` |
| GET | `/settings/managed-keys/credits` |
| GET | `/settings/managed-keys/usage` |

## Install

```sh
jarvis skill install nexus:managed-keys
```

Source of truth: `backend/routes/routes_managed_keys.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
