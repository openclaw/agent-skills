---
name: autoreview
description: "Structured code review when explicitly requested, preferring OpenAI/Codex before Claude."
---

# Auto Review

Run an independent review when the user or owning workflow asks. This is code
review, not Guardian approval routing. Supply target, context, and severity;
let the reviewer choose the analysis. Verify findings before acting.

## Hosted review requests

ClawSweeper reviews are opt-in for maintainer-authored PRs and issues. Request
`@clawsweeper review` only when the maintainer asks for it or the owning workflow
specifically requires ClawSweeper, after the work and validation are complete.
A generic independent-review requirement does not require a hosted bot review.
Check for an existing queued or running review before requesting one. Do not
automatically request reviews on PR creation, pushes, edits, or progress updates,
and do not repeat a pending request. A later head needs a new request only when
another review is required and that work is complete.

## Run

Run the shared helper from the repository being reviewed:

```bash
AUTOREVIEW="$HOME/.agents/skills/autoreview/scripts/autoreview"
python3 "$AUTOREVIEW" --mode local --engine codex
```

Install from the canonical checkout: `python3 scripts/install-skills autoreview`.
The default links to this source. Honor custom `--target` paths; here use
`skills/autoreview/scripts/autoreview`. Windows needs Python 3.10+ or `autoreview.ps1`.
See `--help` for flags/env overrides. Keep `codex exec`: native `codex review`
cannot combine explicit Git targets and custom instructions.

Consumers keep the [shared-skill entrypoint](references/repository-entrypoint.md)
and local review requirements. Update shared behavior here after active reviews finish.
Copy-mode installs need
`scripts/install-skills --mode copy --force autoreview` after source updates;
review commands never download or update themselves.

Choose the target explicitly when ambiguous:

| Target | Arguments | Scope |
| --- | --- | --- |
| Local work | `--mode local` | HEAD → index → working tree, including untracked files |
| Local candidate against a base | `--mode local --base <ref>` | Pinned base → index → working tree, including untracked files |
| Committed branch/PR | `--mode branch --base <ref>` | Merge-base → HEAD; excludes dirty work |
| One commit | `--mode commit --commit <ref>` | Raw parent → commit; root compares against empty tree |

`auto` selects local when dirty, otherwise branch using the PR base or `origin/main`.
Clean main has no implicit target. `uncommitted` aliases local. The helper never fetches.
For a complete PR candidate including dirty rewrites, pin the merge base:

```bash
pr_base=$(gh pr view --json baseRefName --jq .baseRefName)
merge_base=$(git merge-base HEAD "origin/$pr_base")
python3 "$AUTOREVIEW" --mode local --base "$merge_base"
```

