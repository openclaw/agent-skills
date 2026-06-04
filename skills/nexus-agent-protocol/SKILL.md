---
name: nexus-agent-protocol
description: "Nexus agent.protocol API surface. Use when an OpenJarvis user wants to call Nexus agent.protocol (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: agent.protocol
  source_file: backend/routes/routes_agent_protocol.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus agent.protocol

Nexus user-callable surface exposing the `agent.protocol` API.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `agent.protocol` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/channels/{ch_id}/agent-request` |
| POST | `/agent-requests/{req_id}/respond` |
| GET | `/channels/{ch_id}/agent-requests` |
| GET | `/channels/{ch_id}/agent-requests/pending/{agent_key}` |

## Install

```sh
jarvis skill install nexus:agent-protocol
```

Source of truth: `backend/routes/routes_agent_protocol.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
