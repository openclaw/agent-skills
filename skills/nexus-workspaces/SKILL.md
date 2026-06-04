---
name: nexus-workspaces
description: "Extracted from server.py — auto-generated module. Use when an OpenJarvis user wants to call Nexus workspaces (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: workspaces
  source_file: backend/routes/routes_workspaces.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus workspaces

Extracted from server.py — auto-generated module.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `workspaces` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces` |
| POST | `/workspaces` |
| GET | `/workspaces/{workspace_id}` |
| GET | `/workspaces/{workspace_id}/ai-key-health` |
| PUT | `/workspaces/{workspace_id}` |
| PUT | `/workspaces/{workspace_id}/disable` |
| PUT | `/workspaces/{workspace_id}/pin` |
| DELETE | `/workspaces/{workspace_id}/pin` |
| GET | `/ai-models` |
| GET | `/workspaces/{workspace_id}/settings` |
| PUT | `/workspaces/{workspace_id}/settings` |
| GET | `/workspaces/{workspace_id}/tpm` |
| PUT | `/workspaces/{workspace_id}/tpm` |

## Install

```sh
jarvis skill install nexus:workspaces
```

Source of truth: `backend/routes/routes_workspaces.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
