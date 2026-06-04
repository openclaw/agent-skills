---
name: nexus-research
description: "Nexus research API surface. Use when an OpenJarvis user wants to call Nexus research (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: research
  source_file: backend/routes/routes_research.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus research

Nexus user-callable surface exposing the `research` API.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `research` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/research/start` |
| GET | `/research/{session_id}/status` |
| POST | `/research/{session_id}/refine` |
| GET | `/research/{session_id}/report` |
| POST | `/research/{session_id}/export` |
| GET | `/research/history` |
| DELETE | `/research/{session_id}` |
| GET | `/research/config` |
| POST | `/fact-check/verify` |
| GET | `/fact-check/{check_id}/result` |
| GET | `/fact-check/history` |

## Install

```sh
jarvis skill install nexus:research
```

Source of truth: `backend/routes/routes_research.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
