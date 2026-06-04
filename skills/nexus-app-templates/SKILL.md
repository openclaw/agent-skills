---
name: nexus-app-templates
description: "App template marketplace — publishable starter apps for Nexus Build. Use when an OpenJarvis user wants to call Nexus app.templates (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: app.templates
  source_file: backend/routes/routes_app_templates.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus app.templates

App template marketplace — publishable starter apps for Nexus Build.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `app.templates` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/build/templates` |
| POST | `/workspaces/{ws_id}/build/templates` |
| POST | `/workspaces/{ws_id}/build/templates/install` |

## Install

```sh
jarvis skill install nexus:app-templates
```

Source of truth: `backend/routes/routes_app_templates.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
