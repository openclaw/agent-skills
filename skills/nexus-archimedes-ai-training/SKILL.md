---
name: nexus-archimedes-ai-training
description: "Archimedes AI Training routes — drive the multi-agent training pipeline. Use when an OpenJarvis user wants to call Nexus archimedes.ai.training (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: archimedes.ai.training
  source_file: backend/routes/routes_archimedes_ai_training.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus archimedes.ai.training

Archimedes AI Training routes — drive the multi-agent training pipeline.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `archimedes.ai.training` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/archimedes/ai-training/providers` |
| POST | `/archimedes/ai-training/run` |
| POST | `/archimedes/ai-training/batch` |
| GET | `/archimedes/ai-training/runs` |
| GET | `/archimedes/ai-training/runs/{run_id}` |
| POST | `/archimedes/ai-training/runs/{run_id}/cancel` |
| POST | `/archimedes/ai-training/autoloop/start` |
| POST | `/archimedes/ai-training/autoloop/stop` |
| GET | `/archimedes/ai-training/autoloop/status` |
| GET | `/archimedes/ai-training/progress` |
| GET | `/archimedes/ai-training/audit` |
| GET | `/archimedes/ai-training/security` |

## Install

```sh
jarvis skill install nexus:archimedes-ai-training
```

Source of truth: `backend/routes/routes_archimedes_ai_training.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
