---
name: nexus-skill-marketplace
description: "AI Skills Marketplace — Build, share, and install custom AI agent skills. Use when an OpenJarvis user wants to call Nexus skill.marketplace (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: skill.marketplace
  source_file: backend/routes/routes_skill_marketplace.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus skill.marketplace

AI Skills Marketplace — Build, share, and install custom AI agent skills.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `skill.marketplace` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/skill-marketplace/skills` |
| GET | `/skill-marketplace/stats` |
| GET | `/skill-marketplace/categories` |
| GET | `/skill-marketplace/my-skills` |
| GET | `/skill-marketplace/installed` |
| GET | `/skill-marketplace/skills/{listing_id}` |
| POST | `/skill-marketplace/skills` |
| PUT | `/skill-marketplace/skills/{listing_id}` |
| DELETE | `/skill-marketplace/skills/{listing_id}` |
| POST | `/skill-marketplace/skills/{listing_id}/rate` |
| GET | `/skill-marketplace/skills/{listing_id}/reviews` |
| POST | `/skill-marketplace/skills/{listing_id}/install` |
| DELETE | `/skill-marketplace/skills/{listing_id}/uninstall` |
| POST | `/skill-marketplace/skills/{listing_id}/logo` |
| DELETE | `/skill-marketplace/skills/{listing_id}/logo` |
| GET | `/skill-marketplace/logos/{listing_id}` |

## Install

```sh
jarvis skill install nexus:skill-marketplace
```

Source of truth: `backend/routes/routes_skill_marketplace.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
