---
name: nexus-repo-labels
description: "Repo Labels — first-class managed labels for issues. Use when an OpenJarvis user wants to call Nexus repo.labels (DELETE, GET, PATCH, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: repo.labels
  source_file: backend/routes/routes_repo_labels.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus repo.labels

Repo Labels — first-class managed labels for issues.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `repo.labels` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/code-repo/labels` |
| GET | `/workspaces/{workspace_id}/code-repo/labels` |
| PATCH | `/workspaces/{workspace_id}/code-repo/labels/{label_id}` |
| DELETE | `/workspaces/{workspace_id}/code-repo/labels/{label_id}` |

## Install

```sh
jarvis skill install nexus:repo-labels
```

Source of truth: `backend/routes/routes_repo_labels.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
