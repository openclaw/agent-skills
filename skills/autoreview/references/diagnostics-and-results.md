# Diagnostic and result guidance

Exit codes, result interpretation, finding decisions:
[SKILL.md](../SKILL.md#diagnostics-and-results).
Read for output-path edge cases, machine status, usage accounting, local stage observation.

## Local stage diagnostic

- Observe first streamed Codex process: `--engine-stage-dir /outside/repo/fresh-private-directory`
  + `--stream-engine-output`.
- Create/exclusively hold fresh mode-`0700` directory on responsive local POSIX
  storage. Helper neither creates it nor overwrites `engine-stage.json`.
- No observation for other engines, buffered output, dry runs; no environment
  variable activates it.

- Sidecar: only closed booleans/enums, ≤4096 bytes; local launch, read, parser,
  display, first-process terminal observations. Retries/passes never update it;
  terminal state can differ from review outcome.
- `spoofable` always true; `provider_receipt`/`acceptance` always false.
- Missing/false = unknown, not provider activity, native initialization, acceptance.
  Redaction wrapper leaves flushed-display observations unknown.

- Ordinary observation/persistence failures preserve primary result. Persistence
  rejects repository paths, symlinks, unsafe ownership/permissions, existing names.
- Failed cleanup may leave private `.engine-stage.partial` or unresolved closure;
  retain custody when clearing it. Never retry ambiguous closes.
- Cancellation propagates; cleanup cancellation can replace pending exception
  after remaining attempts.
- Assumes ordinary descriptor acquisition/assignment, trusted caller custody,
  responsive storage; not hostile same-user interference, concurrent descriptor
  reuse, arbitrary interruption, network/stalled filesystems, crash durability.
- No change to report, usage, deadline, exit, isolation rules.

## Results

- All output paths must be outside repo as both final entries (resolve parent
  symlinks) and resolved referents.
- Without `--status-output`: human/JSON outputs must name distinct final entries;
  distinct symlinks/hardlinks may share existing referent (publication replaces entries).
- Status enabled: all resolved referents must differ; refuse hardlink aliases.
- Conservatively refuse case-only/Unicode-normalization aliases on every platform.
- Tilde/relative paths expand once, anchored to invocation directory.
- Atomic writes replace final symlink; never modify its target.

- Event streams: non-null `structured_output` must contain report object;
  only absent/null permits `result`. Last terminal event authoritative.

- `--status-output /outside/repo/status.json`: versioned outcome; validated
  `--json-output` report format unchanged. Completed status values:
  `scoped-clean`, `findings`, `filtered`, `incorrect`, `incomplete`.
- Launched reviewer fails or returns invalid output: `reviewer_unavailable` (exit 1).
- Failed later pass never publishes partial report.

```json
{
  "schema_version": 1,
  "status": "reviewer_unavailable",
  "exit_code": 1,
  "engine": "codex",
  "report_produced": false,
  "reason": "engine_failed",
  "reviewer_exit_code": 124,
  "timed_out": true
}
```

- Unavailable reasons: `engine_failed`, `invalid_report`, `runtime_validation_failed`;
  completed reviews use null.
- Runtime validation: Amp post-launch isolation attestation/private-result check
  refused output, not transient-provider failure.
- `reviewer_exit_code`: retained last process code (possibly zero for rejected
  output), otherwise null. `timed_out`: helper's deadline, not merely process exit 124.
- Inspect status independently of `--expect-findings` exit changes.

- Unfinished assessment: keep validated observations with `incomplete`, exit 2,
  `report_produced: true`, even with findings. Never publish private completion field.
- Missing/invalid completion: invalid report, not unfinished.

- Status contains no logs, prompts, findings, model identifiers.
- Bounded display-safe stderr diagnostics + command-auth suppression stay enabled.
- Use a fresh status path for real reviews: after argument/path validation, remove
  old status before target selection.
- Dry runs validate output paths but do not create, replace, or remove output files.
  Any existing status belongs to a prior invocation, not the dry run.
- Preflight/pre-launch isolation refusals, source mutations, interruptions,
  output failures: no new status. Absence never means clean verdict.

## Usage

- Codex collects usage with live display on/off. Reports, status, terminal summary:
  process attempts; reported, unknown, partial counts; `complete`; observed token totals.
- Each attempt contributes last valid cumulative snapshot once, including access
  retries + failed passes. Retry policy: [engine options](engines.md).

- Cached input/reasoning output: subsets, not extra totals.
- Counts: observed tokens, not billing estimates or cache-hit promises.
- Missing telemetry (including all-zero defaults without sample): unknown, never
  measured zero. `tokens: null`: no usable totals; incomplete totals: lower bounds.
- Interrupted runs: print retained usage; never publish status/reports.
- Other engines do not aggregate usage.
