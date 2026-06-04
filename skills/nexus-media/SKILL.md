---
name: nexus-media
description: "Multimedia — Video/Audio/Media Generation, TTS, STT, Media Library. Use when an OpenJarvis user wants to call Nexus media (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: media
  source_file: backend/routes/routes_media.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
  flags: "multipart"
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus media

Multimedia — Video/Audio/Media Generation, TTS, STT, Media Library

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `media` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Flags

- `multipart`: surface uses multipart request/response handling.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/media/config` |
| POST | `/workspaces/{workspace_id}/generate-video` |
| POST | `/workspaces/{workspace_id}/generate-audio` |
| POST | `/workspaces/{workspace_id}/transcribe` |
| GET | `/workspaces/{workspace_id}/media` |
| GET | `/media/{media_id}` |
| GET | `/media/operations/{operation_id}/status` |
| GET | `/media/{media_id}/data` |
| PUT | `/media/{media_id}` |
| DELETE | `/media/{media_id}` |
| GET | `/workspaces/{workspace_id}/media/metrics` |
| GET | `/workspaces/{workspace_id}/media/folders` |
| POST | `/workspaces/{workspace_id}/media/jobs` |
| GET | `/workspaces/{workspace_id}/media/jobs` |
| GET | `/media/jobs/{job_id}` |
| POST | `/workspaces/{workspace_id}/image-to-video` |
| POST | `/workspaces/{workspace_id}/media/bulk/tag` |
| POST | `/workspaces/{workspace_id}/media/bulk/move` |
| POST | `/workspaces/{workspace_id}/media/bulk/delete` |
| POST | `/media/{media_id}/share` |
| GET | `/media/shared/{token}` |
| POST | `/workspaces/{workspace_id}/generate-music` |
| POST | `/workspaces/{workspace_id}/generate-sfx` |
| POST | `/workspaces/{workspace_id}/video/storyboard` |
| GET | `/workspaces/{workspace_id}/video/storyboards` |
| POST | `/video/storyboards/{storyboard_id}/generate` |
| POST | `/workspaces/{workspace_id}/audio/tts-preview` |
| POST | `/workspaces/{workspace_id}/podcast/generate` |
| GET | `/workspaces/{workspace_id}/podcasts` |
| GET | `/workspaces/{workspace_id}/media/analytics` |
| POST | `/workspaces/{workspace_id}/media/schedules` |
| GET | `/workspaces/{workspace_id}/media/schedules` |
| DELETE | `/media/schedules/{schedule_id}` |
| GET | `/workspaces/{workspace_id}/media/smart-folders` |
| GET | `/media/{media_id}/versions` |
| POST | `/media/{media_id}/versions/{version}/restore` |
| POST | `/workspaces/{workspace_id}/audio/tts-stream` |
| POST | `/workspaces/{workspace_id}/video/compose` |
| GET | `/workspaces/{workspace_id}/media/storage` |
| POST | `/workspaces/{workspace_id}/media/upload` |

## Install

```sh
jarvis skill install nexus:media
```

Source of truth: `backend/routes/routes_media.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
