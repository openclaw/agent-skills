---
name: nexus-roi-comparison
description: "Multi-Workspace ROI Comparison Dashboard — compare costs, efficiency, and ROI across workspaces. Use when an OpenJarvis user wants to call Nexus roi.comparison (GET) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: roi.comparison
  source_file: backend/routes/routes_roi_comparison.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus roi.comparison

Multi-Workspace ROI Comparison Dashboard — compare costs, efficiency, and ROI across workspaces.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `roi.comparison` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/roi-comparison/workspaces` |
| GET | `/roi-comparison/trend` |

## Install

```sh
jarvis skill install nexus:roi-comparison
```

Source of truth: `backend/routes/routes_roi_comparison.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
