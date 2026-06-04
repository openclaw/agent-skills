---
name: nexus-code-repo-issues
description: "Repo Issues v1 — lightweight issue tracker, companion to PRs. Use when an OpenJarvis user wants to call Nexus code.repo.issues (DELETE, GET, PATCH, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: code.repo.issues
  source_file: backend/routes/routes_code_repo_issues.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus code.repo.issues

Repo Issues v1 — lightweight issue tracker, companion to PRs.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `code.repo.issues` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/code-repo/issues` |
| GET | `/workspaces/{workspace_id}/code-repo/issues` |
| GET | `/workspaces/{workspace_id}/code-repo/issues/{issue_id}` |
| PATCH | `/workspaces/{workspace_id}/code-repo/issues/{issue_id}` |
| POST | `/workspaces/{workspace_id}/code-repo/issues/{issue_id}/close` |
| POST | `/workspaces/{workspace_id}/code-repo/issues/{issue_id}/reopen` |
| POST | `/workspaces/{workspace_id}/code-repo/issues/{issue_id}/comments` |
| PATCH | `/workspaces/{workspace_id}/code-repo/issues/{issue_id}/comments/{comment_id}` |
| DELETE | `/workspaces/{workspace_id}/code-repo/issues/{issue_id}/comments/{comment_id}` |
| POST | `/workspaces/{workspace_id}/code-repo/issue-comments/{comment_id}/react` |
| GET | `/workspaces/{workspace_id}/code-repo/issues/{issue_id}/timeline` |
| GET | `/workspaces/{workspace_id}/code-repo/templates/issues` |

## Install

```sh
jarvis skill install nexus:code-repo-issues
```

Source of truth: `backend/routes/routes_code_repo_issues.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
