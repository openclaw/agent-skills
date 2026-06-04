---
name: nexus-ideation
description: "Ideation Module — Brainstorming, feature specs, wireframes, and prototype briefs. Use when an OpenJarvis user wants to call Nexus ideation (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: ideation
  source_file: backend/routes/routes_ideation.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus ideation

Ideation Module — Brainstorming, feature specs, wireframes, and prototype briefs.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `ideation` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/ideas` |
| GET | `/workspaces/{workspace_id}/ideas` |
| GET | `/ideas/{idea_id}` |
| PUT | `/ideas/{idea_id}` |
| DELETE | `/ideas/{idea_id}` |
| POST | `/ideas/{idea_id}/specs` |
| GET | `/ideas/{idea_id}/specs` |
| PUT | `/specs/{spec_id}` |
| DELETE | `/specs/{spec_id}` |
| POST | `/ideas/{idea_id}/wireframes` |
| GET | `/ideas/{idea_id}/wireframes` |
| PUT | `/wireframes/{wireframe_id}` |
| DELETE | `/wireframes/{wireframe_id}` |
| POST | `/ideas/{idea_id}/generate-brief` |
| POST | `/ideas/{idea_id}/send-to-channel` |
| GET | `/idea-templates` |
| POST | `/ideas/{idea_id}/clone-template/{template_id}` |

## Install

```sh
jarvis skill install nexus:ideation
```

Source of truth: `backend/routes/routes_ideation.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
