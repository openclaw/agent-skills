---
name: nexus-code-review
description: "Code review REST routes — intent-aware PR review. Use when an OpenJarvis user wants to call Nexus code.review (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: code.review
  source_file: backend/routes/routes_code_review.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus code.review

Code review REST routes — intent-aware PR review.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `code.review` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/repos/{repo_id}/prs/{pr_number}/review` |
| GET | `/repos/{repo_id}/prs/{pr_number}/reviews` |

## Install

```sh
jarvis skill install nexus:code-review
```

Source of truth: `backend/routes/routes_code_review.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
