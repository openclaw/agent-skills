---
name: nexus-export-audit
description: "Export & Audit Trail — export conversations/workflows/artifacts + audit logging. Use when an OpenJarvis user wants to call Nexus export.audit (GET) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: export.audit
  source_file: backend/routes/routes_export_audit.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus export.audit

Export & Audit Trail — export conversations/workflows/artifacts + audit logging

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `export.audit` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{workspace_id}/audit-log` |
| GET | `/audit-log/actions` |
| GET | `/channels/{channel_id}/export` |
| GET | `/workspaces/{workspace_id}/export` |
| GET | `/workflows/{workflow_id}/export` |
| GET | `/workspaces/{workspace_id}/export/csv` |
| GET | `/channels/{channel_id}/export/csv` |

## Install

```sh
jarvis skill install nexus:export-audit
```

Source of truth: `backend/routes/routes_export_audit.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
