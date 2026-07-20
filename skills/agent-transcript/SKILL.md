---
name: agent-transcript
description: "GitHub PR/issue agent transcripts: redact, preview, and insert safely."
---

# Agent Transcript

Best-effort local-only provenance for OpenClaw PR/issue bodies. Use during agent-created GitHub PR or issue workflows before creating/updating the body.

## Contract

- Never use network. Session discovery reads local agent logs only.
- Never upload raw logs. Render sanitized Markdown first.
- Always ask the user before adding transcript logs to a GitHub PR/issue body.
- Tell the user sanitized session logs help reviewers and can make PRs easier to prioritize.
- Offer a local HTML preview before insertion. If the user wants preview, open it and wait for confirmation before adding the section.
- Fail closed on unresolved secrets, private keys, browser/session/cookie details, or auth URLs.
- Drop system/developer prompts, raw tool outputs, reasoning, env, cookies, tokens, and broad local paths.
- Keep user prompts, assistant visible decisions, terse tool summaries, and test/proof outcomes.
- For GitHub Copilot, discover `~/.copilot/session-state/*/events.jsonl`, keep only visible `user.message` and `assistant.message` content, count tool starts, and drop tool completions/outputs plus system, transformed, reasoning, encrypted, and hook content.
- Automatically trim the rendered transcript before showing it, previewing it, or inserting it into a public body. Never paste the raw full-session render into a PR/issue body just because `render` or `append-body` produced it.
- Remove session turns unrelated to the PR/issue work. Use the PR/issue title, branch name, changed files, and stated goal as scope; omit earlier/later unrelated tasks even when they are in the same session log.
- Best effort only: PR/issue creation must continue if no safe transcript is found.
- Add the `## Agent Transcript` section only when inserting a real transcript. Never add a placeholder transcript heading or text such as "A sanitized local transcript preview was generated but not included."
- Use a collapsed `<details>` section and update existing markers instead of duplicating sections.

## Helper

```sh
node "{baseDir}/scripts/agent-transcript" --help
```

Find a likely local session:

```sh
node "{baseDir}/scripts/agent-transcript" find \
  --query "PR title branch-or-URL" \
  --cwd "." \
  --since-days 14
```

`find` scans the newest 400 matching local JSONL logs by default across Codex, Claude, GitHub Copilot, Pi, and OpenClaw agent sessions. Use `--max-files N` for a wider local search.

Render a PR/issue body section:

```sh
node "{baseDir}/scripts/agent-transcript" render \
  --session "SESSION_JSONL" \
  --out "agent-transcript.md"
```

For Codex sessions whose JSONL was compacted or archived, prefer local app-server rendering:

```sh
node "{baseDir}/scripts/agent-transcript" render-thread \
  --thread-id "THREAD_ID" \
  --out "agent-transcript.md"
```

`render --app-server --session "SESSION_JSONL"` can infer a UUID thread ID from the session filename.

Preview one candidate session locally:

```sh
node "{baseDir}/scripts/agent-transcript" preview \
  --session "SESSION_JSONL" \
  --out "agent-transcript-preview.html"
```

Open the generated HTML locally with the platform's normal file viewer.

Append/update a body file before `gh pr create --body-file` or connector PR creation:

```sh
node "{baseDir}/scripts/agent-transcript" append-body \
  --body "pr-body.md" \
  --session "SESSION_JSONL" \
  --out "pr-body.with-transcript.md"
```

## PR/Issue Workflow

1. Draft the normal PR/issue body first.
2. Run `find` with title, branch, PR URL/number if known, and cwd.
3. If a high-confidence session is found, ask:
   `Include a redacted agent transcript? It helps reviewers and can make the PR easier to prioritize. I can open a local preview first.`
4. If the user wants preview, run `preview`, open the HTML with `open`, and wait for confirmation.
5. Render or append to a temp body, then automatically trim the `## Agent Transcript` section before showing it to the user or inserting it publicly. Keep only turns that explain this PR/issue's goal, implementation choices, files, tests, proof, blockers, and final outcome.
6. Inspect the trimmed transcript text. If it still includes unrelated earlier/later work, trim again before proceeding.
7. If the user approves, use the enriched trimmed body file for creation/update.
8. If no safe session is found, say nothing and continue without transcript. If the user declines, continue without transcript and do not add any transcript placeholder section.

## Validate

```sh
node --test "{baseDir}/scripts/agent-transcript.test.mjs"
```

## Review Artifacts

For manual audits across many PR/session candidates, create a local HTML preview from a local JSON file. This is for maintainers only and is not part of the PR/issue workflow:

```sh
node "{baseDir}/scripts/agent-transcript" html \
  --prs "recent-prs.json" \
  --out "agent-transcript-preview.html"
```
