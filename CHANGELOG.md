# Changelog

## Unreleased

- Update development Node.js types to 26.6.5 and the native macOS sandbox-test Codex CLI to 0.162.1.
- Update development Node.js types to 26.6.4 and the native macOS sandbox-test Codex CLI to 0.160.1.
- Skip inaccessible executable search candidates during Autoreview preflight while preserving explicit executable selection and repository-path rejection. Thanks @vincentkoc.
- Use one shared autoreview installation across repositories through thin Markdown entrypoints instead of vendored implementations and tests.
- Preserve Crabline's Windows review launcher, Python 3.10 interpreter probing, complete malicious-fixture expectations, and harness cleanup failure reporting in the canonical skill. Thanks @vincentkoc.
- Accept `ultrafast` for Autoreview's `--codex-speed` and `AUTOREVIEW_CODEX_SPEED`, sending Codex the Ultrafast service tier when the active model catalog lists it.
- Add `team-handoff`: start a worktree session on a shared OpenClaw Gateway behind Cloudflare Access as the operator's own identity in one `sessions.create` request, with status/archive helpers and an opt-in SSH operator fallback.

## 0.4.0 - 2026-09-30

**Highlights:** Review with GPT-6.1 Sol by default, with early effort validation and an access-only GPT-6 Sol retry.

- Default Autoreview's Codex reviewer to GPT-6.1 Sol at high reasoning, reject unsupported efforts before preparation, and retry GPT-6 Sol only on account-access failure while preserving explicit older-model behavior. Thanks @coygeek.

## 0.3.0 - 2026-09-30

**Highlights:** Review deleted binary assets safely, with stronger result validation and reviewer deadlines.

- Review deleted binary assets as Git deletion metadata in local, branch, and commit reviews, while preserving added-image review and refusing unsupported binary content changes. Thanks @roboclaw-bot.
- Reject invalid final Autoreview terminal results without reusing earlier reports, and keep validated output paths consistent through status cleanup and atomic report publication.
- Refuse Autoreview output symlinks inside the reviewed repository even when their referents are outside, preserving repository entries and stale status on validation failure.
- Keep Autoreview's configured reviewer deadline active after streamed output closes, so a still-running reviewer cannot overrun the limit and return a successful review.
- Preserve literal Unicode separators inside Autoreview JSONL records so final reports remain authoritative and valid Amp streams are accepted.
- Reject invalid Amp model names during Autoreview dry runs with the same provider/model diagnostic used for execution.
- Preserve feasible Autoreview partitions when intact context leaves less room than the estimated continuation reserve, while retaining complete evidence and the prompt limit.
- Reject colliding Autoreview JSON and human output entries before review, while preserving separate symlink and hardlink destinations when no status sidecar is requested.
- Refuse Kimi reviews and dry runs before startup until a private prompt input channel is supported, preventing review bundles from entering process arguments without silently changing engines.
- Reject invalid Autoreview priority environment defaults before preparation or reviewer startup, while preserving explicit priority overrides.
- Normalize absolute in-repository Autoreview finding paths without losing other findings, while preserving literal filenames and refusing traversal and outside paths. Thanks @kennykankush.
- Update the native macOS sandbox-test Codex CLI to 0.159.3.

## 0.2.0 - 2026-09-24

**Highlights:** Native image review, committed source context, and more efficient multi-pass reviews.

- Review added single-frame PNG, JPEG, and WebP assets in Codex branch reviews through native image attachments, with pinned bytes and per-pass manifests. Thanks @mgunnin.
- Add Autoreview `--source-context-file` to keep explicitly selected committed source intact in every pass, with the existing provenance, mutation, path and finding-scope guards and unchanged prompt limits.
- Add Autoreview `--source-context` for complete source bytes bound to the reviewed commit and blob, with validated same-role deduplication and strict credential-path and mutation guards, without expanding finding scope or changing generic evidence restrictions.
- Reduce repeated Autoreview evidence without increasing passes or dropping change/evidence coverage; show planned work, add an explicit preflight pass budget, and aggregate observed Codex usage across passes and access retries with incomplete telemetry marked as a lower bound.
- Keep complete Autoreview evidence in every change partition when it leaves sufficient change space, before splitting datasets or optimizing their allocation; preserve feasible terminal plans when batch framing cannot fit.
- Update Autoreview’s default Codex model and account-access-only fallback; preserve explicit model choices and validate supported reasoning levels.
- Prefer OpenAI/Codex before Claude when choosing an Autoreview engine, including independent second opinions; retain explicit user choices and require a concrete Codex availability failure before switching.
- Split Windows skill validation into core, hardening, and boundary jobs while retaining the complete default check sequence and existing job timeouts.
- Split Windows Autoreview hardening validation into two deterministic test-ID shards, preserving the full test union, aggregate local commands and existing job timeouts.

## 0.1.0 - 2026-09-22

