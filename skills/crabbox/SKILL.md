---
name: crabbox
description: "Crabbox/Testbox remote proof: portable provider routing, untrusted isolation, Linux/macOS/Windows/WSL2, live E2E, diagnostics, cleanup."
---

# Crabbox

- **PR CI = default broad proof.** Use the consumer repository's proof policy
  for required checks, builds, and ready/merge gates. Run bounded local checks
  only when source trust and host qualification permit them.
- **Required build unavailable:** remote capacity unavailable + local execution
  unqualified permits an already-authorized draft with the exact missing build
  and capacity gap recorded. Require successful exact-head CI covering that build
  before ready or merge. A skipped draft job is not proof: use the consumer's
  supported exact-head CI route. This changes proof timing, never publication
  authority, source trust, credentials, owner approval, or merge gates.
- Box only for gaps in CI/local coverage: another OS/device, live providers/channels,
  long E2E, heavy benchmarks. Acquire only with command ready + immediate grant.
- Queued: stop task-owned request; use PR CI or a qualified, trusted local scope.
  Report uncovered requirements. Never wait on queues or chain providers.
- Fix real failures; never rerun/re-push merely for green. Read available CI failure
  classification before attributing failure to change.

## Repository Contract

- Skill owns portable routing, leases, sync, commands, cleanup.
- Resolve `<check-command>`, runtime/container image, PR, bootstrap from trusted
  consumer instructions, package scripts, or hydration workflow.
- Never invent missing commands or copy another consumer's setup.
- Always report provider, id, run URL, command, result. Never call Testbox
  “AWS Crabbox” or local Docker remote proof.

## Authorization and Isolation

- Routine configured use: creating/reusing/stopping task-owned leases, temporary state,
  clean checkouts/worktrees for proof or required Crabbox repair; no separate approval.
- Preserve user checkouts, branches, unrelated edits; dirty/missing/occupied
  checkouts: use task-owned ones.
- Preserve source-trust, credential, production-access, budget, publication boundaries.

- Never execute untrusted repository wrappers/config locally or on credential-hydrated
  Testbox. Use secretless fork CI or sanitized direct AWS: fresh lease per full head
  SHA; no instance role, Tailscale, hydration; only `CI` forwarded.
- Before untrusted AWS execution: read/follow complete
  [untrusted recipe](references/untrusted-aws.md), including no-role + SHA proof.
  Proof unavailable: secretless fork CI.
- Live credentials: exact key, one command, safe injection only. Never print secrets,
  put in repository files/shell history, or call fake keys live proof.
  No safe injection path: live auth blocked. Review captured artifacts for secrets.
- Isolate proof in consumer's temporary state/config directory; never mutate
  operator's normal installation. Stop owned leases after use, including failures.

## Route First

- Source trust restricts providers; does not select one. Inspect/preserve resolved provider.
- Normally omit `--provider`; override only when explicitly requested or proof
  requires backend semantics. Never for size, duration, hydration failure, capacity.
- No speculative warmup or provider escalation.

| Provider | Use |
| --- | --- |
| `blacksmith-testbox` | Trusted maintainer source with prepared CI; `tbx_...` |
| `aws` | Direct brokered execution, fresh PRs, custom sync/env/capture; `cbx_...` |
| `local-container` | Configured/requested local Docker; not remote proof |
| `ssh` | Existing operator host for macOS/Windows/WSL2 |

## Preflight

From repo root, select trusted installed binary once:

```sh
export CRABBOX="$(command -v crabbox)"
test -n "$CRABBOX"
"$CRABBOX" --version
"$CRABBOX" config show --json | jq '{provider, profile, target}'
"$CRABBOX" run --help
```

- Read `.crabbox.yaml` + resolved config, including user/environment settings.
- Testbox: also check `command -v blacksmith` + `blacksmith --version`.
- Consumer may name trusted wrapper; missing/broken: follow trusted install/update
  path; verify canonical upstream before building in clean task checkout.
- Never assume sibling checkouts trusted or replace operator's binary with task build.
- Isolate wrapper failures with installed CLI on same resolved provider.

## Trusted Testbox

Only for resolved/requested Testbox. Provider-neutral commands retain configuration;
add `--provider blacksmith-testbox` only for explicit override.

```sh
"$CRABBOX" run --timing-json -- CI=1 <check-command>
```

Several commands: save id, reuse, stop:

```sh
"$CRABBOX" warmup --keep --timing-json
"$CRABBOX" run --id <tbx_id> --timing-json -- <check-command>
"$CRABBOX" stop <tbx_id>
```

- One lease, one active command; no sync/reclaim during run. `--reclaim` only
  for deliberate checkout-path ownership transfer.
- Native Testbox runs sync even with reused ids. Never rely on `--no-sync` for
  baseline, even unchanged rerun; may be silently ignored.
- Base/head changed: stop + rewarm; never override stale lease.
  Crabbox `warmup --blacksmith-ref` (native `blacksmith testbox warmup --ref`):
  branch/tag only, never raw SHA. Never checkout refs in synced root.
- Testbox native status/stop: `--id`; status has no `--json`. Use
  `blacksmith testbox list --all` or `blacksmith testbox status --id <tbx_id>`.
- Delegated Testbox rejects `--fresh-pr`, `--full-resync`, `--script*`, `--env-helper`,
  and capture/download flags. Crabbox `stop` does not accept `--timing-json`.

### Verify Synced Inputs

- Missing modules/fixtures: compare required inputs to frozen source; inspect sync
  exclusions, including Git-ignore negations. Successful sync can omit tracked files.
- Record each missing path + frozen Git blob. Restore only reviewed required inputs
  into task-owned remote checkout; verify bytes. Account for changed/untracked inputs
  separately. Recheck after each native sync.
- Never regenerate baselines, copy unrelated state, disable exclusions, or assume
  all missing files safe.
- Sync timeout ≠ test result. Establish whether payload dispatched; unknown:
  inspect lease/invocation before retrying. Preserve completed proof by source
  identity; run only missing verification.

## Specialized Proof and Diagnostics

Read only relevant recipe; routing + immediate-availability rules still apply:

- [Direct AWS, containers, desktop and cross-OS](references/providers-and-desktop.md):
  exact provider commands, broker auth, paid macOS quota/no-spend preflight, desktop
  handoff. No silent substitution; never commit proof assets to product repo.
- [Diagnostics and real E2E](references/diagnostics-and-e2e.md): capture/env flags,
  failure layers, and the recipe for requested or consumer-required user-path proof.
  Full-screen CLIs: real PTY. Compare Testbox revisions within one synced invocation
  using detached temporary worktrees; later runs resync local source.
