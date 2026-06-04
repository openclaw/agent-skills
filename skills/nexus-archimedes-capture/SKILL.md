---
name: nexus-archimedes-capture
description: "HTTP surface for the Archimedes distillation-capture pipeline. Use when an OpenJarvis user wants to call Nexus archimedes.capture (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: archimedes.capture
  source_file: backend/routes/routes_archimedes_capture.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus archimedes.capture

HTTP surface for the Archimedes distillation-capture pipeline.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `archimedes.capture` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/archimedes/capture/consent` |
| POST | `/archimedes/capture/consent` |
| POST | `/archimedes/feedback` |
| GET | `/archimedes/training-queue` |

## Install

```sh
jarvis skill install nexus:archimedes-capture
```

Source of truth: `backend/routes/routes_archimedes_capture.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
