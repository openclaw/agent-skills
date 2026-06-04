---
name: nexus-marketplace
description: "Marketplace & Artifacts API routes. Use when an OpenJarvis user wants to call Nexus marketplace (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: marketplace
  source_file: backend/routes/routes_marketplace.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus marketplace

Marketplace & Artifacts API routes

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `marketplace` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/marketplace` |
| GET | `/marketplace/org/{org_id}` |
| GET | `/marketplace/{template_id}` |
| POST | `/marketplace/publish` |
| POST | `/marketplace/{template_id}/import` |
| POST | `/marketplace/{template_id}/rate` |
| POST | `/workspaces/{workspace_id}/artifacts` |
| GET | `/workspaces/{workspace_id}/artifacts` |
| GET | `/artifacts/{artifact_id}` |
| PUT | `/artifacts/{artifact_id}` |
| POST | `/artifacts/{artifact_id}/pin` |
| POST | `/artifacts/{artifact_id}/tag` |
| DELETE | `/artifacts/{artifact_id}` |
| POST | `/artifacts/{artifact_id}/restore/{version}` |
| GET | `/artifacts/{artifact_id}/diff` |
| POST | `/artifacts/{artifact_id}/attachments` |
| GET | `/artifacts/{artifact_id}/attachments/{attachment_id}` |
| DELETE | `/artifacts/{artifact_id}/attachments/{attachment_id}` |

## Install

```sh
jarvis skill install nexus:marketplace
```

Source of truth: `backend/routes/routes_marketplace.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
