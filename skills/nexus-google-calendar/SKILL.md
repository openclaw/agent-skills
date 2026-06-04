---
name: nexus-google-calendar
description: "Google Calendar Connector — OAuth + Calendar REST API integration for Nexus. Use when an OpenJarvis user wants to call Nexus google.calendar (DELETE, GET, PATCH, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: google.calendar
  source_file: backend/routes/routes_google_calendar.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus google.calendar

Google Calendar Connector — OAuth + Calendar REST API integration for Nexus.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `google.calendar` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/google-calendar/status` |
| POST | `/google-calendar/connect` |
| GET | `/google-calendar/callback` |
| GET | `/google-calendar/connections` |
| DELETE | `/google-calendar/connections/{connection_id}` |
| GET | `/google-calendar/calendars` |
| GET | `/google-calendar/calendars/{calendar_id}/events` |
| GET | `/google-calendar/calendars/{calendar_id}/events/{event_id}` |
| POST | `/google-calendar/calendars/{calendar_id}/events` |
| PATCH | `/google-calendar/calendars/{calendar_id}/events/{event_id}` |
| DELETE | `/google-calendar/calendars/{calendar_id}/events/{event_id}` |
| POST | `/google-calendar/freebusy` |
| POST | `/google-calendar/quick-add` |

## Install

```sh
jarvis skill install nexus:google-calendar
```

Source of truth: `backend/routes/routes_google_calendar.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
