---
name: nexus-ai-skills
description: "AI Skills Configuration - Vendor-supported skill libraries per AI model. Use when an OpenJarvis user wants to call Nexus ai.skills (GET, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: ai.skills
  source_file: backend/routes/routes_ai_skills.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus ai.skills

AI Skills Configuration - Vendor-supported skill libraries per AI model

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `ai.skills` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/ai-skills` |
| GET | `/workspaces/{workspace_id}/ai-skills` |
| PUT | `/workspaces/{workspace_id}/ai-skills` |
| PUT | `/workspaces/{workspace_id}/ai-skills/{model_key}` |
| GET | `/workspaces/{workspace_id}/ai-skills/{model_key}` |

## Install

```sh
jarvis skill install nexus:ai-skills
```

Source of truth: `backend/routes/routes_ai_skills.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
