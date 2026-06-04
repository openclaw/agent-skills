---
name: nexus-social-publish
description: "Nexus social.publish API surface. Use when an OpenJarvis user wants to call Nexus social.publish (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: social.publish
  source_file: backend/routes/routes_social_publish.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus social.publish

Nexus user-callable surface exposing the `social.publish` API.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `social.publish` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/social/platforms` |
| POST | `/social/connect` |
| POST | `/social/callback` |
| GET | `/social/connections` |
| DELETE | `/social/connections/{conn_id}` |
| POST | `/media/{media_id}/publish` |
| GET | `/social/publish-jobs` |
| GET | `/social/publish-jobs/{job_id}` |
| POST | `/content/social-caption` |

## Install

```sh
jarvis skill install nexus:social-publish
```

Source of truth: `backend/routes/routes_social_publish.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