**Highlights:** Safer Git collection and installation, explicit review completion, and reusable review and session workflows.

- Prevent checkout-controlled Git execution during Autoreview PR-base discovery and collection; refuse executable conversion before review while preserving local diffs that need no converter and committed branch/commit reviews.
- Refuse installer destinations that overlap source skills before any mutation, preventing recursive installs and source deletion with `--force`.
- Keep unfinished Autoreview assessments incomplete while retaining validated provider observations and existing public report contracts. Thanks @vincentkoc.
- Preflight Autoreview Git within 10 seconds, honor a trusted `AUTOREVIEW_GIT` override and macOS `DEVELOPER_DIR`, and accept absolute in-repository prompt files with existing evidence safeguards.
- Validate requested reasoning levels before Autoreview preparation and keep source instructions subordinate to the noninteractive review contract. Thanks @coygeek.
- Support launcher-provided authenticated HTTP/SOCKS proxies in Autoreview, preserve external transport trust settings, and redact proxy credentials from diagnostics and reports without changing reviewer isolation. Thanks @fuller-stack-dev.
- Fix Claude reviewer startup when the CLI truncates piped help output, while retaining mandatory isolation checks. Thanks @phyrexia.
- Add opt-in Autoreview `--status-output` to distinguish unavailable reviewers from clean, adverse, filtered, and incomplete reviews without changing existing report JSON or exit codes. Thanks @coygeek.
- Provide shared Autoreview, Crabbox, behavior-validator, handoff, readme-standard, agent-transcript, session-viewer, and Beam workflows, with selectable symlink/copy installation and cross-platform skill validation.
- Reject malformed frontmatter closing delimiters and report non-mapping YAML values accurately during skill validation.
- Run explicitly requested reviews through isolated Codex, Claude, Amp, Pi, or Kimi engines, with structured findings, scoped attribution, progress, streaming diagnostics, dry-run preflight, and optional process deadlines.
- Preserve complete Autoreview source and evidence without file or count caps, partitioning oversized inputs across review passes without truncation or partial-clean success.
- Preserve base/index/working-tree source identity, literal paths, empty-source anchors, raw Git parents, and directory transitions; honor explicit local bases and normalize Git diff presentation.
- Honor trusted global Git `core.autocrlf` during Autoreview selection while preserving local overrides, attributes, source bytes, and protected Git execution.
- Respect an explicit Git `HOME` without evaluating an unavailable Windows platform-home fallback.
- Remove the external TruffleHog requirement from Autoreview; keep isolated reviewer credential checks and leave any pre-send scanning to the caller. Thanks @Patrick-Erichsen.
- Keep reviewer input, authentication, temporary files, and tools isolated; protect captured evidence against mutation and topology changes, and confine macOS reviewer scratch access.
- Allow explicit trusted OpenAI Responses route projection through Autoreview's existing Codex config override, retaining native provider defaults, isolated catalogue snapshots, and trusted caller HOME only for selected POSIX authentication helpers.
- Preserve Unicode and control characters in Autoreview's Codex configuration overrides and isolated Kimi TOML configuration.
- Preserve provider conclusions, rejected findings, and distinct mixed-source claim variants; distinguish filtered and incomplete reviews from a scoped-clean result.
- Publish redacted coding sessions through Beam's authenticated read-only catalog; accept readable and named share URLs, ignore persisted agent messages, and keep transcript items within receiver limits.
- Let Beam discover exact-limit session stores, retry short transcript/metadata reads, and stop publication on unexpected EOF.
- Make agent transcripts explicit-request-only and trim before previews or publication, retaining native hosted-session sharing and partial-source notices.
- Bound agent-transcript session reads to 8 MiB and disclose partial source content in render, preview, append-body, and HTML output. Thanks @SebTardif.
- Retry short agent-transcript reads and fail on unexpected EOF before rendering or scoring incomplete session content.
- Bound agent-transcript `find` and `html` discovery to 20,000 session files, with an integer override and correct exact-limit handling. Thanks @SebTardif.
- Add opt-in session-viewer head/tail reads with `--max-read-bytes`, preserving complete exports by default and showing escaped truncation warnings; retry short reads and fail on unexpected EOF. Thanks @SebTardif.
- Normalize session-viewer metadata and timestamps, improve searchable local HTML exports, and avoid the Windows shell when opening an export.
- Make Crabbox guidance portable and provider-neutral while preserving source-trust, remote-proof, and cleanup ownership boundaries.
- Pin validation actions and Node.js 26, share reproducible Python/Node checks across local development and CI, typecheck the session viewer, and exercise native macOS sandbox controls alongside Linux/Windows regression coverage.
- Declare the repository's native Node helpers as ES modules to avoid loader warnings when running from a development checkout.
- Keep copied Beam, agent-transcript, and session-viewer helpers runnable inside CommonJS projects with skill-local module declarations.
