---
name: nexus-image-gen
description: "Image Generation — Gemini Nano Banana (default) + user-provided API key support. Use when an OpenJarvis user wants to call Nexus image.gen (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: image.gen
  source_file: backend/routes/routes_image_gen.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
  flags: "multipart"
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus image.gen

Image Generation — Gemini Nano Banana (default) + user-provided API key support

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `image.gen` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Flags

- `multipart`: surface uses multipart request/response handling.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/generate-image` |
| GET | `/images/{image_id}` |
| GET | `/images/{image_id}/data` |
| GET | `/workspaces/{workspace_id}/images` |
| DELETE | `/images/{image_id}` |
| GET | `/workspaces/{workspace_id}/image-gen/metrics` |

## Install

```sh
jarvis skill install nexus:image-gen
```

Source of truth: `backend/routes/routes_image_gen.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
