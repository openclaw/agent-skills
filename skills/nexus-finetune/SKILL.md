---
name: nexus-finetune
description: "Prompt Optimization Pipeline — Build datasets & optimize agent system prompts. Use when an OpenJarvis user wants to call Nexus finetune (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: finetune
  source_file: backend/routes/routes_finetune.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus finetune

Prompt Optimization Pipeline — Build datasets & optimize agent system prompts.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `finetune` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/finetune/datasets` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/finetune/datasets` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/finetune/datasets/{dataset_id}/export` |
| DELETE | `/workspaces/{ws_id}/agents/{agent_id}/finetune/datasets/{dataset_id}` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/finetune/jobs` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/finetune/jobs` |
| GET | `/workspaces/{ws_id}/agents/{agent_id}/finetune/jobs/{job_id}` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/finetune/jobs/{job_id}/apply` |

## Install

```sh
jarvis skill install nexus:finetune
```

Source of truth: `backend/routes/routes_finetune.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
