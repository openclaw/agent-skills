---
name: nexus-plm-advanced
description: "PLM Phases 2-5 — Sprints, Dependencies, Milestones, Portfolios, Time Tracking, Automation, Custom Fields. Use when an OpenJarvis user wants to call Nexus plm.advanced (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: plm.advanced
  source_file: backend/routes/routes_plm_advanced.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus plm.advanced

PLM Phases 2-5 — Sprints, Dependencies, Milestones, Portfolios, Time Tracking, Automation, Custom Fields

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `plm.advanced` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/projects/{project_id}/sprints` |
| GET | `/projects/{project_id}/sprints` |
| PUT | `/sprints/{sprint_id}` |
| POST | `/sprints/{sprint_id}/tasks` |
| GET | `/sprints/{sprint_id}/board` |
| GET | `/sprints/{sprint_id}/burndown` |
| DELETE | `/sprints/{sprint_id}` |
| POST | `/tasks/dependencies` |
| GET | `/tasks/{task_id}/dependencies` |
| DELETE | `/dependencies/{dep_id}` |
| PUT | `/milestones/{ms_id}` |
| DELETE | `/milestones/{ms_id}` |
| GET | `/projects/{project_id}/gantt` |
| GET | `/workspaces/{workspace_id}/portfolio` |
| POST | `/workspaces/{workspace_id}/programs` |
| GET | `/workspaces/{workspace_id}/programs` |
| POST | `/programs/{program_id}/projects` |
| DELETE | `/programs/{program_id}` |
| POST | `/portfolios` |
| GET | `/portfolios` |
| POST | `/portfolios/{portfolio_id}/programs` |
| GET | `/portfolios/{portfolio_id}/health` |
| POST | `/time-entries` |
| GET | `/tasks/{task_id}/time-entries` |
| GET | `/my-timesheet` |
| DELETE | `/time-entries/{entry_id}` |
| POST | `/projects/{project_id}/automations` |
| GET | `/projects/{project_id}/automations` |
| PUT | `/automations/{rule_id}` |
| DELETE | `/automations/{rule_id}` |
| GET | `/automations/triggers` |
| POST | `/projects/{project_id}/recurring-tasks` |
| GET | `/projects/{project_id}/recurring-tasks` |
| POST | `/projects/{project_id}/custom-fields` |
| GET | `/projects/{project_id}/custom-fields` |
| DELETE | `/custom-fields/{field_id}` |
| POST | `/tasks/{task_id}/custom-values` |
| GET | `/tasks/{task_id}/custom-values` |
| POST | `/projects/{project_id}/field-templates` |
| GET | `/field-templates` |
| POST | `/projects/{project_id}/apply-template` |
| GET | `/plm-config` |

## Install

```sh
jarvis skill install nexus:plm-advanced
```

Source of truth: `backend/routes/routes_plm_advanced.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
