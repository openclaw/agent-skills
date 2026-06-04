---
name: nexus-ai-tools
description: "AI Agent Tools - allows AI agents to autonomously interact with Nexus workspace resources. Use when an OpenJarvis user wants to call Nexus ai.tools (GET) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: ai.tools
  source_file: backend/routes/routes_ai_tools.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus ai.tools

AI Agent Tools - allows AI agents to autonomously interact with Nexus workspace resources

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `ai.tools` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/ai-tools` |
| GET | `/workspaces/{workspace_id}/tools` |
| GET | `/channels/{channel_id}/mentionable` |

## Install

```sh
jarvis skill install nexus:ai-tools
```

Source of truth: `backend/routes/routes_ai_tools.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
