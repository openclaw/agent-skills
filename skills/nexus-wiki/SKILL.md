---
name: nexus-wiki
description: "Wiki/Docs Module — uses JSONB adapter for backward compatibility. Use when an OpenJarvis user wants to call Nexus wiki (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: wiki
  source_file: backend/routes/routes_wiki.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus wiki

Wiki/Docs Module — uses JSONB adapter for backward compatibility.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `wiki` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/wiki` |
| POST | `/workspaces/{workspace_id}/wiki` |
| GET | `/workspaces/{workspace_id}/wiki/{page_id}` |
| PUT | `/workspaces/{workspace_id}/wiki/{page_id}` |
| DELETE | `/workspaces/{workspace_id}/wiki/{page_id}` |
| GET | `/workspaces/{workspace_id}/wiki/{page_id}/history` |
| GET | `/workspaces/{workspace_id}/wiki/{page_id}/version/{version}` |
| POST | `/workspaces/{workspace_id}/wiki/{page_id}/restore/{version}` |
| POST | `/workspaces/{workspace_id}/wiki/ai-update` |
| GET | `/wiki-templates` |
| POST | `/workspaces/{workspace_id}/wiki/from-template` |
| GET | `/workspaces/{workspace_id}/search` |
| GET | `/workspaces/{workspace_id}/activities` |
| GET | `/workspaces/{workspace_id}/activities/export` |

## Install

```sh
jarvis skill install nexus:wiki
```

Source of truth: `backend/routes/routes_wiki.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
