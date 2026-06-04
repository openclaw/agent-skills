---
name: nexus-user-prefs
description: "User preferences, language, theme hierarchy, and desktop download routes — extracted from server.py (N7-019). Use when an OpenJarvis user wants to call Nexus user.prefs (GET, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: user.prefs
  source_file: backend/routes/routes_user_prefs.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus user.prefs

User preferences, language, theme hierarchy, and desktop download routes — extracted from server.py (N7-019).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `user.prefs` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| PUT | `/user/language` |
| PUT | `/user/preferences` |
| GET | `/user/preferences` |
| GET | `/settings/resolved-theme` |
| GET | `/admin/platform-theme` |
| PUT | `/admin/platform-theme` |
| GET | `/orgs/{org_id}/theme` |
| PUT | `/orgs/{org_id}/theme` |
| GET | `/download/desktop/{arch}` |

## Install

```sh
jarvis skill install nexus:user-prefs
```

Source of truth: `backend/routes/routes_user_prefs.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
