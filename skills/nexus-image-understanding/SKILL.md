---
name: nexus-image-understanding
description: "Nexus image.understanding API surface. Use when an OpenJarvis user wants to call Nexus image.understanding (POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: image.understanding
  source_file: backend/routes/routes_image_understanding.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
  flags: "multipart"
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus image.understanding

Nexus user-callable surface exposing the `image.understanding` API.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `image.understanding` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Flags

- `multipart`: surface uses multipart request/response handling.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/tools/analyze-image` |
| POST | `/channels/{ch_id}/analyze-attachment` |

## Install

```sh
jarvis skill install nexus:image-understanding
```

Source of truth: `backend/routes/routes_image_understanding.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
