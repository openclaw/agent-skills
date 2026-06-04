---
name: nexus-archimedes
description: "Nexus Archimedes — native, trainable, platform-resident LLM. Use when an OpenJarvis user wants to call Nexus archimedes (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: archimedes
  source_file: backend/routes/routes_archimedes.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus archimedes

Nexus Archimedes — native, trainable, platform-resident LLM.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `archimedes` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/archimedes/chat` |
| POST | `/archimedes/chat/stream` |
| POST | `/archimedes/train` |
| POST | `/archimedes/train/upload` |
| POST | `/archimedes/train/web-search` |
| POST | `/archimedes/train/hf-dataset` |
| GET | `/archimedes/status` |
| GET | `/archimedes/memory` |
| POST | `/archimedes/memory/recompact` |
| GET | `/archimedes/history` |
| DELETE | `/archimedes/history` |
| GET | `/archimedes/context` |
| GET | `/archimedes/checkpoints` |
| POST | `/archimedes/checkpoints/save` |
| POST | `/archimedes/checkpoints/load` |
| POST | `/archimedes/checkpoints/load-base` |
| GET | `/archimedes/seed` |
| POST | `/archimedes/seed/load` |
| POST | `/archimedes/foundation/load` |
| POST | `/archimedes/foundation/unload` |
| GET | `/archimedes/foundation/status` |
| GET | `/archimedes/backends` |
| POST | `/archimedes/backends/chain` |
| POST | `/archimedes/backends/refresh` |
| GET | `/archimedes/embeddings` |
| POST | `/archimedes/embeddings/chain` |
| POST | `/archimedes/agent/native-chat` |
| POST | `/archimedes/agent/run` |
| POST | `/archimedes/agent/run-batch` |
| POST | `/archimedes/agent/run-stream` |
| POST | `/archimedes/agent/run-mcp` |
| POST | `/archimedes/agent/run-mcp-stdio` |
| GET | `/archimedes/agent/keys` |
| GET | `/archimedes/quality/stats` |
| POST | `/archimedes/quality/refresh` |
| POST | `/archimedes/quality/recommend` |
| POST | `/archimedes/quality/feedback` |
| GET | `/archimedes/quality/leaderboard` |
| POST | `/archimedes/quality/experiments` |
| GET | `/archimedes/quality/experiments` |
| GET | `/archimedes/quality/experiments/{exp_id}` |
| POST | `/archimedes/quality/experiments/{exp_id}/cancel` |
| POST | `/archimedes/pipeline/create` |
| POST | `/archimedes/pipeline/{pipeline_id}/upload` |
| POST | `/archimedes/pipeline/{pipeline_id}/start` |
| GET | `/archimedes/pipeline/{pipeline_id}` |
| POST | `/archimedes/pipeline/{pipeline_id}/cancel` |
| GET | `/archimedes/pipeline/list` |
| GET | `/archimedes/ingestion/monitor` |
| GET | `/archimedes/ingestion/stream` |
| GET | `/archimedes/tools` |
| POST | `/archimedes/tools/invoke` |
| POST | `/archimedes/agent/chat` |
| POST | `/archimedes/goals` |
| GET | `/archimedes/goals` |
| PUT | `/archimedes/goals/{goal_id}` |
| POST | `/archimedes/goals/{goal_id}/decompose` |
| POST | `/archimedes/goals/{goal_id}/complete` |
| POST | `/archimedes/feedback` |
| GET | `/archimedes/reasoning/{session_id}` |
| GET | `/archimedes/agent/status` |
| GET | `/archimedes/sessions` |
| GET | `/archimedes/sessions/{session_id}` |
| DELETE | `/archimedes/sessions/{session_id}` |
| GET | `/archimedes/analytics` |
| POST | `/archimedes/reset` |

## Install

```sh
jarvis skill install nexus:archimedes
```

Source of truth: `backend/routes/routes_archimedes.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
