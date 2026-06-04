---
name: nexus-ai-keys
description: "API key management routes - account-level and workspace-level. Use when an OpenJarvis user wants to call Nexus ai.keys (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: ai.keys
  source_file: backend/routes/routes_ai_keys.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus ai.keys

API key management routes - account-level and workspace-level

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `ai.keys` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/settings/ai-keys` |
| POST | `/settings/ai-keys` |
| DELETE | `/settings/ai-keys/{agent}` |
| POST | `/settings/ai-keys/test` |
| POST | `/settings/ai-keys/test-all` |
| POST | `/workspaces/{workspace_id}/ai-config` |
| GET | `/workspaces/{workspace_id}/ai-config` |
| GET | `/settings/ai-keys/health` |

## Install

```sh
jarvis skill install nexus:ai-keys
```

Source of truth: `backend/routes/routes_ai_keys.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
