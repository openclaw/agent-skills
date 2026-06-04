---
name: nexus-archimedes-voice
description: "Archimedes voice command routes (Phase 9.13). Use when an OpenJarvis user wants to call Nexus archimedes.voice (POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: archimedes.voice
  source_file: backend/routes/routes_archimedes_voice.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus archimedes.voice

Archimedes voice command routes (Phase 9.13).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `archimedes.voice` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/archimedes/voice/transcribe` |
| POST | `/archimedes/voice/synthesize` |
| POST | `/archimedes/voice/session/stream` |

## Install

```sh
jarvis skill install nexus:archimedes-voice
```

Source of truth: `backend/routes/routes_archimedes_voice.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