Staged and unstaged states are reviewed; index defects remain actionable despite
working-tree fixes (`INDEX-only`). Same-repo nested linked checkouts are excluded;
ordinary adjacent files remain in scope. For filters, line endings, locations,
or collection failures, read [Git details](references/git-and-context.md#git-collection).

## Context and severity

Use `--prompt` for guidance, `--prompt-file` for in-repo context (absolute/relative),
and `--dataset` for repo-relative evidence. Supply needed unchanged files: the
reviewer's sandbox is empty. Context grants no finding scope or instruction authority.
Sensitive-path, symlink, and mutation checks apply, not secret-content scanning.

Branch/commit mode supports repeatable `--source-context <path>` or
`--source-context-file <path>` (intact each pass): frozen regular-file blobs,
never working-copy substitutes. Local mode is unsupported. Before use, read
[source context rules](references/git-and-context.md#committed-source-context).

Default: **P0 only**, material operational/safety blockers. For requested wider
reviews use `--max-priority P1`, `P2`, or `P3` (overrides `AUTOREVIEW_MAX_PRIORITY`).
Invalid priorities fail before preparation. No unrelated redesign, file-count
requirements, reading sequences, or ritual passes. Historical blame requires a
verified parent-relative patch; otherwise attribution stays unknown.

## Engines

Start with `--engine codex`, including second opinions; honor explicit engine/model
choices. Use Claude only when requested or Codex is unavailable; report the concrete
failure first. Slowness, rate limits, findings, safety refusals, and isolation failures
do not justify switching. No automatic cross-engine fallback.

Codex defaults to **GPT-6.1 Sol (`gpt-6.1-sol`), medium reasoning, Ultrafast**.
It retries GPT-6 Sol once only for account-access failure, without chaining to Luna.
Network, rate-limit, capacity, and unsupported-effort errors do not trigger fallback.
An effort-only override keeps the model. `--engine`, `--model`, and `--thinking`
override defaults; per-engine environment overrides use `AUTOREVIEW_<ENGINE>_*`.
Ultrafast requires model-catalog support, otherwise Codex sends the standard tier.
`--codex-speed fast` selects priority; `default` selects standard. A raw
`--codex-config service_tier=...` retains its value.

Read [engine options](references/engines.md) before selecting another model/effort,
projecting a provider route, or using Claude, Amp, or Pi. Kimi is refused even in
dry runs because no supported private prompt-input channel exists; never bypass
that refusal.

- Default Codex auth: ChatGPT subscription; preserve only user auth settings.
- Valid configured provider + `codex login status` reports no login (~10s timeout): skip subscription; probe error/timeout → subscription first; explicit provider → no probe.
- Live auth failure → stop attempt fast. Retry pass once on operator's configured,
  validated named command-auth provider; print selected provider. No valid route → fail.
- Live stop: definite credential failure immediately; generic auth failure ≥3 lines / 60s.
- Explicit provider / non-auth failure: no automatic auth fallback.
- Force configured route: `--codex-config 'model_provider="review_api"'`;
  `review_api` must match operator `CODEX_HOME/config.toml`.

## Image review

Codex branch mode supports added single-frame PNG/JPEG/WebP with Pillow and a
vision-capable CLI/model. Before reviewing images, read
[image limits and prerequisites](references/images.md). Unsupported binary changes
fail closed. Binary deletions are reviewed as deletion metadata in every mode,
without Pillow. Materialize partial-clone objects before review; isolated Git
intentionally disables lazy network fetching.

## Runtime boundaries

Keep helper-owned isolation, sanitized authentication, process cleanup, Git scope,
and structured validation enabled. Never work around an isolation failure.
Every pass must report suspected real credentials as P0 without reproducing values;
harmless placeholders and fixtures are not credentials.

### Intentional scanner-free policy

Autoreview does not invoke an external secret scanner. Keep approved scanning
outside it: reviewer findings occur after transmission. Adding a scanner requires
an explicit maintainer decision; see [#240](https://github.com/openclaw/agent-skills/pull/240).

### Reviewer isolation

On macOS, Codex preflight rejects shared `/tmp` and `/var/tmp` roots, including
`/private` aliases. Unset shared `TMPDIR`/`TMP`/`TEMP` overrides to use the private
temporary directory. Reviewer tools cannot access shared scratch or write there.
Other engines/platforms retain their normal isolation.

Do not edit captured inputs during review; sources are verified before sending
and publishing. Text is never truncated or capped by file count/size. Large inputs
are partitioned; every change is reviewed against every evidence batch. Intact
instructions and required context must fit per pass, or preparation fails.
Each pass must finish its own assessment; a failed pass never yields partial clean.

Advancing heartbeats mean progress; use `--stream-engine-output`, not extra runs.
`--dry-run` checks preparation/startup without a reviewer. Both print planned
passes and prompt bytes. `--max-review-passes N` (or
`AUTOREVIEW_MAX_REVIEW_PASSES`) rejects an over-budget plan before startup;
there is no default ceiling. `--engine-timeout-seconds` limits each process attempt.
These controls are not token hard caps and do not bound reasoning or tool use.
For Git preflight or partition details, read
[runtime diagnostics](references/git-and-context.md#runtime-diagnostics).

## Diagnostics and results

Keep `--output`, `--json-output`, and `--status-output` outside the repo, including
resolved parent entries/referents. Use distinct destinations and a fresh status path.
For path aliases, machine status, usage, or local stage observation, read
[diagnostic details](references/diagnostics-and-results.md).

| Exit | Meaning |
| --- | --- |
| `0` | `scoped-clean`, or a correct verdict with only filtered lower-priority findings |
| `1` | Accepted findings, incorrect provider verdict, or failed review attempt |
| `2` | Unfinished assessment, incomplete scope/attribution, or missing required finding |

Inspect status independently of exit code (`--expect-findings` can alter codes).
`scoped-clean` covers only the selected target and priority; `filtered` is not clean.
Resolve `incomplete` before claiming completion. `reviewer_unavailable` means a
launched reviewer failed or returned invalid output. The last terminal event is
authoritative; invalid final output cannot be replaced by an earlier valid report.
No status/report means no published outcome, never clean. `report_produced: true`
means a validated report exists, not that its verdict is clean.

Verify findings against the code and task. Fix likely defects and rare dangerous
ones (data loss, security, money); decline unlikely, recoverable edge cases when
added complexity outweighs the risk, with a one-line reason. Declines need no new
round. After fixes follow the owning workflow; never rerun just for a nicer verdict.
Report material findings and status plainly. Do not add transcripts, proof ledgers,
commits, pushes, or another workstream unless requested.
