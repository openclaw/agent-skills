---
name: nexus-agent-training
description: "Agent Training Module — RAG-based knowledge ingestion and retrieval. Use when an OpenJarvis user wants to call Nexus agent.training (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: agent.training
  source_file: backend/routes/routes_agent_training.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus agent.training

Agent Training Module — RAG-based knowledge ingestion and retrieval.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `agent.training` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/train/topics` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/train/suggest-topics` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/train/url` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/train/text` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/train/file` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/train/staleness` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/train/quality-dashboard` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/knowledge` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/knowledge/stats` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/training-sessions` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/training-sessions/{session_id}` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/training-sessions/{session_id}/progress` |
| DELETE | `/workspaces/{ws_id}/agents/{agent_id}/knowledge/{chunk_id}` |
| PUT | `/workspaces/{ws_id}/agents/{agent_id}/knowledge/{chunk_id}` |
| PUT | `/workspaces/{ws_id}/agents/{agent_id}/knowledge/{chunk_id}/flag` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/knowledge/query` |

## Install

```sh
jarvis skill install nexus:agent-training
```

Source of truth: `backend/routes/routes_agent_training.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
