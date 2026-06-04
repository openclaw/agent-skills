---
name: nexus-coding-sessions
description: "Coding session REST routes — Codex-class agentic coding sessions. Use when an OpenJarvis user wants to call Nexus coding.sessions (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: coding.sessions
  source_file: backend/routes/routes_coding_sessions.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus coding.sessions

Coding session REST routes — Codex-class agentic coding sessions.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `coding.sessions` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/coding-sessions` |
| GET | `/workspaces/{workspace_id}/coding-sessions` |
| GET | `/coding-sessions/{session_id}` |
| POST | `/coding-sessions/{session_id}/transition` |
| POST | `/coding-sessions/{session_id}/cancel` |

## Install

```sh
jarvis skill install nexus:coding-sessions
```

Source of truth: `backend/routes/routes_coding_sessions.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
