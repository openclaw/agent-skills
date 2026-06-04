---
name: nexus-code-dev
description: "Code Execution Sandbox + GitHub/GitLab Integration + CI/CD Triggers. Use when an OpenJarvis user wants to call Nexus code.dev (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: code.dev
  source_file: backend/routes/routes_code_dev.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus code.dev

Code Execution Sandbox + GitHub/GitLab Integration + CI/CD Triggers

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `code.dev` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/code/execute` |
| GET | `/code/runtimes` |
| GET | `/code/executions` |
| POST | `/github/connect` |
| POST | `/github/callback` |
| GET | `/github/connections` |
| DELETE | `/github/connections/{conn_id}` |
| GET | `/github/connections/{conn_id}/repos` |
| GET | `/github/connections/{conn_id}/repos/{owner}/{repo}/tree` |
| GET | `/github/connections/{conn_id}/repos/{owner}/{repo}/file` |
| POST | `/github/connections/{conn_id}/repos/{owner}/{repo}/pr` |
| POST | `/github/connections/{conn_id}/repos/{owner}/{repo}/issues` |
| POST | `/github/webhook` |
| POST | `/workflows/{workflow_id}/trigger/github` |
| GET | `/workflow-templates/dev` |
| POST | `/tasks/{task_id}/link-artifact` |
| GET | `/tasks/{task_id}/linked-artifacts` |
| DELETE | `/tasks/{task_id}/link-artifact/{artifact_id}` |
| GET | `/workspaces/{workspace_id}/console/history` |
| POST | `/external/review` |

## Install

```sh
jarvis skill install nexus:code-dev
```

Source of truth: `backend/routes/routes_code_dev.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
