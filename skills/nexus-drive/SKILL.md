---
name: nexus-drive
description: "Built-in File Storage / Drive — workspace + personal drives with folders, trash, sharing. Use when an OpenJarvis user wants to call Nexus drive (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: drive
  source_file: backend/routes/routes_drive.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus drive

Built-in File Storage / Drive — workspace + personal drives with folders, trash, sharing

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `drive` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/drive/upload` |
| POST | `/drive/folder` |
| GET | `/drive/list` |
| GET | `/drive/file/{file_id}` |
| GET | `/drive/file/{file_id}/download` |
| PUT | `/drive/file/{file_id}/move` |
| PUT | `/drive/file/{file_id}/rename` |
| DELETE | `/drive/file/{file_id}` |
| POST | `/drive/file/{file_id}/restore` |
| GET | `/drive/search` |
| POST | `/drive/file/{file_id}/share` |
| GET | `/drive/shared/{token}` |
| GET | `/drive/storage-usage` |

## Install

```sh
jarvis skill install nexus:drive
```

Source of truth: `backend/routes/routes_drive.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
