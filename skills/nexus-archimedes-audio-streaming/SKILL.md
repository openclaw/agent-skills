---
name: nexus-archimedes-audio-streaming
description: "Archimedes streaming audio routes (Phase 4 ChatGPT-parity slice). Use when an OpenJarvis user wants to call Nexus archimedes.audio.streaming (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: archimedes.audio.streaming
  source_file: backend/routes/routes_archimedes_audio_streaming.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
  flags: "streaming"
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus archimedes.audio.streaming

Archimedes streaming audio routes (Phase 4 ChatGPT-parity slice).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `archimedes.audio.streaming` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Flags

- `streaming`: surface uses streaming request/response handling.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/archimedes/audio/transcribe/stream` |
| POST | `/archimedes/audio/synthesize/stream` |
| GET | `/archimedes/audio/streaming/info` |

## Install

```sh
jarvis skill install nexus:archimedes-audio-streaming
```

Source of truth: `backend/routes/routes_archimedes_audio_streaming.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
