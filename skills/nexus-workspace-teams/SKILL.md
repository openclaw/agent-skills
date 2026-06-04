---
name: nexus-workspace-teams
description: "Workspace Teams — GitHub-style sub-groupings inside a workspace. Use when an OpenJarvis user wants to call Nexus workspace.teams (DELETE, GET, PATCH, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: workspace.teams
  source_file: backend/routes/routes_workspace_teams.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus workspace.teams

Workspace Teams — GitHub-style sub-groupings inside a workspace.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `workspace.teams` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/teams` |
| GET | `/workspaces/{workspace_id}/teams` |
| GET | `/workspaces/{workspace_id}/teams/{team_id}` |
| PATCH | `/workspaces/{workspace_id}/teams/{team_id}` |
| POST | `/workspaces/{workspace_id}/teams/{team_id}/members` |
| DELETE | `/workspaces/{workspace_id}/teams/{team_id}/members/{user_id}` |
| DELETE | `/workspaces/{workspace_id}/teams/{team_id}` |

## Install

```sh
jarvis skill install nexus:workspace-teams
```

Source of truth: `backend/routes/routes_workspace_teams.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
