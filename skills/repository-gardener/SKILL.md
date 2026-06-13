---
name: repository-gardener
description: "Run a conservative report-first repository garden: inspect code, docs, tests, and proof drift, then propose or apply only narrow guarded fixes."
metadata:
  version: "2026-06-13"
---

# Repository Gardener

Run a bounded repository health pass that reduces entropy instead of creating
drive-by cleanup noise.

Use when the user asks for repository gardener, repo garden, weekly repo health,
entropy reduction, code health maintenance, stale docs/tests/examples review, or
a guarded cleanup PR.

## Contract

- Default to report-only mode.
- Enter fix mode only when the user explicitly asks for guarded fixes.
- Follow the local repo instructions before inspecting or editing files.
- Keep every conclusion tied to source, commands, tests, logs, CI, docs, issues,
  or PR evidence.
- Do not invent repository policy, artifact paths, schedules, or ownership.
- Do not create hidden memory, ambient state, broad refactors, mass formatting,
  or speculative rewrites.
- Do not post GitHub comments, open issues, open PRs, schedule jobs, or publish
  artifacts unless the user explicitly asks.
- Redact secrets, private URLs, private account data, raw logs, and large copied
  source blobs from reports.
- Keep output bounded enough for a maintainer to review in one pass.

## Modes

Use these names in your own plan and report:

- `report`: inspect, run proof, and produce findings/actions only.
- `guarded-fix`: make narrow edits only after report evidence shows a safe,
  local fix class.
- `schedule`: prepare an explicit OpenClaw cron or repository automation prompt
  that runs this skill later; do not install it silently.
- `publish`: prepare ClawHub publishing steps for this skill or repo-owned
  gardening policy; do not publish silently.

If the user does not specify a mode, use `report`.

## Workflow

1. Resolve the repository and scope.
   - Run `git status -sb`.
   - Confirm the current repo, branch, dirty files, issue/PR links, and target
     branch.
   - Read root and scoped agent instructions before touching files.
   - If the request came from GitHub, fetch the live issue/PR state with `gh`.
2. Define the garden boundary.
   - Name the repo areas in scope: code, docs, tests, examples, CI, packaging,
     release readiness, or proof artifacts.
   - Exclude generated, vendored, build, lockfile, migration, snapshot, and
     ownership-sensitive paths unless the repo instructions say otherwise.
   - Prefer repo-local policy. If none exists, use report-only and recommend a
     policy follow-up instead of inventing one.
3. Collect evidence.
   - Inspect recent changes, failing or skipped checks, stale docs/examples,
     TODO/FIXME clusters, repeated review findings, flaky or quarantined tests,
     old CI failures, and proof gaps.
   - Use structured tools (`rg`, package scripts, test runners, docs linters,
     type checks, CI logs, `gh`) rather than ad hoc guesses.
   - For dependency-backed behavior, read current upstream docs/source/types
     before calling a finding confirmed.
4. Run proof.
   - Prefer the repo's targeted checks first.
   - Use broad or remote proof only when the repo policy calls for it or the
     risk justifies it.
   - Record commands exactly, including skipped checks and why they were
     skipped.
5. Classify findings.
   - `entropy`: duplicate docs, stale examples, dead paths, obsolete TODOs,
     noisy generated output, brittle scripts.
   - `readability`: confusing APIs, missing examples, comments contradicting
     code, unclear invariants.
   - `proof`: missing tests, stale E2E coverage, unproven provider paths,
     missing artifacts.
   - `correctness`: repeated review findings, weak invariants, unhandled edge
     cases, regression or performance signals.
   - `ownership`: work that belongs in another repo, plugin, skill, docs site,
     or maintainer decision.
6. Recommend actions.
   - Choose one of: no-op, file follow-up, update docs, add small test, run a
     targeted proof command, open a narrow PR, request maintainer decision.
   - Prefer one or two high-signal actions over a long cleanup backlog.
7. If in `guarded-fix` mode, edit only after the report justifies it.
   - Keep changes narrow and reviewable.
   - Fix one demonstrated bug class at the right ownership boundary.
   - Update matching docs/tests only when the behavior or public workflow
     changes.
   - Rerun focused proof and summarize before/after evidence.

## Report Shape

Use this structure unless the repo provides its own artifact format:

```markdown
# Repository Garden Report

Scope:
- Repository:
- Mode:
- Target branch/commit:
- Areas inspected:
- Areas excluded:

Evidence:
- Commands/checks run:
- Skipped checks:
- Source/docs/issue/PR evidence:

Findings:
- Entropy:
- Readability:
- Proof:
- Correctness:
- Ownership:

Proposed actions:
- No-op:
- Follow-up issue:
- Docs/test/code fix:
- Maintainer decision:

Guardrails:
- Secrets/raw private data omitted:
- Broad refactors avoided:
- GitHub/public mutations performed:
```

Keep empty sections as `None found` or omit them if the final report stays
clearer.

## Guarded Fix Rules

Allowed fix classes:

- Correct a stale doc/example that directly contradicts current behavior.
- Add or repair a focused test for a demonstrated proof gap.
- Remove an obsolete TODO only when current code and issue history prove it is
  obsolete.
- Tighten a small script/check when it has a failing or missing proof path.
- Update repo-local gardening policy when maintainers already requested it.

Disallowed fix classes:

- broad cleanup, churn, mass formatting, or style-only rewrites
- renaming public APIs or files without owner approval
- changing release, security, auth, or migration behavior without maintainer
  review
- adding new global config, env vars, state stores, background jobs, or core
  commands just to support gardening
- opening multiple low-confidence issues or PRs

## ClawHub And Scheduling

For OpenClaw ecosystem work, prefer this route:

1. Keep the reusable gardening workflow as an installable skill.
2. Publish or sync the skill through ClawHub.
3. Use OpenClaw cron to schedule a prompt that invokes the skill in `report`
   mode.
4. Use repo-local policy to decide checks, exclusions, thresholds, and allowed
   fix classes.
5. Open a core or product issue only after a real gardening run proves a
   missing OpenClaw, ClawHub, Lobster, Crabbox, AutoReview, or ClawSweeper
   extension primitive.

Do not propose a bundled OpenClaw core command unless you can name the concrete
missing extension primitive and show why a ClawHub skill cannot express it.
