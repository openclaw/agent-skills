# Changelog

## Unreleased

**Highlights:** Authenticated proxy support for isolated reviews, explicit reviewer availability, and controlled session sharing.

- Support launcher-provided authenticated HTTP/SOCKS proxies in Autoreview, preserve external transport trust settings, and redact proxy credentials from diagnostics and reports without changing reviewer isolation. Thanks @fuller-stack-dev.
- Fix Claude reviewer startup when the CLI truncates piped help output, while retaining mandatory isolation checks. Thanks @phyrexia.
- Add opt-in Autoreview `--status-output` to distinguish unavailable reviewers from clean, adverse, filtered, and incomplete reviews without changing existing report JSON or exit codes. Thanks @coygeek.
- Provide shared Autoreview, Crabbox, behavior-validator, handoff, readme-standard, agent-transcript, session-viewer, and Beam workflows, with selectable symlink/copy installation and cross-platform skill validation.
- Run explicitly requested reviews through isolated Codex, Claude, Amp, Pi, or Kimi engines, with structured findings, scoped attribution, progress, streaming diagnostics, dry-run preflight, and optional process deadlines.
- Preserve complete Autoreview source and evidence without file or count caps, partitioning oversized inputs across review passes without truncation or partial-clean success.
- Preserve base/index/working-tree source identity, literal paths, empty-source anchors, raw Git parents, and directory transitions; honor explicit local bases and normalize Git diff presentation.
- Remove the external TruffleHog requirement from Autoreview; keep isolated reviewer credential checks and leave any pre-send scanning to the caller. Thanks @Patrick-Erichsen.
- Keep reviewer input, authentication, temporary files, and tools isolated; protect captured evidence against mutation and topology changes, and confine macOS reviewer scratch access.
- Allow explicit trusted OpenAI Responses route projection through Autoreview's existing Codex config override, retaining native provider defaults, isolated catalogue snapshots, and trusted caller HOME only for selected POSIX authentication helpers.
- Preserve Unicode and control characters in Autoreview's Codex configuration overrides and isolated Kimi TOML configuration.
- Preserve provider conclusions, rejected findings, and distinct mixed-source claim variants; distinguish filtered and incomplete reviews from a scoped-clean result.
- Publish redacted coding sessions through Beam's authenticated read-only catalog; accept readable and named share URLs, ignore persisted agent messages, and keep transcript items within receiver limits.
- Make agent transcripts explicit-request-only and trim before previews or publication, retaining native hosted-session sharing and partial-source notices.
- Bound agent-transcript session reads to 8 MiB and disclose partial source content in render, preview, append-body, and HTML output. Thanks @SebTardif.
- Bound agent-transcript `find` and `html` discovery to 20,000 session files, with an integer override and correct exact-limit handling. Thanks @SebTardif.
- Add opt-in session-viewer head/tail reads with `--max-read-bytes`, preserving complete exports by default and showing escaped truncation warnings; retry short reads and fail on unexpected EOF. Thanks @SebTardif.
- Normalize session-viewer metadata and timestamps, improve searchable local HTML exports, and avoid the Windows shell when opening an export.
- Make Crabbox guidance portable and provider-neutral while preserving source-trust, remote-proof, and cleanup ownership boundaries.
- Update validation to Node.js 26 and current setup actions, restrict workflow permissions, and maintain Python and Node regression coverage across Linux and Windows.
