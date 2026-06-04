---
name: nexus-projects
description: "Projects module - workspace-level project management with tasks and artifacts. Use when an OpenJarvis user wants to call Nexus projects (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: projects
  source_file: backend/routes/routes_projects.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus projects

Projects module - workspace-level project management with tasks and artifacts

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `projects` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/projects` |
| POST | `/workspaces/{workspace_id}/projects` |
| GET | `/projects/{project_id}` |
| PUT | `/projects/{project_id}` |
| DELETE | `/projects/{project_id}` |
| GET | `/projects/{project_id}/instructions` |
| PUT | `/projects/{project_id}/instructions` |
| GET | `/projects/{project_id}/schedules` |
| GET | `/projects/{project_id}/tasks` |
| POST | `/projects/{project_id}/tasks` |
| PUT | `/projects/{project_id}/tasks/{task_id}` |
| DELETE | `/projects/{project_id}/tasks/{task_id}` |
| POST | `/projects/{project_id}/tasks/bulk-update` |
| POST | `/projects/{project_id}/tasks/bulk-delete` |
| GET | `/workspaces/{workspace_id}/tasks/search` |
| GET | `/workspaces/{workspace_id}/assignees` |
| GET | `/channels/{channel_id}/projects` |
| POST | `/tasks/{task_id}/comments` |
| GET | `/tasks/{task_id}/comments` |
| DELETE | `/task-comments/{comment_id}` |
| POST | `/tasks/{task_id}/attachments` |
| GET | `/tasks/{task_id}/attachments` |
| GET | `/task-attachments/{attachment_id}` |
| DELETE | `/task-attachments/{attachment_id}` |
| GET | `/tasks/{task_id}/subtasks` |
| GET | `/tasks/{task_id}/activity` |
| GET | `/my-tasks` |
| GET | `/project-config` |
| GET | `/projects/{project_id}/milestones` |
| POST | `/projects/{project_id}/milestones` |
| PUT | `/projects/{project_id}/milestones/{milestone_id}` |
| DELETE | `/projects/{project_id}/milestones/{milestone_id}` |
| GET | `/tasks/{task_id}/relationships` |
| POST | `/tasks/{task_id}/relationships` |
| DELETE | `/relationships/{rel_id}` |
| GET | `/tasks/{task_id}/detail` |
| GET | `/project-templates` |
| POST | `/workspaces/{workspace_id}/projects/from-template` |
| GET | `/workspaces/{workspace_id}/code-repo/analytics` |
| GET | `/workspaces/{workspace_id}/milestone-alerts` |

## Install

```sh
jarvis skill install nexus:projects
```

Source of truth: `backend/routes/routes_projects.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
