---
name: nexus-command-center
description: "Command Center REST routes — unified observability + control plane. Use when an OpenJarvis user wants to call Nexus command.center (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: command.center
  source_file: backend/routes/routes_command_center.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus command.center

Command Center REST routes — unified observability + control plane

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `command.center` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/command-center/board` |
| GET | `/workspaces/{workspace_id}/command-center/batches` |
| GET | `/workspaces/{workspace_id}/command-center/batches/{batch_id}` |
| GET | `/workspaces/{workspace_id}/command-center/agents` |
| GET | `/workspaces/{workspace_id}/command-center/timeline` |
| GET | `/workspaces/{workspace_id}/command-center/stats` |
| POST | `/workspaces/{workspace_id}/command-center/batches/{batch_id}/cancel` |
| POST | `/workspaces/{workspace_id}/command-center/spawn` |

## Install

```sh
jarvis skill install nexus:command-center
```

Source of truth: `backend/routes/routes_command_center.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
