---
name: nexus-reviews
description: "Marketplace Reviews & Ratings — User feedback on marketplace agents/templates. Use when an OpenJarvis user wants to call Nexus reviews (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: reviews
  source_file: backend/routes/routes_reviews.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus reviews

Marketplace Reviews & Ratings — User feedback on marketplace agents/templates.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `reviews` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/marketplace/{template_id}/reviews` |
| GET | `/marketplace/{template_id}/reviews` |
| PUT | `/marketplace/{template_id}/reviews/{review_id}` |
| DELETE | `/marketplace/{template_id}/reviews/{review_id}` |
| POST | `/marketplace/{template_id}/reviews/{review_id}/flag` |
| POST | `/marketplace/{template_id}/reviews/{review_id}/helpful` |

## Install

```sh
jarvis skill install nexus:reviews
```

Source of truth: `backend/routes/routes_reviews.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
