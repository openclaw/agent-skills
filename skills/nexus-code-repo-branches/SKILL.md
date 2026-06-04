---
name: nexus-code-repo-branches
description: "Repo Branches v1 — list/create/delete/merge/compare endpoints. Use when an OpenJarvis user wants to call Nexus code.repo.branches (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: code.repo.branches
  source_file: backend/routes/routes_code_repo_branches.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus code.repo.branches

Repo Branches v1 — list/create/delete/merge/compare endpoints.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `code.repo.branches` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/code-repo/branches` |
| POST | `/workspaces/{workspace_id}/code-repo/branches` |
| DELETE | `/workspaces/{workspace_id}/code-repo/branches/{branch_name}` |
| POST | `/workspaces/{workspace_id}/code-repo/branches/{branch_name}/merge` |
| GET | `/workspaces/{workspace_id}/code-repo/branches/compare` |

## Install

```sh
jarvis skill install nexus:code-repo-branches
```

Source of truth: `backend/routes/routes_code_repo_branches.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
