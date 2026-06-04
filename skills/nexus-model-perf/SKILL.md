---
name: nexus-model-perf
description: "Model Performance & Disagreement Resolution — track model stats, suggest optimal models, consensus protocol. Use when an OpenJarvis user wants to call Nexus model.perf (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: model.perf
  source_file: backend/routes/routes_model_perf.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus model.perf

Model Performance & Disagreement Resolution — track model stats, suggest optimal models, consensus protocol

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `model.perf` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/model-stats` |
| GET | `/workspaces/{workspace_id}/model-recommendations` |
| POST | `/workspaces/{workspace_id}/auto-route` |
| POST | `/channels/{channel_id}/disagreements` |
| POST | `/disagreements/{disagreement_id}/vote` |
| POST | `/disagreements/{disagreement_id}/resolve` |
| GET | `/channels/{channel_id}/disagreements` |
| GET | `/workspaces/{ws_id}/disagreement-audit` |
| POST | `/disagreements/{disagreement_id}/manual-resolve` |
| POST | `/workflows/{workflow_id}/checkpoints` |
| GET | `/workflows/{workflow_id}/checkpoints` |
| GET | `/checkpoints/types` |

## Install

```sh
jarvis skill install nexus:model-perf
```

Source of truth: `backend/routes/routes_model_perf.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
