---
name: nexus-code-repo
description: "Code Repository - Per-workspace multi-repo with file tree, versioning, and linking. Use when an OpenJarvis user wants to call Nexus code.repo (DELETE, GET, PATCH, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: code.repo
  source_file: backend/routes/routes_code_repo.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus code.repo

Code Repository - Per-workspace multi-repo with file tree, versioning, and linking

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `code.repo` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/code-repos` |
| POST | `/workspaces/{workspace_id}/code-repos` |
| PUT | `/workspaces/{workspace_id}/code-repos/{repo_id}` |
| DELETE | `/workspaces/{workspace_id}/code-repos/{repo_id}` |
| GET | `/channels/{channel_id}/repos` |
| POST | `/channels/{channel_id}/repos` |
| DELETE | `/channels/{channel_id}/repos/{repo_id}` |
| GET | `/workspaces/{workspace_id}/code-repo` |
| GET | `/workspaces/{workspace_id}/code-repo/tree` |
| POST | `/workspaces/{workspace_id}/code-repo/files` |
| POST | `/workspaces/{workspace_id}/code-repo/folders` |
| GET | `/workspaces/{workspace_id}/code-repo/files/{file_id}` |
| PUT | `/workspaces/{workspace_id}/code-repo/files/{file_id}` |
| DELETE | `/workspaces/{workspace_id}/code-repo/files/{file_id}` |
| PATCH | `/workspaces/{workspace_id}/code-repo/files/{file_id}` |
| GET | `/workspaces/{workspace_id}/code-repo/history` |
| GET | `/workspaces/{workspace_id}/code-repo/commits/{commit_id}` |
| POST | `/workspaces/{workspace_id}/code-repo/links` |
| GET | `/workspaces/{workspace_id}/code-repo/links` |
| DELETE | `/workspaces/{workspace_id}/code-repo/links/{link_id}` |
| POST | `/workspaces/{workspace_id}/code-repo/ai-update` |
| POST | `/workspaces/{workspace_id}/code-repo/pull-requests` |
| GET | `/workspaces/{workspace_id}/code-repo/pull-requests` |
| GET | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}` |
| PATCH | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}` |
| POST | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/merge` |
| POST | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/ready-for-review` |
| POST | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/convert-to-draft` |
| POST | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/auto-merge` |
| POST | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/close` |
| POST | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/reopen` |
| GET | `/workspaces/{workspace_id}/saved-replies` |
| POST | `/workspaces/{workspace_id}/saved-replies` |
| PATCH | `/workspaces/{workspace_id}/saved-replies/{reply_id}` |
| DELETE | `/workspaces/{workspace_id}/saved-replies/{reply_id}` |

## Install

```sh
jarvis skill install nexus:code-repo
```

Source of truth: `backend/routes/routes_code_repo.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
