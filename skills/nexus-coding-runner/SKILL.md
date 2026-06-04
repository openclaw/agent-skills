---
name: nexus-coding-runner
description: "HTTP surface for the coding session runner. Use when an OpenJarvis user wants to call Nexus coding.runner (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: coding.runner
  source_file: backend/routes/routes_coding_runner.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus coding.runner

HTTP surface for the coding session runner.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `coding.runner` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/coding-sessions/{session_id}/run` |
| GET | `/coding-sessions/{session_id}/events` |

## Install

```sh
jarvis skill install nexus:coding-runner
```

Source of truth: `backend/routes/routes_coding_runner.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
