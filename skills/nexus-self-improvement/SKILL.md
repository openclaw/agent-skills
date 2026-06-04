---
name: nexus-self-improvement
description: "Admin routes for the Nexus self-improvement loop orchestrator. Use when an OpenJarvis user wants to call Nexus self.improvement (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: self.improvement
  source_file: backend/routes/routes_self_improvement.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus self.improvement

Admin routes for the Nexus self-improvement loop orchestrator.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `self.improvement` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/admin/self-improvement/runs` |
| GET | `/admin/self-improvement/runs` |
| GET | `/admin/self-improvement/runs/{run_id}` |
| GET | `/admin/self-improvement/runs/{run_id}/events` |
| GET | `/admin/self-improvement/runs/{run_id}/decisions` |
| POST | `/admin/self-improvement/runs/{run_id}/abort` |

## Install

```sh
jarvis skill install nexus:self-improvement
```

Source of truth: `backend/routes/routes_self_improvement.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
