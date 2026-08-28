# Changelog

## Unreleased

- Partition oversized Autoreview evidence without dropping change context, keeping complete-input and per-pass credential scans within existing engine limits.
- Preserve exact outgoing autoreview scan bytes on Windows instead of translating line endings.
- Fix autoreview credential-source inclusion and scope-filtered results, preserving provider verdicts and rejected findings while documenting complete PR-plus-dirty review.
- Honor explicit review bases in local Autoreview runs, preserving complete staged and unstaged changes without re-reviewing unchanged upstream files.
- Update the validation workflow to Node.js 26.
- Fix autoreview scans with root-owned TruffleHog installations by disabling scanner self-updates while preserving credential detection and fail-closed behavior.
