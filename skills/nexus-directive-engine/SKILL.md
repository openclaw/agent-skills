---
name: nexus-directive-engine
description: "Directive Engine — Structured directives as runtime constraints on AI agents. Use when an OpenJarvis user wants to call Nexus directive.engine (GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: directive.engine
  source_file: backend/routes/routes_directive_engine.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus directive.engine

Directive Engine — Structured directives as runtime constraints on AI agents

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `directive.engine` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/directives` |
| GET | `/workspaces/{workspace_id}/directives` |
| GET | `/workspaces/{workspace_id}/directives/active` |
| GET | `/directives/{directive_id}` |
| PUT | `/directives/{directive_id}/activate` |
| PUT | `/directives/{directive_id}/deactivate` |
| GET | `/directives/{directive_id}/tasks` |
| GET | `/directives/{directive_id}/phases` |
| PUT | `/directive-tasks/{task_id}/status` |
| GET | `/directives/{directive_id}/ownership` |
| GET | `/directives/{directive_id}/audit` |
| GET | `/directives/{directive_id}/metrics` |
| GET | `/channels/{channel_id}/directive` |
| POST | `/channels/{channel_id}/directive` |
| PUT | `/channels/{channel_id}/directive` |
| POST | `/directives/upload-document` |
| GET | `/directive-documents/{doc_id}` |
| POST | `/directive-tasks/{task_id}/validate` |
| POST | `/directives/{directive_id}/check-gate/{phase_id}` |
| POST | `/directives/{directive_id}/track-cost` |
| GET | `/directives/{directive_id}/cost` |
| POST | `/directives/{directive_id}/check-conflicts` |
| GET | `/directives/{directive_id}/dashboard` |

## Install

```sh
jarvis skill install nexus:directive-engine
```

Source of truth: `backend/routes/routes_directive_engine.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
