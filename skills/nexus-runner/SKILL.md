---
name: nexus-runner
description: "HTTP surface for the GitHub Actions-style runner pool (v1). Use when an OpenJarvis user wants to call Nexus runner (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: runner
  source_file: backend/routes/routes_runner.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus runner

HTTP surface for the GitHub Actions-style runner pool (v1).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `runner` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/code-repo/runner/jobs` |
| GET | `/workspaces/{workspace_id}/code-repo/runner/jobs` |
| GET | `/workspaces/{workspace_id}/code-repo/runner/jobs/{job_id}` |
| POST | `/workspaces/{workspace_id}/code-repo/runner/jobs/{job_id}/cancel` |
| POST | `/workspaces/{workspace_id}/repo-runner-toggle` |

## Install

```sh
jarvis skill install nexus:runner
```

Source of truth: `backend/routes/routes_runner.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
