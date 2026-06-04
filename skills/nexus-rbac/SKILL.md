---
name: nexus-rbac
description: "RBAC (Role-Based Access Control) system for Nexus workspaces. Use when an OpenJarvis user wants to call Nexus rbac (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: rbac
  source_file: backend/routes/routes_rbac.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus rbac

RBAC (Role-Based Access Control) system for Nexus workspaces

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `rbac` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/members` |
| POST | `/workspaces/{workspace_id}/members/invite` |
| POST | `/workspaces/{workspace_id}/invite-link` |
| POST | `/invites/{link_code}/join` |
| GET | `/invites/{link_code}` |
| PUT | `/workspaces/{workspace_id}/members/{member_user_id}/role` |
| DELETE | `/workspaces/{workspace_id}/members/{member_user_id}` |
| POST | `/workspaces/{workspace_id}/leave` |
| GET | `/workspaces/{workspace_id}/my-role` |
| GET | `/workspaces/{workspace_id}/my-custom-roles` |

## Install

```sh
jarvis skill install nexus:rbac
```

Source of truth: `backend/routes/routes_rbac.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
