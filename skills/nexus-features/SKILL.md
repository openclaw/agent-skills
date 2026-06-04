---
name: nexus-features
description: "Additional Features — Channel archiving, message pinning, workspace export. Use when an OpenJarvis user wants to call Nexus features (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: features
  source_file: backend/routes/routes_features.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus features

Additional Features — Channel archiving, message pinning, workspace export.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `features` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/channels/{channel_id}/archive` |
| POST | `/channels/{channel_id}/unarchive` |
| POST | `/channels/{channel_id}/messages/{message_id}/pin` |
| POST | `/channels/{channel_id}/messages/{message_id}/unpin` |
| GET | `/channels/{channel_id}/agent-performance` |

## Install

```sh
jarvis skill install nexus:features
```

Source of truth: `backend/routes/routes_features.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
