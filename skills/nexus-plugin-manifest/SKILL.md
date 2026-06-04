---
name: nexus-plugin-manifest
description: "Plugin Manifest installer routes. Use when an OpenJarvis user wants to call Nexus plugin.manifest (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: plugin.manifest
  source_file: backend/routes/routes_plugin_manifest.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus plugin.manifest

Plugin Manifest installer routes.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `plugin.manifest` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/plugins/install` |
| POST | `/workspaces/{workspace_id}/plugins/install-from-url` |
| POST | `/workspaces/{workspace_id}/plugins/validate` |
| GET | `/workspaces/{workspace_id}/plugins` |
| DELETE | `/workspaces/{workspace_id}/plugins/{plugin_id}` |
| GET | `/plugin-catalog` |
| GET | `/plugin-catalog/{plugin_id}` |
| POST | `/workspaces/{workspace_id}/plugins/install-from-catalog` |

## Install

```sh
jarvis skill install nexus:plugin-manifest
```

Source of truth: `backend/routes/routes_plugin_manifest.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
