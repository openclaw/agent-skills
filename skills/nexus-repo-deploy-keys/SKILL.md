---
name: nexus-repo-deploy-keys
description: "Repo Deploy Keys — workspace-scoped credentials for repo automation. Use when an OpenJarvis user wants to call Nexus repo.deploy.keys (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: repo.deploy.keys
  source_file: backend/routes/routes_repo_deploy_keys.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus repo.deploy.keys

Repo Deploy Keys — workspace-scoped credentials for repo automation.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `repo.deploy.keys` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/code-repo/deploy-keys` |
| GET | `/workspaces/{workspace_id}/code-repo/deploy-keys` |
| GET | `/workspaces/{workspace_id}/code-repo/deploy-keys/{key_id}` |
| DELETE | `/workspaces/{workspace_id}/code-repo/deploy-keys/{key_id}` |

## Install

```sh
jarvis skill install nexus:repo-deploy-keys
```

Source of truth: `backend/routes/routes_repo_deploy_keys.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
