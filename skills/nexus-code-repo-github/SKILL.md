---
name: nexus-code-repo-github
description: "Repo GitHub integration + import/export — final split (#4/n). Use when an OpenJarvis user wants to call Nexus code.repo.github (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: code.repo.github
  source_file: backend/routes/routes_code_repo_github.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus code.repo.github

Repo GitHub integration + import/export — final split (#4/n).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `code.repo.github` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/code-repo/git-export` |
| POST | `/workspaces/{workspace_id}/code-repo/git-import` |
| POST | `/workspaces/{workspace_id}/code-repo/github-push` |
| POST | `/workspaces/{workspace_id}/code-repo/github-pull` |
| GET | `/workspaces/{workspace_id}/code-repo/download` |
| POST | `/workspaces/{workspace_id}/code-repo/import-zip` |
| POST | `/workspaces/{workspace_id}/code-repo/upload-url` |
| POST | `/workspaces/{workspace_id}/code-repo/import-from-gcs` |

## Install

```sh
jarvis skill install nexus:code-repo-github
```

Source of truth: `backend/routes/routes_code_repo_github.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
