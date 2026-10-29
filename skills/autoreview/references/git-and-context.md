# Git collection and context

## Git collection

- Registered nested linked checkouts from same repository: outside current review
  scope; presence/edits do not make parent dirty. Ordinary adjacent files stay included.
- Revalidate worktree boundaries without changing Git ignore rules.

- Local status columns come from the captured base → index and index → working-tree
  diff queues, not a separate HEAD-relative status. Paths are JSON strings; renames
  appear as add/delete transitions, matching the no-renames patches.

- Git display settings cannot suppress context markers or add patch colors;
  repository configuration unchanged. Source paths/text retain literal whitespace.
- Empty present source: line 1, column 1, empty excerpt. Empty physical lines:
  empty excerpt at column 1. Source identity mandatory.

- Binary deletions stay in scope as Git deletion metadata; former contents neither
  included nor reviewed. Check each local transition independently:
  deleting working-tree file cannot hide staged binary change.

- Finding locations may use native absolute paths resolving inside reviewed
  repository; convert to repository-relative before scope/attribution checks.
  Preserve changed symlink's path when target also inside.
- Parent traversal/paths resolving outside repository: invalid.
  Invalid location fails report; never silently drop findings.

- Local selection honors external operator Git `core.autocrlf`; repository-local
  values/attributes keep precedence. Only validated scalar value reaches diff/status;
  other global/system Git configuration stays disabled.
- Never import repository-owned/relative global-config overrides or rewrite reviewed source bytes.

- Local collection disables effective Git clean/process commands; conversion must
  succeed. Unused drivers, unchanged filtered neighbors, staged-only changes,
  deletions: reviewable without executing converters.
- Git needs executable conversion to assemble diff: fail collection before reviewer
  starts. Can include unchanged filtered file whose stat cache needs refreshing.
  Use explicit branch/commit mode for committed content then.
- Built-in line-ending normalization stays enabled; raw bytes never substitute
  for required executable conversion.
- PR-base discovery: trusted external Git + scoped GitHub CLI environment;
  preserve external authentication/configuration + proxy settings; exclude inherited
  Git routing, `GH_REPO` redirection, checkout-owned executables.
- Differently named `AUTOREVIEW_GIT` override child cannot also select as `git`:
  explicit `--base` required. Rejected GitHub configuration paths: same requirement.

## Submodule pins

Gitlink changes (mode `160000`) include full old/new commit IDs and the path's
URLs from the corresponding `.gitmodules` states. Branch/commit mode reads frozen
blobs; local mode reads base, index and working-tree mappings independently.
Local Git config, URL rewrites, includes and submodule update commands are not used.
Missing mappings are explicit `null` values; ambiguous mappings fail preparation.

This reviews the superproject pin and integration, not the upstream code. No
network fetch or submodule checkout runs. To review upstream changes, explicitly
fetch the range in a separate checkout and supply relevant evidence with
`--dataset`; that context does not expand finding scope beyond the superproject.
Uncommitted submodule contents and mixed staged/unstaged gitlink changes remain
unsupported; use committed branch/commit mode for pin reviews. Other source,
authentication, sandbox and mutation checks remain enabled.

## Committed source context

- Basic context flags/safety rules: [SKILL.md](../SKILL.md#context-and-severity).
- Repeated paths in same evidence role share one validated capture. Equal content
  at different paths and prompt-file versus dataset roles stay distinct.

- Unchanged committed source: repeatable `--source-context <repo-relative-path>`
  with branch/commit mode. Source must stay intact every review pass:
  `--source-context-file <repo-relative-path>`.
- Both read exact regular-file blob from frozen reviewed commit (branch HEAD or
  `--commit`), including executable source files.
- Local mode, including auto-selected local target: unsupported.
  No separate context revision or working-copy substitution accepted.
- Checkout path must stay regular file; revalidate bytes/path topology throughout review.
- Repeated normalized source-context paths share one capture after validating every
  argument; different paths/evidence roles stay distinct.

- Both roles: tracked-source filename classification; source names such as
  `src/token_count.py` accepted. Credential directories, stores, keyfiles forbidden.
  Existing prompt-file/dataset restrictions unchanged.
- Every source block: path, commit, blob, mode provenance.
- `--source-context` bytes: partition with change when needed.
- `--source-context-file` blocks: complete every pass; must fit with instructions
  + change framing. Over-capacity plan: refuse, never drop required evidence.
- Context never adds finding targets/instruction authority.
  Contract: source-provenance, not secret-content scanning.

```bash
"$AUTOREVIEW" --mode branch --base origin/main --source-context src/token_count.py
"$AUTOREVIEW" --mode branch --base origin/main --source-context-file src/token_count.py
```

## Runtime diagnostics

- Before repository detection/target selection: Git must pass `--version` within
  10 seconds. Failure: exit `2`, `incomplete` diagnostic + resolved executable
  (or unresolved selection); never `scoped-clean`.
- Executable discovery skips inaccessible search candidates;
  inaccessible explicit executable override still fails preflight.
- Set `AUTOREVIEW_GIT` to trusted external Git executable: override every
  helper-owned Git invocation.
- macOS, broken selected Xcode: use
  `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer` for invocation.
- Git sanitized environment additionally retains only absolute, external
  `DEVELOPER_DIR`; neither override forwarded to isolated reviewer environment.

## Partition planning

- Text review files: no size/count cap; never truncate. Image inputs:
  [image safety limits](images.md). Partition large diffs/datasets automatically.
- Change partitions retain complete datasets when they fit with sufficient change
  space. Preference may cost more passes/prompt bytes than evidence batching;
  explicit pass budget still applies.
- Terminal fallbacks preserve feasible complete-evidence plan when batch framing cannot fit.
- Intact instructions, source-context files, required mixed source context must fit
  per-pass prompt budget. Failed pass never produces partial clean verdict.
- `--max-prompt-bytes N` selects that UTF-8 byte budget for dry-run and live review
  (default `512000`). The plan reports its limit and largest rendered prompt.
  A larger explicit budget admits more complete context only when it fits;
  it does not change engine/model context limits or guarantee token capacity.
- Otherwise compare bounded evidence allocations; keep existing plan unless total
  prompt bytes improve without more passes, or equal bytes need fewer passes.
- Every change reviewed against every evidence batch.
