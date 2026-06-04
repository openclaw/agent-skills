---
name: nexus-repo-ci
description: "Repo CI configurations — declare which workflows fire on PR events. Use when an OpenJarvis user wants to call Nexus repo.ci (DELETE, GET, PATCH, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: repo.ci
  source_file: backend/routes/routes_repo_ci.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus repo.ci

Repo CI configurations — declare which workflows fire on PR events.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `repo.ci` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/code-repo/ci-configs` |
| GET | `/workspaces/{workspace_id}/code-repo/ci-configs` |
| PATCH | `/workspaces/{workspace_id}/code-repo/ci-configs/{config_id}` |
| DELETE | `/workspaces/{workspace_id}/code-repo/ci-configs/{config_id}` |

## Install

```sh
jarvis skill install nexus:repo-ci
```

Source of truth: `backend/routes/routes_repo_ci.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
