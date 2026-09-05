# Changelog

## Unreleased

- Make agent transcripts explicit-request-only and trim before previews or publication, retaining native hosted-session sharing and partial-source notices.

- Preserve Unicode and control characters in Autoreview's Codex configuration overrides and isolated Kimi TOML configuration.
- Allow explicit trusted OpenAI Responses route projection through Autoreview's existing Codex config override, preserving default auth-only compatibility, native provider defaults, and isolated catalogue snapshots.
- Validate explicit index/working-tree targets for mixed local Autoreview paths, preserving source anchors, rejected-attribution audit and distinct claim variants while repeating mandatory context within existing capacity limits.
- Restore mandatory Autoreview TruffleHog `verified,unknown` pre-send scans removed in #209, retaining reviewer P0 credential checks as defense in depth.
- Add opt-in session-viewer head/tail reads with `--max-read-bytes`, preserving complete exports by default and showing escaped truncation warnings in normalized and raw exports; retry short reads and fail on unexpected EOF. Thanks @SebTardif.
- Bound agent-transcript session reads to 8 MiB and disclose partial source content in render, preview, append-body, and HTML output. Thanks @SebTardif.
- Bound agent-transcript `find` and `html` discovery to 20,000 session files, with an integer override and correct exact-limit handling. Thanks @SebTardif.
- Rescan the exact outgoing Autoreview pack before Codex access-fallback retries, refusing findings, scanner errors, and missing scanners before another provider invocation.
- Show Autoreview preparation progress, reuse captured bundle membership, and guard explicit evidence against content and path changes while preserving full-tree integrity checks.
- Verify raw Git parents in Autoreview commit bundles, preserving true roots and refusing unsupported attribution from shallow boundaries, grafts, or misleading metadata.
- Partition oversized Autoreview evidence without dropping change context, keeping complete-input and per-pass credential scans within existing engine limits.
- Preserve exact outgoing autoreview scan bytes on Windows instead of translating line endings.
- Fix autoreview credential-source inclusion and scope-filtered results, preserving provider verdicts and rejected findings while documenting complete PR-plus-dirty review.
- Honor explicit review bases in local Autoreview runs, preserving complete staged and unstaged changes without re-reviewing unchanged upstream files.
- Update the validation workflow to Node.js 26.
- Fix autoreview scans with root-owned TruffleHog installations by disabling scanner self-updates while preserving credential detection and fail-closed behavior.
