---
name: nexus-handoffs-memory
description: "Agent Handoffs & Knowledge Base - structured context passing and persistent workspace memory. Use when an OpenJarvis user wants to call Nexus handoffs.memory (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: handoffs.memory
  source_file: backend/routes/routes_handoffs_memory.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus handoffs.memory

Agent Handoffs & Knowledge Base - structured context passing and persistent workspace memory

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `handoffs.memory` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/channels/{channel_id}/handoffs` |
| GET | `/channels/{channel_id}/handoffs` |
| PUT | `/handoffs/{handoff_id}/acknowledge` |
| GET | `/workspaces/{workspace_id}/memory` |
| POST | `/workspaces/{workspace_id}/memory` |
| PUT | `/memory/{memory_id}` |
| DELETE | `/memory/{memory_id}` |
| GET | `/memory/categories` |
| POST | `/workspaces/{workspace_id}/memory/semantic-search` |
| POST | `/workspaces/{workspace_id}/memory/upload` |

## Install

```sh
jarvis skill install nexus:handoffs-memory
```

Source of truth: `backend/routes/routes_handoffs_memory.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
