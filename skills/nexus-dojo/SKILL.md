---
name: nexus-dojo
description: "Dojo Routes — REST API for Agent Dojo sessions, scenarios, extraction. Use when an OpenJarvis user wants to call Nexus dojo (DELETE, GET, PATCH, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: dojo
  source_file: backend/routes/routes_dojo.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus dojo

Dojo Routes — REST API for Agent Dojo sessions, scenarios, extraction.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `dojo` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{ws_id}/dojo/sessions` |
| GET | `/workspaces/{ws_id}/dojo/sessions` |
| GET | `/dojo/sessions/{session_id}` |
| POST | `/dojo/sessions/{session_id}/start` |
| POST | `/dojo/sessions/{session_id}/pause` |
| POST | `/dojo/sessions/{session_id}/resume` |
| POST | `/dojo/sessions/{session_id}/cancel` |
| DELETE | `/dojo/sessions/{session_id}` |
| POST | `/dojo/sessions/{session_id}/fork` |
| GET | `/dojo/scenarios` |
| POST | `/workspaces/{ws_id}/dojo/scenarios` |
| GET | `/dojo/scenarios/{scenario_id}` |
| PATCH | `/dojo/scenarios/{scenario_id}` |
| DELETE | `/dojo/scenarios/{scenario_id}` |
| POST | `/dojo/scenarios/{scenario_id}/clone` |
| GET | `/dojo/marketplace` |
| POST | `/dojo/scenarios/{scenario_id}/publish` |
| POST | `/dojo/scenarios/{scenario_id}/version` |
| GET | `/dojo/scenarios/{scenario_id}/versions` |
| POST | `/dojo/scenarios/{scenario_id}/restore-version` |
| POST | `/workspaces/{ws_id}/dojo/scenarios/import-yaml` |
| GET | `/dojo/scenarios/{scenario_id}/export-yaml` |
| POST | `/dojo/scenarios/{scenario_id}/rate` |
| POST | `/dojo/sessions/{session_id}/extract` |
| GET | `/dojo/sessions/{session_id}/extracted-data` |
| POST | `/dojo/extracted/{extraction_id}/approve` |
| POST | `/dojo/extracted/{extraction_id}/reject` |
| POST | `/dojo/extracted/{extraction_id}/ingest` |
| POST | `/workspaces/{ws_id}/dojo/finetune/exports` |
| GET | `/workspaces/{ws_id}/dojo/finetune/exports` |
| POST | `/workspaces/{ws_id}/dojo/finetune/jobs` |
| GET | `/workspaces/{ws_id}/dojo/finetune/jobs` |
| GET | `/workspaces/{ws_id}/dojo/finetune/jobs/{job_id}` |
| POST | `/dojo/finetune/jobs/{job_id}/promote` |
| GET | `/dojo/redteam/attacks` |
| POST | `/workspaces/{ws_id}/dojo/redteam/run` |
| GET | `/dojo/sessions/{session_id}/safety` |
| GET | `/workspaces/{ws_id}/dojo/redteam/batches/{batch_id}` |
| GET | `/workspaces/{ws_id}/dojo/extracted/queue` |
| POST | `/dojo/extracted/{extraction_id}/pairs/{pair_index}/edit` |
| POST | `/dojo/extracted/{extraction_id}/pairs/{pair_index}/approve` |
| POST | `/dojo/extracted/{extraction_id}/pairs/{pair_index}/reject` |
| POST | `/workspaces/{ws_id}/dojo/sessions/{session_id}/agents/{agent_id}/claim` |
| DELETE | `/workspaces/{ws_id}/dojo/sessions/{session_id}/agents/{agent_id}/claim` |
| POST | `/dojo/sessions/{session_id}/human_turn` |
| GET | `/workspaces/{ws_id}/dojo/config` |
| PATCH | `/workspaces/{ws_id}/dojo/config` |
| GET | `/workspaces/{ws_id}/dojo/audit` |
| GET | `/workspaces/{ws_id}/dojo/approvals` |
| POST | `/dojo/approvals/{approval_id}/decide` |
| POST | `/workspaces/{ws_id}/dojo/roles/{user_id}` |
| PATCH | `/dojo/scenarios/{scenario_id}/rubric` |
| GET | `/dojo/sessions/{session_id}/eval` |
| POST | `/dojo/sessions/{session_id}/eval/run` |
| GET | `/dojo/eval/graders` |
| GET | `/workspaces/{ws_id}/dojo/analytics` |
| POST | `/workspaces/{ws_id}/dojo/byo-providers` |
| GET | `/workspaces/{ws_id}/dojo/byo-providers` |
| DELETE | `/workspaces/{ws_id}/dojo/byo-providers/{provider_id}` |
| POST | `/workspaces/{ws_id}/dojo/byo-providers/{provider_id}/test` |
| POST | `/workspaces/{ws_id}/dojo/arena/tournaments` |
| GET | `/workspaces/{ws_id}/dojo/arena/tournaments` |
| GET | `/workspaces/{ws_id}/dojo/arena/tournaments/{tournament_id}` |
| POST | `/dojo/arena/matchups/{matchup_id}/judge` |
| GET | `/workspaces/{ws_id}/dojo/arena/leaderboard` |
| GET | `/workspaces/{ws_id}/dojo/metrics` |
| GET | `/dojo/metrics` |
| POST | `/dojo/sessions/{session_id}/replay` |
| GET | `/dojo/sessions/{a}/diff/{b}` |
| GET | `/dojo/compliance/packs` |
| GET | `/dojo/compliance/packs/{pack_id}` |
| POST | `/workspaces/{ws_id}/dojo/compliance/packs/{pack_id}/install` |
| POST | `/workspaces/{ws_id}/dojo/compliance/{pack_id}/reports` |

## Install

```sh
jarvis skill install nexus:dojo
```

Source of truth: `backend/routes/routes_dojo.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
