---
name: nexus-sharing
description: "Content sharing routes — uses JSONB adapter for backward compatibility. Use when an OpenJarvis user wants to call Nexus sharing (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: sharing
  source_file: backend/routes/routes_sharing.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus sharing

Content sharing routes — uses JSONB adapter for backward compatibility.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `sharing` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/channels/{channel_id}/share` |
| GET | `/shares/{share_id}` |
| POST | `/replay/{share_id}` |
| GET | `/channels/{channel_id}/shares` |

## Install

```sh
jarvis skill install nexus:sharing
```

Source of truth: `backend/routes/routes_sharing.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
