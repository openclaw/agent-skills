---
name: nexus-code-repo-pr-collab
description: "Repo PR collaboration — comments / reviewers / reviews / checks / timeline. Use when an OpenJarvis user wants to call Nexus code.repo.pr.collab (DELETE, GET, PATCH, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: code.repo.pr.collab
  source_file: backend/routes/routes_code_repo_pr_collab.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus code.repo.pr.collab

Repo PR collaboration — comments / reviewers / reviews / checks / timeline.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `code.repo.pr.collab` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/threads` |
| POST | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/threads/{thread_id}/resolve` |
| POST | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/threads/{thread_id}/unresolve` |
| POST | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/comments` |
| GET | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/comments` |
| PATCH | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/comments/{comment_id}` |
| DELETE | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/comments/{comment_id}` |
| POST | `/workspaces/{workspace_id}/code-repo/pr-comments/{comment_id}/react` |
| POST | `/workspaces/{workspace_id}/code-repo/pr-review-comments/{comment_id}/react` |
| POST | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/reviewers` |
| DELETE | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/reviewers/{user_id}` |
| POST | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/reviewers/team` |
| POST | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/reviews` |
| DELETE | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/reviews/{review_id}` |
| POST | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/checks` |
| GET | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/checks` |
| DELETE | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/checks/{check_id}` |
| GET | `/workspaces/{workspace_id}/code-repo/pull-requests/{pr_id}/timeline` |
| GET | `/workspaces/{workspace_id}/code-repo/templates/pr` |

## Install

```sh
jarvis skill install nexus:code-repo-pr-collab
```

Source of truth: `backend/routes/routes_code_repo_pr_collab.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
