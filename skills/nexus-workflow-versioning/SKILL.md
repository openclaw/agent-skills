---
name: nexus-workflow-versioning
description: "Workflow Versioning & Rollback — Snapshot and restore workflow graphs. Use when an OpenJarvis user wants to call Nexus workflow.versioning (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: workflow.versioning
  source_file: backend/routes/routes_workflow_versioning.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus workflow.versioning

Workflow Versioning & Rollback — Snapshot and restore workflow graphs.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `workflow.versioning` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workflows/{workflow_id}/versions` |
| GET | `/workflows/{workflow_id}/versions` |
| GET | `/workflows/{workflow_id}/versions/{version_id}` |
| POST | `/workflows/{workflow_id}/versions/{version_id}/rollback` |
| DELETE | `/workflows/{workflow_id}/versions/{version_id}` |

## Install

```sh
jarvis skill install nexus:workflow-versioning
```

Source of truth: `backend/routes/routes_workflow_versioning.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
