---
name: nexus-files
description: "File upload and management routes for channels and tasks. Use when an OpenJarvis user wants to call Nexus files (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: files
  source_file: backend/routes/routes_files.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
  flags: "multipart"
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus files

File upload and management routes for channels and tasks

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `files` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Flags

- `multipart`: surface uses multipart request/response handling.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/channels/{channel_id}/files` |
| POST | `/workspaces/{workspace_id}/files` |
| POST | `/task-sessions/{session_id}/files` |
| GET | `/files/{file_id}` |
| GET | `/files/{file_id}/download` |
| GET | `/files/{file_id}/text` |
| GET | `/files/{file_id}/preview` |
| DELETE | `/files/{file_id}` |
| GET | `/channels/{channel_id}/files` |
| GET | `/task-sessions/{session_id}/files` |
| GET | `/workspaces/{workspace_id}/files` |

## Install

```sh
jarvis skill install nexus:files
```

Source of truth: `backend/routes/routes_files.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
