---
name: nexus-discussions
description: "Repo Discussions v1 — GitHub-style discussion forum per repo. Use when an OpenJarvis user wants to call Nexus discussions (DELETE, GET, PATCH, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: discussions
  source_file: backend/routes/routes_discussions.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus discussions

Repo Discussions v1 — GitHub-style discussion forum per repo.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `discussions` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/code-repo/discussions/categories` |
| POST | `/workspaces/{workspace_id}/code-repo/discussions/categories` |
| DELETE | `/workspaces/{workspace_id}/code-repo/discussions/categories/{category_id}` |
| POST | `/workspaces/{workspace_id}/code-repo/discussions` |
| GET | `/workspaces/{workspace_id}/code-repo/discussions` |
| GET | `/workspaces/{workspace_id}/code-repo/discussions/{discussion_id}` |
| PATCH | `/workspaces/{workspace_id}/code-repo/discussions/{discussion_id}` |
| POST | `/workspaces/{workspace_id}/code-repo/discussions/{discussion_id}/close` |
| POST | `/workspaces/{workspace_id}/code-repo/discussions/{discussion_id}/reopen` |
| DELETE | `/workspaces/{workspace_id}/code-repo/discussions/{discussion_id}` |
| POST | `/workspaces/{workspace_id}/code-repo/discussions/{discussion_id}/comments` |
| PATCH | `/workspaces/{workspace_id}/code-repo/discussions/{discussion_id}/comments/{comment_id}` |
| DELETE | `/workspaces/{workspace_id}/code-repo/discussions/{discussion_id}/comments/{comment_id}` |
| POST | `/workspaces/{workspace_id}/code-repo/discussion-comments/{comment_id}/react` |
| POST | `/workspaces/{workspace_id}/code-repo/discussions/{discussion_id}/upvote` |
| DELETE | `/workspaces/{workspace_id}/code-repo/discussions/{discussion_id}/upvote` |
| POST | `/workspaces/{workspace_id}/code-repo/discussions/{discussion_id}/mark-answer` |
| POST | `/workspaces/{workspace_id}/code-repo/discussions/{discussion_id}/pin` |
| POST | `/workspaces/{workspace_id}/code-repo/discussions/{discussion_id}/unpin` |
| POST | `/workspaces/{workspace_id}/code-repo/discussions/{discussion_id}/lock` |
| POST | `/workspaces/{workspace_id}/code-repo/discussions/{discussion_id}/unlock` |

## Install

```sh
jarvis skill install nexus:discussions
```

Source of truth: `backend/routes/routes_discussions.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
