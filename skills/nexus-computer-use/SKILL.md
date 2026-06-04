---
name: nexus-computer-use
description: "Computer Use REST routes — consent management + tool catalogue. Use when an OpenJarvis user wants to call Nexus computer.use (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: computer.use
  source_file: backend/routes/routes_computer_use.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus computer.use

Computer Use REST routes — consent management + tool catalogue.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `computer.use` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/computer-use/tools` |
| GET | `/workspaces/{workspace_id}/computer-use/consents` |
| POST | `/workspaces/{workspace_id}/computer-use/consents` |
| DELETE | `/computer-use/consents/{consent_id}` |

## Install

```sh
jarvis skill install nexus:computer-use
```

Source of truth: `backend/routes/routes_computer_use.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
