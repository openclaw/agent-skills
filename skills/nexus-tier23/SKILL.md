---
name: nexus-tier23
description: "Tier 2+3 — Enhanced Agent Builder, AI Team Roles, Real-Time Collab, Multilingual, Voice, Workflow Templates. Use when an OpenJarvis user wants to call Nexus tier23 (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: tier23
  source_file: backend/routes/routes_tier23.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus tier23

Tier 2+3 — Enhanced Agent Builder, AI Team Roles, Real-Time Collab, Multilingual, Voice, Workflow Templates

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `tier23` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/agents/custom` |
| GET | `/agents/custom` |
| GET | `/agents/custom/{agent_id}` |
| PUT | `/agents/custom/{agent_id}` |
| DELETE | `/agents/custom/{agent_id}` |
| POST | `/agents/custom/{agent_id}/test` |
| GET | `/workspaces/{workspace_id}/ai-roles` |
| POST | `/workspaces/{workspace_id}/ai-roles` |
| DELETE | `/workspaces/{workspace_id}/ai-roles/{role_id}` |
| GET | `/workflow-templates/extended` |
| POST | `/presence/heartbeat` |
| GET | `/workspaces/{workspace_id}/presence` |
| POST | `/presence/typing` |
| GET | `/channels/{channel_id}/typing` |
| POST | `/export/chat-to-document` |
| POST | `/export/chat-to-report` |
| POST | `/export/artifacts-to-document` |
| GET | `/i18n/languages` |
| POST | `/notifications/push-token` |
| POST | `/voice-notes` |
| GET | `/voice-notes` |

## Install

```sh
jarvis skill install nexus:tier23
```

Source of truth: `backend/routes/routes_tier23.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
