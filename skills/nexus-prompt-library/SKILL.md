---
name: nexus-prompt-library
description: "Prompt Management & Versioning — Create, version, test, and analyze reusable prompts. Use when an OpenJarvis user wants to call Nexus prompt.library (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: prompt.library
  source_file: backend/routes/routes_prompt_library.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus prompt.library

Prompt Management & Versioning — Create, version, test, and analyze reusable prompts.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `prompt.library` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/prompts` |
| POST | `/workspaces/{ws_id}/prompts` |
| GET | `/workspaces/{ws_id}/prompts/{prompt_id}` |
| PUT | `/workspaces/{ws_id}/prompts/{prompt_id}` |
| DELETE | `/workspaces/{ws_id}/prompts/{prompt_id}` |
| POST | `/workspaces/{ws_id}/prompts/{prompt_id}/duplicate` |
| GET | `/workspaces/{ws_id}/prompts/{prompt_id}/versions` |
| POST | `/workspaces/{ws_id}/prompts/{prompt_id}/rollback/{version}` |
| POST | `/workspaces/{ws_id}/prompts/{prompt_id}/test` |
| GET | `/workspaces/{ws_id}/prompts/{prompt_id}/analytics` |

## Install

```sh
jarvis skill install nexus:prompt-library
```

Source of truth: `backend/routes/routes_prompt_library.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
