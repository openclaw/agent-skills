---
name: nexus-workspace-templates
description: "Workspace Templates — Pre-built workspace configurations that users can clone. Use when an OpenJarvis user wants to call Nexus workspace.templates (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: workspace.templates
  source_file: backend/routes/routes_workspace_templates.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus workspace.templates

Workspace Templates — Pre-built workspace configurations that users can clone.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `workspace.templates` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspace-templates/marketplace` |
| POST | `/workspace-templates/marketplace/{template_id}/clone` |
| POST | `/workspace-templates/marketplace/publish` |

## Install

```sh
jarvis skill install nexus:workspace-templates
```

Source of truth: `backend/routes/routes_workspace_templates.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
