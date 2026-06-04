---
name: nexus-forks
description: "Repo Forks v1 — GitHub-style \"fork this repo\" support. Use when an OpenJarvis user wants to call Nexus forks (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: forks
  source_file: backend/routes/routes_forks.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus forks

Repo Forks v1 — GitHub-style "fork this repo" support.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `forks` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/code-repo/fork` |
| GET | `/workspaces/{workspace_id}/code-repo/forks` |
| GET | `/workspaces/{workspace_id}/code-repo/parent` |

## Install

```sh
jarvis skill install nexus:forks
```

Source of truth: `backend/routes/routes_forks.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
